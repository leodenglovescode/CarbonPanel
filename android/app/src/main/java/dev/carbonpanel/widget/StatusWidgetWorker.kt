package dev.carbonpanel.widget

import android.content.Context
import androidx.glance.appwidget.updateAll
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.data.WidgetState
import dev.carbonpanel.net.ApiClient
import dev.carbonpanel.ui.components.isPseudoMount
import java.util.concurrent.TimeUnit

/**
 * Periodic refresh for the home-screen widget.
 *
 * The app's only background network activity, and it is bounded: one short
 * request per interval, only when a network is available, only while a widget
 * is placed. No persistent connection and no wakelock — the foreground polling
 * loop is torn down the moment the app leaves the screen.
 */
class StatusWidgetWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val prefs = Prefs.get(applicationContext)
        if (!prefs.isPaired) return Result.success()

        val resolved = ApiClient.resolve(applicationContext)
        if (resolved == null) {
            markStale(prefs)
            return Result.retry()
        }

        return try {
            val snap = resolved.second.metricsCurrent(
                fields = "cpu,memory,gpu,disks,network,system",
                interval = null,
            )

            // Chosen disk, else the largest real one: on a server the big data
            // volume is usually what you want to watch, and "/" is often a
            // small system partition that never moves.
            val realDisks = snap.disks.filterNot { isPseudoMount(it.mountpoint, it.device) }
            val disk = realDisks.firstOrNull { it.mountpoint == prefs.widgetDisk }
                ?: realDisks.maxByOrNull { it.total_gb }

            // Chosen interface, else the busiest — excluding container plumbing,
            // which on a Docker host is otherwise the noisiest thing present.
            val realIfaces = snap.network.filterNot { n ->
                listOf("veth", "br-", "docker", "lo", "virbr")
                    .any { n.iface.startsWith(it, ignoreCase = true) }
            }
            val iface = realIfaces.firstOrNull { it.iface == prefs.widgetIface }
                ?: realIfaces.maxByOrNull { it.rx_mb_s + it.tx_mb_s }

            val gpu = snap.gpu?.takeIf { it.available }?.devices?.firstOrNull()

            prefs.widgetState = WidgetState.encode(
                WidgetState(
                    serverName = snap.system?.hostname?.ifBlank { null }
                        ?: prefs.serverName.orEmpty(),
                    cpuPercent = snap.cpu?.aggregate ?: 0.0,
                    memPercent = snap.memory?.percent ?: 0.0,
                    memUsedMb = snap.memory?.used_mb ?: 0.0,
                    memTotalMb = snap.memory?.total_mb ?: 0.0,
                    gpuPresent = gpu != null,
                    gpuPercent = gpu?.utilization_percent ?: 0.0,
                    gpuMemUsedMb = gpu?.memory_used_mb ?: 0.0,
                    gpuMemTotalMb = gpu?.memory_total_mb ?: 0.0,
                    diskMount = disk?.mountpoint.orEmpty(),
                    diskPercent = disk?.usage_percent ?: 0.0,
                    diskUsedGb = disk?.used_gb ?: 0.0,
                    diskTotalGb = disk?.total_gb ?: 0.0,
                    netIface = iface?.iface.orEmpty(),
                    netRxMbPerSec = iface?.rx_mb_s ?: 0.0,
                    netTxMbPerSec = iface?.tx_mb_s ?: 0.0,
                    updatedAt = System.currentTimeMillis(),
                    stale = false,
                ),
            )
            StatusWidget().updateAll(applicationContext)
            Result.success()
        } catch (_: Throwable) {
            markStale(prefs)
            Result.retry()
        }
    }

    /**
     * Keeps the previous reading but flags it, so the widget can say the server
     * is unreachable rather than silently showing numbers that look current.
     */
    private suspend fun markStale(prefs: Prefs) {
        WidgetState.decode(prefs.widgetState)?.let {
            prefs.widgetState = WidgetState.encode(it.copy(stale = true))
            runCatching { StatusWidget().updateAll(applicationContext) }
        }
    }

    companion object {
        private const val WORK_NAME = "carbonpanel-widget-refresh"

        fun ensureScheduled(context: Context) = schedule(context, replace = false)

        /** Call after changing the interval so the new cadence takes effect. */
        fun reschedule(context: Context) = schedule(context, replace = true)

        private fun schedule(context: Context, replace: Boolean) {
            val minutes = Prefs.get(context).widgetRefreshMinutes.toLong()
            val request = PeriodicWorkRequestBuilder<StatusWidgetWorker>(
                minutes, TimeUnit.MINUTES,
            ).setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build(),
            ).build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                if (replace) ExistingPeriodicWorkPolicy.UPDATE
                else ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }

        /** Immediate one-shot, so changing a setting shows up without waiting. */
        fun refreshNow(context: Context) {
            WorkManager.getInstance(context).enqueue(
                androidx.work.OneTimeWorkRequestBuilder<StatusWidgetWorker>()
                    .setConstraints(
                        Constraints.Builder()
                            .setRequiredNetworkType(NetworkType.CONNECTED)
                            .build(),
                    )
                    .build(),
            )
        }
    }
}

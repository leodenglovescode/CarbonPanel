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
import dev.carbonpanel.net.ApiClient
import java.util.concurrent.TimeUnit

/**
 * Periodic refresh for the home-screen widget.
 *
 * This is the app's only background network activity, and it is bounded: one
 * short request every 15 minutes (the platform floor), only when a network is
 * available, only while a widget is actually placed. There is no persistent
 * connection and no wakelock — the foreground polling loop is torn down the
 * moment the app leaves the screen.
 */
class StatusWidgetWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val prefs = Prefs.get(applicationContext)
        if (!prefs.isPaired) return Result.success()

        val resolved = ApiClient.resolve(applicationContext) ?: return Result.retry()

        return try {
            val snapshot = resolved.second.metricsCurrent(
                fields = "cpu,memory,disks",
                interval = null,
            )
            val cpu = snapshot.cpu?.aggregate ?: 0.0
            val mem = snapshot.memory?.percent ?: 0.0
            val worstDisk = snapshot.disks.maxByOrNull { it.usage_percent }

            prefs.widgetSummary = buildString {
                append("CPU %.0f%% · RAM %.0f%%".format(cpu, mem))
                worstDisk?.let { append(" · %s %.0f%%".format(it.mountpoint, it.usage_percent)) }
            }
            prefs.widgetUpdatedAt = System.currentTimeMillis()
            StatusWidget().updateAll(applicationContext)
            Result.success()
        } catch (_: Throwable) {
            // Leave the previous summary in place; the widget's timestamp makes
            // the staleness visible without inventing a value.
            Result.retry()
        }
    }

    companion object {
        private const val WORK_NAME = "carbonpanel-widget-refresh"

        fun ensureScheduled(context: Context) {
            val request = PeriodicWorkRequestBuilder<StatusWidgetWorker>(
                15, TimeUnit.MINUTES,
            ).setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            ).build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }
    }
}

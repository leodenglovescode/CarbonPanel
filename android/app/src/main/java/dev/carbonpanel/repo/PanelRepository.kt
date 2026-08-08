package dev.carbonpanel.repo

import android.content.Context
import dev.carbonpanel.data.ContainerInfo
import dev.carbonpanel.data.HistoryPoint
import dev.carbonpanel.data.MetricsSnapshot
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.data.ServiceActionRequest
import dev.carbonpanel.data.SystemServiceInfo
import dev.carbonpanel.net.Api
import dev.carbonpanel.net.ApiClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.Dispatchers

sealed interface PollState {
    data object Connecting : PollState
    data class Connected(val snapshot: MetricsSnapshot, val endpoint: String) : PollState
    data class Error(val message: String) : PollState
    data object Unpaired : PollState
}

class PanelRepository(private val context: Context) {

    private val prefs get() = Prefs.get(context)

    private suspend fun api(): Pair<String, Api>? = ApiClient.resolve(context)

    /**
     * Emits metrics until the collector is cancelled.
     *
     * Deliberately a cold Flow with no internal scope: the caller collects it
     * under `repeatOnLifecycle(STARTED)`, so backgrounding the app cancels the
     * coroutine and stops every request. That is the entire background-battery
     * story for this app — no service, no wakelock, no socket to keep alive.
     *
     * [fields] should name only the sections on screen. A dashboard needs
     * cpu+memory+gpu, not the process table.
     */
    fun metricsStream(fields: String? = null): Flow<PollState> = flow {
        if (!prefs.isPaired) {
            emit(PollState.Unpaired)
            return@flow
        }
        emit(PollState.Connecting)

        var resolved = api()
        if (resolved == null) {
            emit(PollState.Error("No reachable address for this server"))
            return@flow
        }

        var consecutiveFailures = 0
        while (true) {
            val interval = prefs.pollIntervalSeconds
            try {
                val snapshot = resolved!!.second.metricsCurrent(
                    fields = fields,
                    interval = interval,
                )
                consecutiveFailures = 0
                emit(PollState.Connected(snapshot, resolved!!.first))
            } catch (t: Throwable) {
                consecutiveFailures++
                // The phone may have moved between networks (home wifi to
                // mobile data), which invalidates the endpoint we settled on
                // rather than the pairing. Re-resolve before giving up.
                if (consecutiveFailures >= 2) {
                    ApiClient.clearCache()
                    resolved = api()
                    if (resolved == null) {
                        emit(PollState.Error("Server unreachable"))
                        delay(5_000)
                        resolved = api()
                        continue
                    }
                } else {
                    emit(PollState.Error(t.message ?: "Request failed"))
                }
            }
            delay((interval * 1000).toLong().coerceAtLeast(400L))
        }
    }.flowOn(Dispatchers.IO)

    suspend fun history(): List<HistoryPoint> =
        api()?.second?.metricsHistory() ?: emptyList()

    suspend fun containers(): List<ContainerInfo> =
        api()?.second?.containers() ?: emptyList()

    suspend fun containerAction(id: String, action: String): Result<String> = runCatching {
        val client = api()?.second ?: error("Server unreachable")
        val response = when (action) {
            "start" -> client.startContainer(id)
            "stop" -> client.stopContainer(id)
            "restart" -> client.restartContainer(id)
            else -> error("Unknown action $action")
        }
        if (!response.success) error(response.output.ifBlank { "$action failed" })
        response.output
    }

    suspend fun services(starredOnly: Boolean = false): List<SystemServiceInfo> =
        api()?.second?.systemServices(starredOnly = starredOnly) ?: emptyList()

    suspend fun serviceAction(name: String, action: String): Result<String> = runCatching {
        val client = api()?.second ?: error("Server unreachable")
        val response = client.systemServiceAction(name, ServiceActionRequest(action))
        if (!response.success) error(response.output.ifBlank { "$action failed" })
        response.output
    }

    fun unpair() {
        prefs.clear()
        ApiClient.clearCache()
    }
}

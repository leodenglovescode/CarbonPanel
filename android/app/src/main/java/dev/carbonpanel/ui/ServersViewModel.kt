package dev.carbonpanel.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dev.carbonpanel.data.DiskInfo
import dev.carbonpanel.data.MetricsSnapshot
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.net.ApiClient
import dev.carbonpanel.ui.components.isPseudoMount
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.sync.withPermit

/** A failed preview never prevents opening or monitoring the other servers. */
data class ServerPreview(
    val snapshot: MetricsSnapshot? = null,
    val endpoint: String? = null,
    val storagePercent: Double? = null,
    val online: Boolean = false,
    val error: String? = null,
)

@OptIn(ExperimentalCoroutinesApi::class)
class ServersViewModel(app: Application) : AndroidViewModel(app) {
    private val ids = MutableStateFlow<List<String>>(emptyList())
    fun setServers(serverIds: List<String>) { ids.value = serverIds }

    // Only the visible chooser collects this flow. Fast servers render as
    // soon as they answer, independently of unreachable servers in the list.
    val previews: StateFlow<Map<String, ServerPreview>> = ids.flatMapLatest { servers ->
        channelFlow {
            var previous = emptyMap<String, ServerPreview>()
            val limit = Semaphore(3)
            val lock = Mutex()
            while (currentCoroutineContext().isActive) {
                coroutineScope {
                    servers.forEach { id -> launch(Dispatchers.IO) {
                        limit.withPermit {
                            val lastKnown = lock.withLock { previous[id] } ?: ServerPreview()
                            val preview = loadPreview(app, id, lastKnown)
                            lock.withLock {
                                previous = previous + (id to preview)
                                send(previous)
                            }
                        }
                    } }
                }
                delay(15_000)
            }
        }
    }.stateIn(viewModelScope,
        SharingStarted.WhileSubscribed(stopTimeoutMillis = 0, replayExpirationMillis = 0), emptyMap())

    private suspend fun loadPreview(app: Application, id: String, previous: ServerPreview): ServerPreview = try {
        withTimeout(12_000) {
            val prefs = Prefs.get(app).forServer(id)
            val (endpoint, api) = ApiClient.resolve(app, prefs) ?: error("No address reachable")
            val snapshot = api.metricsCurrent(fields = "cpu,memory,system")
            val storage = try {
                withTimeoutOrNull(4_000) { fleetStorageUsage(api.disks()) }
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) { null }
            ServerPreview(snapshot, endpoint, storage, online = true)
        }
    } catch (error: TimeoutCancellationException) {
        previous.copy(online = false, error = "Timed out")
    } catch (error: CancellationException) {
        throw error
    } catch (error: Exception) {
        val message = if (error is retrofit2.HttpException && error.code() == 401)
            "Pairing expired" else "Unreachable"
        previous.copy(online = false, error = message)
    }
}

internal fun fleetStorageUsage(disks: List<DiskInfo>): Double? {
    val volumes = disks.filterNot {
        it.is_virtual || isPseudoMount(it.mountpoint, it.device, it.fstype)
    }.distinctBy { it.device }.filter {
        it.total_gb.isFinite() && it.total_gb > 0 && it.used_gb.isFinite()
    }
    val total = volumes.sumOf { it.total_gb }
    return if (total > 0) (volumes.sumOf { it.used_gb } / total * 100).coerceIn(0.0, 100.0) else null
}

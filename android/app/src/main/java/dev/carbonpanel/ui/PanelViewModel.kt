package dev.carbonpanel.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dev.carbonpanel.data.ContainerInfo
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.data.SystemServiceInfo
import dev.carbonpanel.repo.PanelRepository
import dev.carbonpanel.repo.PollState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class PanelViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = PanelRepository(app)
    private val prefs get() = Prefs.get(getApplication())

    /**
     * Metrics stream, started only while something is collecting it and
     * stopped 5s after the last collector goes away.
     *
     * `SharingStarted.WhileSubscribed` is what ties polling to the UI being
     * on screen: the screens collect with `collectAsStateWithLifecycle`, which
     * unsubscribes when the app is backgrounded, which stops the requests.
     *
     * The dashboard doesn't render the process table, so it isn't requested —
     * that alone cuts the payload by roughly two thirds.
     */
    val metrics: StateFlow<PollState> = repo
        .metricsStream(fields = "cpu,memory,gpu,disks,system")
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = PollState.Connecting,
        )

    // ── Docker ─────────────────────────────────────────────────────────────

    private val _containers = MutableStateFlow<List<ContainerInfo>>(emptyList())
    val containers: StateFlow<List<ContainerInfo>> = _containers.asStateFlow()

    private val _busyIds = MutableStateFlow<Set<String>>(emptySet())
    val busyIds: StateFlow<Set<String>> = _busyIds.asStateFlow()

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message.asStateFlow()

    fun clearMessage() {
        _message.value = null
    }

    fun refreshContainers() {
        viewModelScope.launch {
            runCatching { repo.containers() }
                .onSuccess { _containers.value = it }
                .onFailure { _message.value = it.message ?: "Could not list containers" }
        }
    }

    fun containerAction(id: String, action: String) {
        viewModelScope.launch {
            _busyIds.value = _busyIds.value + id
            repo.containerAction(id, action)
                .onFailure { _message.value = it.message }
            _busyIds.value = _busyIds.value - id
            refreshContainers()
        }
    }

    // ── System services ────────────────────────────────────────────────────

    private val _services = MutableStateFlow<List<SystemServiceInfo>>(emptyList())
    val services: StateFlow<List<SystemServiceInfo>> = _services.asStateFlow()

    private val _busyServices = MutableStateFlow<Set<String>>(emptySet())
    val busyServices: StateFlow<Set<String>> = _busyServices.asStateFlow()

    fun refreshServices() {
        viewModelScope.launch {
            runCatching { repo.services() }
                .onSuccess { _services.value = it }
                .onFailure { _message.value = it.message ?: "Could not list services" }
        }
    }

    fun serviceAction(name: String, action: String) {
        viewModelScope.launch {
            _busyServices.value = _busyServices.value + name
            repo.serviceAction(name, action)
                .onFailure { _message.value = it.message }
            _busyServices.value = _busyServices.value - name
            refreshServices()
        }
    }

    // ── Session ────────────────────────────────────────────────────────────

    val serverName: String get() = prefs.serverName ?: "CarbonPanel"

    var pollInterval: Float
        get() = prefs.pollIntervalSeconds
        set(value) {
            prefs.pollIntervalSeconds = value
        }

    fun unpair() = repo.unpair()
}

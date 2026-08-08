package dev.carbonpanel.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dev.carbonpanel.data.*
import dev.carbonpanel.net.ApiClient
import dev.carbonpanel.repo.PanelRepository
import dev.carbonpanel.repo.PollState
import dev.carbonpanel.ui.components.isPseudoMount
import dev.carbonpanel.ui.theme.AccentChoice
import dev.carbonpanel.ui.theme.ThemeMode
import dev.carbonpanel.widget.WidgetBridge
import dev.carbonpanel.widget.StatusWidgetWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/** systemd unit types the services screen can show. */
enum class UnitKind(val label: String) {
    All("All"), Services("Services"), Timers("Timers");

    fun matches(unitName: String): Boolean = when (this) {
        All -> true
        Services -> !unitName.endsWith(".timer")
        Timers -> unitName.endsWith(".timer")
    }
}

class PanelViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = PanelRepository(app)
    private val prefs get() = Prefs.get(getApplication())

    // ── transient UI messages ──────────────────────────────────────────────

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message.asStateFlow()
    fun clearMessage() { _message.value = null }
    private fun say(text: String) { _message.value = text }

    /** Ids/keys with an action in flight, so rows can show a spinner. */
    private val _busy = MutableStateFlow<Set<String>>(emptySet())
    val busy: StateFlow<Set<String>> = _busy.asStateFlow()

    private inline fun withBusy(key: String, crossinline block: suspend () -> Unit) {
        viewModelScope.launch {
            _busy.value = _busy.value + key
            try { block() } finally { _busy.value = _busy.value - key }
        }
    }

    // ── live metrics ───────────────────────────────────────────────────────

    /**
     * Started only while something is collecting, stopped 5s after the last
     * collector goes away. Screens collect with collectAsStateWithLifecycle,
     * so backgrounding the app tears the polling down — the whole battery
     * story in one line.
     *
     * The dashboard doesn't render a process table, so it isn't requested;
     * that alone is roughly two thirds of the payload.
     */
    // No "disks" here: the dashboard reads storage from /disks, which carries
    // fstype and is_virtual, so keeping the snapshot's partition list would be
    // both redundant and a second, inconsistent source of truth.
    val metrics: StateFlow<PollState> = repo
        .metricsStream(fields = "cpu,memory,gpu,network,system")
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), PollState.Connecting)

    private val _history = MutableStateFlow<List<HistoryPoint>>(emptyList())
    val history: StateFlow<List<HistoryPoint>> = _history.asStateFlow()

    fun loadHistory() = viewModelScope.launch {
        repo.history().onSuccess { _history.value = it }
    }

    /**
     * Extends the history series with a live snapshot.
     *
     * /metrics/history is the server's own ring buffer and is only fetched
     * once per screen entry; without this the chart would sit frozen while the
     * numbers above it updated every poll. Capped at the same 300 points the
     * server keeps so the series can't grow without bound.
     */
    fun appendHistory(snapshot: MetricsSnapshot) {
        val cpu = snapshot.cpu?.aggregate ?: return
        val mem = snapshot.memory?.percent ?: return
        val last = _history.value.lastOrNull()
        if (last != null && snapshot.ts <= last.ts) return
        val point = HistoryPoint(
            ts = snapshot.ts,
            cpu = cpu,
            mem = mem,
            gpu = snapshot.gpu?.devices?.firstOrNull()?.utilization_percent,
        )
        _history.value = (_history.value + point).takeLast(300)
    }

    // ── docker ─────────────────────────────────────────────────────────────

    val containers = MutableStateFlow<Load<List<ContainerInfo>>>(Load.Loading)

    fun loadContainers(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) containers.markRefreshing() else if (containers.value !is Load.Ok) containers.value = Load.Loading
        containers.applyResult(repo.containers())
    }

    fun containerAction(id: String, name: String, action: String) = withBusy(id) {
        repo.containerAction(id, action)
            .onSuccess { say("$name ${action}ed") }
            .onFailure { say(it.message ?: "$action failed") }
        containers.applyResult(repo.containers())
    }

    // ── system services ────────────────────────────────────────────────────

    val services = MutableStateFlow<Load<List<SystemServiceInfo>>>(Load.Loading)
    private val _showAllServices = MutableStateFlow(false)
    val showAllServices: StateFlow<Boolean> = _showAllServices.asStateFlow()

    fun toggleShowAllServices() {
        _showAllServices.value = !_showAllServices.value
        loadServices(refresh = true)
    }

    /** Unit-type filter. The server returns .service and .timer units together. */
    private val _serviceKind = MutableStateFlow(UnitKind.All)
    val serviceKind: StateFlow<UnitKind> = _serviceKind.asStateFlow()

    fun setServiceKind(kind: UnitKind) {
        _serviceKind.value = kind
        // Timers are only in the response when the server is asked for every
        // unit file, so selecting them implies widening the scope — otherwise
        // the filter would just show an empty list and look broken.
        if (kind == UnitKind.Timers && !_showAllServices.value) {
            _showAllServices.value = true
            loadServices(refresh = true)
        }
    }

    private val _serviceQuery = MutableStateFlow("")
    val serviceQuery: StateFlow<String> = _serviceQuery.asStateFlow()
    fun setServiceQuery(q: String) { _serviceQuery.value = q }

    private val _dockerQuery = MutableStateFlow("")
    val dockerQuery: StateFlow<String> = _dockerQuery.asStateFlow()
    fun setDockerQuery(q: String) { _dockerQuery.value = q }

    fun loadServices(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) services.markRefreshing() else if (services.value !is Load.Ok) services.value = Load.Loading
        services.applyResult(repo.services(includeAll = _showAllServices.value))
    }

    fun serviceAction(name: String, action: String) = withBusy(name) {
        repo.serviceAction(name, action)
            .onSuccess { say("$name ${action}ed") }
            .onFailure { say(it.message ?: "$action failed") }
        services.applyResult(repo.services(includeAll = _showAllServices.value))
    }

    fun serviceAutostart(name: String, enabled: Boolean) = withBusy(name) {
        repo.serviceAutostart(name, enabled)
            .onFailure { say(it.message ?: "Could not change autostart") }
        services.applyResult(repo.services(includeAll = _showAllServices.value))
    }

    fun serviceStar(name: String, starred: Boolean) = withBusy(name) {
        repo.serviceStar(name, starred).onFailure { say(it.message ?: "Could not star") }
        services.applyResult(repo.services(includeAll = _showAllServices.value))
    }

    // ── sites ──────────────────────────────────────────────────────────────

    val sites = MutableStateFlow<Load<List<SiteResponse>>>(Load.Loading)

    fun loadSites(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) sites.markRefreshing() else if (sites.value !is Load.Ok) sites.value = Load.Loading
        sites.applyResult(repo.sites())
    }

    fun siteAction(id: String, name: String, action: String) = withBusy(id) {
        repo.siteAction(id, action)
            .onSuccess { say("$name ${action}ed") }
            .onFailure { say(it.message ?: "$action failed") }
        sites.applyResult(repo.sites())
    }

    val siteConfig = MutableStateFlow<Load<ConfigReadResponse>>(Load.Loading)
    val siteTraffic = MutableStateFlow<Load<SiteTrafficResponse>>(Load.Loading)

    fun loadSiteDetail(id: String) = viewModelScope.launch {
        siteConfig.value = Load.Loading
        siteTraffic.value = Load.Loading
        siteConfig.applyResult(repo.siteConfig(id))
        siteTraffic.applyResult(repo.siteTraffic(id))
    }

    // ── disks ──────────────────────────────────────────────────────────────

    val disks = MutableStateFlow<Load<List<DiskInfo>>>(Load.Loading)

    fun loadDisks(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) disks.markRefreshing() else if (disks.value !is Load.Ok) disks.value = Load.Loading
        disks.applyResult(repo.disks())
    }

    fun refreshSmart() = withBusy("smart") {
        repo.refreshSmart()
            .onSuccess { say("SMART rescan started") }
            .onFailure { say(it.message ?: "SMART refresh failed") }
        disks.applyResult(repo.disks())
    }

    fun unmount(mountpoint: String) = withBusy(mountpoint) {
        repo.unmount(mountpoint)
            .onSuccess { say("Unmounted $mountpoint") }
            .onFailure { say(it.message ?: "Unmount failed") }
        disks.applyResult(repo.disks())
    }

    // ── cron ───────────────────────────────────────────────────────────────

    val cronEntries = MutableStateFlow<Load<List<CronEntry>>>(Load.Loading)
    val managedCron = MutableStateFlow<Load<List<CronJob>>>(Load.Loading)

    fun loadCron(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) { cronEntries.markRefreshing(); managedCron.markRefreshing() }
        cronEntries.applyResult(repo.cronEntries())
        managedCron.applyResult(repo.managedCron())
    }

    fun saveCron(id: String?, label: String, schedule: String, command: String) = withBusy("cron") {
        val result = if (id == null) repo.createCron(label, schedule, command)
                     else repo.updateCron(id, label, schedule, command)
        result.onSuccess { say(if (id == null) "Job created" else "Job updated") }
              .onFailure { say(it.message ?: "Could not save job") }
        managedCron.applyResult(repo.managedCron())
        cronEntries.applyResult(repo.cronEntries())
    }

    fun deleteCron(id: String) = withBusy(id) {
        repo.deleteCron(id).onFailure { say(it.message ?: "Could not delete job") }
        managedCron.applyResult(repo.managedCron())
        cronEntries.applyResult(repo.cronEntries())
    }

    // ── apps / ports ───────────────────────────────────────────────────────

    val apps = MutableStateFlow<Load<List<AppInfo>>>(Load.Loading)

    fun loadApps(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) apps.markRefreshing() else if (apps.value !is Load.Ok) apps.value = Load.Loading
        apps.applyResult(repo.apps())
    }

    fun setAppLabel(port: Int, label: String) = withBusy("port$port") {
        if (label.isBlank()) repo.clearAppLabel(port) else repo.setAppLabel(port, label)
        apps.applyResult(repo.apps())
    }

    fun killApp(port: Int, force: Boolean) = withBusy("port$port") {
        repo.killApp(port, force)
            .onSuccess { say("Killed process on port $port") }
            .onFailure { say(it.message ?: "Kill failed") }
        apps.applyResult(repo.apps())
    }

    // ── processes ──────────────────────────────────────────────────────────

    val processes = MutableStateFlow<Load<List<ProcessMetrics>>>(Load.Loading)
    private val _processSort = MutableStateFlow("cpu")
    val processSort: StateFlow<String> = _processSort.asStateFlow()

    fun setProcessSort(sort: String) { _processSort.value = sort; loadProcesses(refresh = true) }

    fun loadProcesses(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) processes.markRefreshing() else if (processes.value !is Load.Ok) processes.value = Load.Loading
        processes.applyResult(
            repo.snapshot(fields = "processes").map { it.processes }
        )
    }

    fun killProcess(pid: Int, name: String, force: Boolean) = withBusy("pid$pid") {
        repo.killProcess(pid, force)
            .onSuccess { say("Killed $name ($pid)") }
            .onFailure { say(it.message ?: "Kill failed") }
        loadProcesses(refresh = true)
    }

    // ── sessions / bookmarks / webhooks / logs ─────────────────────────────

    val sessions = MutableStateFlow<Load<List<SessionInfo>>>(Load.Loading)
    fun loadSessions(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) sessions.markRefreshing()
        sessions.applyResult(repo.sessions())
    }

    val bookmarks = MutableStateFlow<Load<List<BookmarkOut>>>(Load.Loading)
    fun loadBookmarks(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) bookmarks.markRefreshing()
        bookmarks.applyResult(repo.bookmarks())
    }
    fun addBookmark(title: String, url: String) = withBusy("bookmark") {
        repo.createBookmark(title, url).onFailure { say(it.message ?: "Could not add bookmark") }
        bookmarks.applyResult(repo.bookmarks())
    }
    fun deleteBookmark(id: String) = withBusy(id) {
        repo.deleteBookmark(id).onFailure { say(it.message ?: "Could not delete") }
        bookmarks.applyResult(repo.bookmarks())
    }

    val webhooks = MutableStateFlow<Load<List<WebhookResponse>>>(Load.Loading)
    fun loadWebhooks(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) webhooks.markRefreshing()
        webhooks.applyResult(repo.webhooks())
    }
    fun addWebhook(label: String, url: String, events: List<String>) = withBusy("webhook") {
        repo.createWebhook(label, url, events).onFailure { say(it.message ?: "Could not add webhook") }
        webhooks.applyResult(repo.webhooks())
    }
    fun toggleWebhook(id: String, enabled: Boolean) = withBusy(id) {
        repo.updateWebhook(id, WebhookUpdate(enabled = enabled))
            .onFailure { say(it.message ?: "Could not update webhook") }
        webhooks.applyResult(repo.webhooks())
    }
    fun deleteWebhook(id: String) = withBusy(id) {
        repo.deleteWebhook(id).onFailure { say(it.message ?: "Could not delete") }
        webhooks.applyResult(repo.webhooks())
    }

    val logs = MutableStateFlow<Load<List<String>>>(Load.Loading)
    fun loadLogs(refresh: Boolean = false) = viewModelScope.launch {
        if (refresh) logs.markRefreshing()
        logs.applyResult(repo.serviceLogs().map { it.lines })
    }

    // ── account / settings ─────────────────────────────────────────────────

    val account = MutableStateFlow<Load<UserInfo>>(Load.Loading)
    val devices = MutableStateFlow<Load<List<DeviceOut>>>(Load.Loading)
    val version = MutableStateFlow<Load<VersionStatus>>(Load.Loading)
    val proxy = MutableStateFlow<Load<ProxyConfig>>(Load.Loading)

    fun loadSettings(refresh: Boolean = false) = viewModelScope.launch {
        account.applyResult(repo.me())
        devices.applyResult(repo.devices())
        version.applyResult(repo.version())
        proxy.applyResult(repo.proxy())
    }

    fun revokeDevice(id: String) = withBusy(id) {
        repo.revokeDevice(id).onFailure { say(it.message ?: "Could not revoke") }
        devices.applyResult(repo.devices())
    }

    fun checkUpdates() = withBusy("update") {
        repo.checkUpdates()
            .onSuccess { say("Update check started") }
            .onFailure { say(it.message ?: "Check failed") }
        version.applyResult(repo.version())
    }

    fun setProxy(config: ProxyConfig) = withBusy("proxy") {
        repo.setProxy(config)
            .onSuccess { say("Proxy saved") }
            .onFailure { say(it.message ?: "Could not save proxy") }
        proxy.applyResult(repo.proxy())
    }

    // ── server addresses ───────────────────────────────────────────────────

    private val _endpoints = MutableStateFlow(prefs.endpoints)
    val endpoints: StateFlow<List<String>> = _endpoints.asStateFlow()

    private val _activeEndpoint = MutableStateFlow(prefs.lastGoodEndpoint)
    val activeEndpoint: StateFlow<String?> = _activeEndpoint.asStateFlow()

    /** url -> reachable?  null while a probe is in flight. */
    private val _reachability = MutableStateFlow<Map<String, Boolean?>>(emptyMap())
    val reachability: StateFlow<Map<String, Boolean?>> = _reachability.asStateFlow()

    fun refreshEndpoints() {
        _endpoints.value = prefs.endpoints
        _activeEndpoint.value = prefs.lastGoodEndpoint
    }

    fun addEndpoint(raw: String) {
        val url = raw.trim().trimEnd('/')
        when {
            url.isEmpty() -> return
            !url.startsWith("http://") && !url.startsWith("https://") ->
                say("Address must start with http:// or https://")
            !ApiClient.isPermittedEndpoint(url) ->
                say("Refusing plain HTTP to a public address — use https:// or a VPN address")
            url in _endpoints.value -> say("Already in the list")
            else -> {
                prefs.endpoints = _endpoints.value + url
                refreshEndpoints()
                testEndpoint(url)
            }
        }
    }

    fun removeEndpoint(url: String) {
        val remaining = _endpoints.value.filterNot { it == url }
        if (remaining.isEmpty()) {
            say("Keep at least one address, or the app can't reach the server")
            return
        }
        prefs.endpoints = remaining
        if (prefs.lastGoodEndpoint == url) prefs.lastGoodEndpoint = remaining.first()
        refreshEndpoints()
    }

    /** Moves an address up the list, which is the order the app tries them in. */
    fun promoteEndpoint(url: String) {
        val list = _endpoints.value.toMutableList()
        val i = list.indexOf(url)
        if (i <= 0) return
        list.removeAt(i)
        list.add(i - 1, url)
        prefs.endpoints = list
        refreshEndpoints()
    }

    fun testEndpoint(url: String) = viewModelScope.launch {
        _reachability.value = _reachability.value + (url to null)
        val ok = withContext(Dispatchers.IO) {
            withTimeoutOrNull(6_000) {
                runCatching { ApiClient.forBaseUrl(getApplication(), url).ping().isSuccessful }
                    .getOrDefault(false)
            } ?: false
        }
        _reachability.value = _reachability.value + (url to ok)
    }

    fun testAllEndpoints() {
        _endpoints.value.forEach { testEndpoint(it) }
    }

    /** Forces re-selection, e.g. after moving networks. */
    fun reconnect() = viewModelScope.launch {
        ApiClient.clearCache()
        val resolved = ApiClient.resolve(getApplication())
        refreshEndpoints()
        say(resolved?.let { "Connected via ${it.first}" } ?: "No address reachable")
    }

    // ── widget ─────────────────────────────────────────────────────────────

    private val _widgetDisk = MutableStateFlow(prefs.widgetDisk)
    val widgetDisk: StateFlow<String> = _widgetDisk.asStateFlow()

    private val _widgetIface = MutableStateFlow(prefs.widgetIface)
    val widgetIface: StateFlow<String> = _widgetIface.asStateFlow()

    private val _widgetNetUnit = MutableStateFlow(NetUnit.from(prefs.widgetNetUnit))
    val widgetNetUnit: StateFlow<NetUnit> = _widgetNetUnit.asStateFlow()

    private val _widgetRefresh = MutableStateFlow(prefs.widgetRefreshMinutes)
    val widgetRefresh: StateFlow<Int> = _widgetRefresh.asStateFlow()

    /** Interfaces worth offering — container plumbing is excluded. */
    val ifaceChoices: List<String>
        get() = (metrics.value as? PollState.Connected)?.snapshot?.network
            ?.map { it.iface }
            ?.filterNot { n ->
                listOf("veth", "br-", "docker", "lo", "virbr")
                    .any { n.startsWith(it, ignoreCase = true) }
            }
            .orEmpty()

    /** Real disks, from the same source the Storage screen uses. */
    val diskChoices: List<String>
        get() = disks.value.dataOrNull
            ?.filterNot { it.is_virtual || isPseudoMount(it.mountpoint, it.device, it.fstype) }
            ?.map { it.mountpoint }
            .orEmpty()

    fun setWidgetDisk(mountpoint: String) {
        prefs.widgetDisk = mountpoint
        _widgetDisk.value = mountpoint
        StatusWidgetWorker.refreshNow(getApplication())
        repaintWidget()
    }

    fun setWidgetIface(iface: String) {
        prefs.widgetIface = iface
        _widgetIface.value = iface
        StatusWidgetWorker.refreshNow(getApplication())
        repaintWidget()
    }

    fun setWidgetNetUnit(unit: NetUnit) {
        prefs.widgetNetUnit = unit.name
        _widgetNetUnit.value = unit
        StatusWidgetWorker.refreshNow(getApplication())
        repaintWidget()
    }

    fun setWidgetRefresh(minutes: Int) {
        prefs.widgetRefreshMinutes = minutes
        _widgetRefresh.value = prefs.widgetRefreshMinutes
        StatusWidgetWorker.reschedule(getApplication())
    }

    fun refreshWidgetNow() {
        StatusWidgetWorker.refreshNow(getApplication())
        repaintWidget()
        say("Widget refresh queued")
    }

    // ── session ────────────────────────────────────────────────────────────

    val serverName: String get() = prefs.serverName ?: "CarbonPanel"
    val username: String get() = prefs.username ?: "—"

    var pollInterval: Float
        get() = prefs.pollIntervalSeconds
        set(v) { prefs.pollIntervalSeconds = v }

    // ── appearance ─────────────────────────────────────────────────────────

    private val _backdropEnabled = MutableStateFlow(prefs.backdropEnabled)
    val backdropEnabled: StateFlow<Boolean> = _backdropEnabled.asStateFlow()

    fun setBackdropEnabled(enabled: Boolean) {
        prefs.backdropEnabled = enabled
        _backdropEnabled.value = enabled
    }

    private val _themeMode = MutableStateFlow(ThemeMode.valueOf(prefs.themeMode))
    val themeMode: StateFlow<ThemeMode> = _themeMode.asStateFlow()

    fun setThemeMode(mode: ThemeMode) {
        prefs.themeMode = mode.name
        _themeMode.value = mode
        repaintWidget()
    }

    private val _accent = MutableStateFlow(AccentChoice.from(prefs.accent))
    val accent: StateFlow<AccentChoice> = _accent.asStateFlow()

    fun setAccent(choice: AccentChoice) {
        if (choice == AccentChoice.Dynamic && !AccentChoice.dynamicSupported) {
            say("Material You needs Android 12 or newer")
            return
        }
        prefs.accent = choice.name
        _accent.value = choice
        repaintWidget()
    }

    /**
     * Redraws the widget from cached data after an appearance change.
     *
     * Not a data refresh — the numbers are unchanged and a network round trip
     * to recolour a widget would be waste. The widget runs in the launcher's
     * process and can't observe the app's theme state, so it has to be told.
     */
    private fun repaintWidget() = viewModelScope.launch {
        // Failures are surfaced rather than swallowed. A silent runCatching
        // here meant a widget that refused to repaint left no trace anywhere,
        // which is the worst possible combination.
        // Pushes the current appearance into Glance's store and redraws.
        // updateAll() alone is not enough: the composable observes Glance
        // state, not SharedPreferences, so without a state write there is
        // nothing to invalidate and a live session simply re-sends the old
        // RemoteViews.
        runCatching { WidgetBridge.push(getApplication()) }
            .onFailure { say("Could not repaint widget: ${it.message}") }
    }

    fun unpair() = repo.unpair()
}

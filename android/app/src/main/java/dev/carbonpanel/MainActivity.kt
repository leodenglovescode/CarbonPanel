package dev.carbonpanel

import android.os.Bundle
import android.app.Application
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.key
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.ViewModelProvider
import androidx.compose.material3.TextButton
import dev.carbonpanel.net.ApiClient
import dev.carbonpanel.widget.WidgetBridge
import dev.carbonpanel.pairing.PairState
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.LocalOnBackPressedDispatcherOwner
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import dev.carbonpanel.ui.components.LocalizedText as Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.awaitCancellation
import androidx.lifecycle.viewmodel.compose.viewModel
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.pairing.PairingViewModel
import dev.carbonpanel.ui.Dest
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.ServersViewModel
import androidx.compose.material.icons.filled.Settings
import dev.carbonpanel.ui.components.Backdrop
import dev.carbonpanel.ui.components.localizeUiText
import dev.carbonpanel.ui.screens.*
import dev.carbonpanel.ui.theme.CarbonTheme
import dev.carbonpanel.widget.StatusWidgetWorker

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Opening the app is the strongest signal that its numbers are about
        // to be looked at, and the widget refreshes on a 30-minute cadence.
        // One request here keeps the two from disagreeing on the same screen.
        // Guarded on isPaired so the pairing flow doesn't fire a doomed fetch —
        // the claim path triggers its own refresh once a token exists.
        if (Prefs.get(this).isPaired) StatusWidgetWorker.refreshNow(this)

        setContent { CarbonPanelRoot() }
    }
}

@Composable
private fun CarbonPanelRoot() {
    val pairingViewModel: PairingViewModel = viewModel()
    val serversViewModel: ServersViewModel = viewModel()
    val context = LocalContext.current
    var servers by remember { mutableStateOf(Prefs.get(context).servers) }
    var selected by rememberSaveable {
        mutableStateOf(servers.singleOrNull()?.id)
    }
    var adding by rememberSaveable { mutableStateOf(servers.isEmpty()) }
    var appSettings by rememberSaveable { mutableStateOf(false) }
    val pairState by pairingViewModel.state.collectAsStateWithLifecycle()

    var chooserVersion by remember { mutableStateOf(dev.carbonpanel.data.ChooserBackground.version(context)) }
    fun reload() {
        servers = Prefs.get(context).servers
        chooserVersion = dev.carbonpanel.data.ChooserBackground.version(context)
    }
    fun open(id: String) {
        Prefs.get(context).activate(id)
        ApiClient.clearCache()
        selected = id
        appSettings = false
        adding = false
        StatusWidgetWorker.refreshNow(context)
    }

    // A fresh store on each visit cancels the previous server's polling and
    // actions, and prevents cached screen data or navigation crossing servers.
    val sessionKey = when { adding -> "pairing"; appSettings -> "app-settings"; else -> selected ?: "servers" }
    val store = remember(sessionKey) { ViewModelStore() }
    DisposableEffect(store) { onDispose { store.clear() } }
    val panelViewModel = remember(store) {
        val owner = object : ViewModelStoreOwner { override val viewModelStore = store }
        ViewModelProvider(owner, ViewModelProvider.AndroidViewModelFactory.getInstance(
            context.applicationContext as Application,
        ))[PanelViewModel::class.java]
    }
    val themeMode by panelViewModel.themeMode.collectAsStateWithLifecycle()
    val accent by panelViewModel.accent.collectAsStateWithLifecycle()
    val backdropEnabled by panelViewModel.backdropEnabled.collectAsStateWithLifecycle()
    val backgrounds by panelViewModel.backgrounds.collectAsStateWithLifecycle()
    val serverOpen = selected != null && !adding && !appSettings
    val chooserOpen = selected == null && !adding && !appSettings
    val background = backgrounds.targets["android-app"]
    val showBackdrop = serverOpen && backdropEnabled && background != null &&
        (background.type == "gradient" || (background.type == "image" && background.version > 0))
    val rootLifecycleOwner = LocalLifecycleOwner.current
    LaunchedEffect(rootLifecycleOwner, panelViewModel, serverOpen) {
        rootLifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                if (serverOpen) panelViewModel.refreshBackgrounds().join()
                kotlinx.coroutines.delay(30_000)
            }
        }
    }

    LaunchedEffect(sessionKey, servers) { WidgetBridge.push(context) }
    BackHandler(enabled = appSettings && !adding) {
        reload()
        appSettings = false
        if (servers.isEmpty()) adding = true
    }
    BackHandler(enabled = adding && servers.isNotEmpty() && pairState !is PairState.Working) {
        pairingViewModel.reset()
        adding = false
    }

    CarbonTheme(mode = themeMode, accent = accent, hasBackdrop = showBackdrop || (chooserOpen && chooserVersion > 0), surfaceTransparency = if (serverOpen) backgrounds.surfaceTransparency else 0) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            key(sessionKey) {
                Backdrop(enabled = showBackdrop, config = background, target = "android-app") {
                    dev.carbonpanel.ui.components.LocalChooserBackdrop(enabled = chooserOpen, version = chooserVersion) {
                        when {
                            adding -> Box(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing)) {
                                PairingScreen(pairingViewModel, onPaired = {
                                    reload()
                                    open(Prefs.get(context).serverId)
                                })
                                if (servers.isNotEmpty()) TextButton(
                                    enabled = pairState !is PairState.Working,
                                    onClick = { pairingViewModel.reset(); adding = false },
                                ) { Text("Cancel") }
                            }
                            appSettings -> AppSettingsScreen(
                                viewModel = panelViewModel,
                                servers = servers,
                                activeServerId = Prefs.get(context).activeServerId,
                                onBack = { reload(); appSettings = false; if (servers.isEmpty()) adding = true },
                                onAdd = { pairingViewModel.reset(); adding = true },
                                onRename = { id, name -> Prefs.get(context).renameServer(id, name); reload() },
                                onRemove = { id ->
                                    Prefs.get(context).removeServer(id)
                                    ApiClient.clearCache()
                                    reload()
                                    if (selected == id) selected = null
                                    StatusWidgetWorker.refreshNow(context)
                                },
                            )
                            selected == null -> ServersScreen(
                                servers = servers,
                                viewModel = serversViewModel,
                                onSelect = { open(it) },
                                onSettings = { appSettings = true },
                            )
                            else -> MainScaffold(
                                viewModel = panelViewModel,
                                transparent = showBackdrop,
                                onServers = { reload(); selected = null },
                                onAppSettings = { appSettings = true },
                                onUnpair = {
                                    ApiClient.clearCache()
                                    reload()
                                    selected = null
                                    if (servers.isEmpty()) { pairingViewModel.reset(); adding = true }
                                    StatusWidgetWorker.refreshNow(context)
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MainScaffold(
    viewModel: PanelViewModel,
    transparent: Boolean,
    onUnpair: () -> Unit,
    onServers: () -> Unit,
    onAppSettings: () -> Unit,
) {
    val dockerInstalled by viewModel.dockerInstalled.collectAsStateWithLifecycle()
    val backDispatcher = LocalOnBackPressedDispatcherOwner.current?.onBackPressedDispatcher
    val lifecycleOwner = LocalLifecycleOwner.current
    var dest by rememberSaveable { mutableStateOf(Dest.Dashboard) }

    LaunchedEffect(lifecycleOwner, viewModel) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            viewModel.refreshDockerAvailability().join()
            awaitCancellation()
        }
    }
    LaunchedEffect(dockerInstalled) {
        if (dockerInstalled == false && dest == Dest.Docker) dest = Dest.Dashboard
    }
    var openSiteId by rememberSaveable { mutableStateOf<String?>(null) }
    val snackbarHost = remember { SnackbarHostState() }
    val message by viewModel.message.collectAsStateWithLifecycle()

    LaunchedEffect(message) {
        message?.let {
            snackbarHost.showSnackbar(it)
            viewModel.clearMessage()
        }
    }

    // Back should unwind the navigation the user actually performed, rather
    // than dropping them out of the app from a secondary screen.
    BackHandler(enabled = openSiteId != null || dest != Dest.Dashboard) {
        when {
            openSiteId != null -> openSiteId = null
            !dest.primary -> dest = Dest.More
            else -> dest = Dest.Dashboard
        }
    }

    val title = when {
        openSiteId != null -> localizeUiText("Site")
        dest == Dest.Dashboard -> viewModel.serverName
        else -> localizeUiText(dest.title)
    }
    val canGoBack = openSiteId != null || !dest.primary

    Scaffold(
        containerColor = if (transparent) Color.Transparent else MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbarHost) },
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(title, style = MaterialTheme.typography.titleMedium) },
                navigationIcon = {
                    if (canGoBack) {
                        IconButton(onClick = {
                            if (dest == Dest.Files) backDispatcher?.onBackPressed()
                            else if (openSiteId != null) openSiteId = null else dest = Dest.More
                        }) {
                            Icon(
                                Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = localizeUiText("Back"),
                            )
                        }
                    }
                },
                actions = {
                    TextButton(onClick = onServers) { Text("Servers") }
                    IconButton(onClick = onAppSettings) {
                        Icon(Icons.Default.Settings, contentDescription = localizeUiText("App settings"))
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
            ) {
                Dest.primaries(dockerInstalled).forEach { entry ->
                    NavigationBarItem(
                        selected = dest == entry || (entry == Dest.More && !dest.primary),
                        onClick = { dest = entry; openSiteId = null },
                        icon = {
                            Icon(entry.icon, contentDescription = localizeUiText(entry.title))
                        },
                        label = { Text(entry.title, style = MaterialTheme.typography.labelSmall) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
                        ),
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            AnimatedContent(
                targetState = openSiteId ?: dest.route,
                transitionSpec = {
                    (fadeIn(tween(180)) togetherWith fadeOut(tween(140)))
                },
                label = "screen",
            ) { key ->
                when {
                    openSiteId != null && key == openSiteId ->
                        SiteDetailScreen(viewModel, openSiteId!!)
                    else -> when (Dest.byRoute(key)) {
                        Dest.Dashboard -> DashboardScreen(viewModel)
                        Dest.Docker -> DockerScreen(viewModel)
                        Dest.Services -> ServicesScreen(viewModel)
                        Dest.Disks -> DisksScreen(viewModel)
                        Dest.More -> MoreScreen(onNavigate = { dest = it })
                        Dest.Files -> dev.carbonpanel.ui.screens.FilesScreen()
                        Dest.Sites -> SitesScreen(viewModel) { openSiteId = it }
                        Dest.Cron -> CronScreen(viewModel)
                        Dest.Apps -> AppsScreen(viewModel)
                        Dest.Processes -> ProcessesScreen(viewModel)
                        Dest.Sessions -> SessionsScreen(viewModel)
                        Dest.Bookmarks -> BookmarksScreen(viewModel)
                        Dest.Webhooks -> WebhooksScreen(viewModel)
                        Dest.Logs -> LogsScreen(viewModel)
                        Dest.Settings -> SettingsScreen(viewModel, onUnpair = onUnpair, onAppSettings = onAppSettings)
                        null -> DashboardScreen(viewModel)
                    }
                }
            }
        }
    }
}

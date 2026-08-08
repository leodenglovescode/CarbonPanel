package dev.carbonpanel

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
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
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.pairing.PairingViewModel
import dev.carbonpanel.ui.Dest
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.Backdrop
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
    val panelViewModel: PanelViewModel = viewModel()
    val context = LocalContext.current

    val themeMode by panelViewModel.themeMode.collectAsStateWithLifecycle()
    val accent by panelViewModel.accent.collectAsStateWithLifecycle()
    val backdropEnabled by panelViewModel.backdropEnabled.collectAsStateWithLifecycle()

    var paired by remember { mutableStateOf(Prefs.get(context).isPaired) }
    // The backdrop only exists once there's a server to fetch it from.
    val showBackdrop = paired && backdropEnabled

    CarbonTheme(mode = themeMode, accent = accent, hasBackdrop = showBackdrop) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background,
        ) {
            Backdrop(enabled = showBackdrop) {
                if (!paired) {
                    PairingScreen(
                        viewModel = pairingViewModel,
                        onPaired = {
                            paired = true
                            panelViewModel.refreshEndpoints()
                        },
                    )
                } else {
                    MainScaffold(
                        viewModel = panelViewModel,
                        transparent = showBackdrop,
                        onUnpair = {
                            pairingViewModel.reset()
                            paired = false
                        },
                    )
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
) {
    var dest by remember { mutableStateOf(Dest.Dashboard) }
    var openSiteId by remember { mutableStateOf<String?>(null) }
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
        openSiteId != null -> "Site"
        dest == Dest.Dashboard -> viewModel.serverName
        else -> dest.title
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
                            if (openSiteId != null) openSiteId = null else dest = Dest.More
                        }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                        }
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = Color.Transparent,
                ),
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = if (transparent) Color.Transparent
                                 else MaterialTheme.colorScheme.surface,
            ) {
                Dest.primaries.forEach { entry ->
                    NavigationBarItem(
                        selected = dest == entry || (entry == Dest.More && !dest.primary),
                        onClick = { dest = entry; openSiteId = null },
                        icon = { Icon(entry.icon, contentDescription = entry.title) },
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
                        Dest.Sites -> SitesScreen(viewModel) { openSiteId = it }
                        Dest.Cron -> CronScreen(viewModel)
                        Dest.Apps -> AppsScreen(viewModel)
                        Dest.Processes -> ProcessesScreen(viewModel)
                        Dest.Sessions -> SessionsScreen(viewModel)
                        Dest.Bookmarks -> BookmarksScreen(viewModel)
                        Dest.Webhooks -> WebhooksScreen(viewModel)
                        Dest.Logs -> LogsScreen(viewModel)
                        Dest.Settings -> SettingsScreen(viewModel, onUnpair = onUnpair)
                        null -> DashboardScreen(viewModel)
                    }
                }
            }
        }
    }
}

package dev.carbonpanel

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.pairing.PairingViewModel
import dev.carbonpanel.ui.DashboardScreen
import dev.carbonpanel.ui.DockerScreen
import dev.carbonpanel.ui.PairingScreen
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.ServicesScreen
import dev.carbonpanel.ui.theme.CarbonTheme

private enum class Tab(val label: String, val icon: ImageVector) {
    Dashboard("Status", Icons.Filled.Dashboard),
    Docker("Docker", Icons.Filled.Inventory2),
    Services("Services", Icons.Filled.Dns),
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            CarbonTheme {
                // Without a Surface the window keeps the Activity theme's
                // background and MaterialTheme's colours never reach the
                // screen — the app renders on Material's default grey instead
                // of the panel's near-black.
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    CarbonPanelRoot()
                }
            }
        }
    }
}

@Composable
private fun CarbonPanelRoot() {
    val pairingViewModel: PairingViewModel = viewModel()
    val panelViewModel: PanelViewModel = viewModel()
    val context = androidx.compose.ui.platform.LocalContext.current

    var paired by remember { mutableStateOf(Prefs.get(context).isPaired) }

    if (!paired) {
        PairingScreen(
            viewModel = pairingViewModel,
            onPaired = { paired = true },
        )
    } else {
        MainScaffold(
            viewModel = panelViewModel,
            onUnpair = {
                panelViewModel.unpair()
                pairingViewModel.reset()
                paired = false
            },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MainScaffold(
    viewModel: PanelViewModel,
    onUnpair: () -> Unit,
) {
    var tab by remember { mutableStateOf(Tab.Dashboard) }
    var menuOpen by remember { mutableStateOf(false) }
    val snackbarHost = remember { SnackbarHostState() }
    val message by viewModel.message.collectAsStateWithLifecycle()

    LaunchedEffect(message) {
        message?.let {
            snackbarHost.showSnackbar(it)
            viewModel.clearMessage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHost) },
        topBar = {
            TopAppBar(
                title = { Text(viewModel.serverName, style = MaterialTheme.typography.titleMedium) },
                actions = {
                    IconButton(onClick = { menuOpen = true }) {
                        Icon(Icons.Filled.Dns, contentDescription = "Menu")
                    }
                    DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                        listOf(0.4f, 1f, 2f, 5f).forEach { seconds ->
                            DropdownMenuItem(
                                text = { Text("Refresh every ${seconds}s") },
                                onClick = {
                                    viewModel.pollInterval = seconds
                                    menuOpen = false
                                },
                            )
                        }
                        DropdownMenuItem(
                            text = { Text("Unpair this device") },
                            onClick = {
                                menuOpen = false
                                onUnpair()
                            },
                        )
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { entry ->
                    NavigationBarItem(
                        selected = tab == entry,
                        onClick = { tab = entry },
                        icon = { Icon(entry.icon, contentDescription = entry.label) },
                        label = { Text(entry.label) },
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding)) {
            when (tab) {
                Tab.Dashboard -> DashboardScreen(viewModel)
                Tab.Docker -> DockerScreen(viewModel)
                Tab.Services -> ServicesScreen(viewModel)
            }
        }
    }
}

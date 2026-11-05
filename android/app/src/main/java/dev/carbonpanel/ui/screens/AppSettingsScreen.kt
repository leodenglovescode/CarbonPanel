package dev.carbonpanel.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.data.SavedServer
import dev.carbonpanel.data.NetUnit
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.components.LocalizedText as Text
import dev.carbonpanel.ui.theme.AccentChoice
import dev.carbonpanel.ui.theme.ThemeMode

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun AppSettingsScreen(
    viewModel: PanelViewModel,
    servers: List<SavedServer>,
    activeServerId: String?,
    onBack: () -> Unit,
    onAdd: () -> Unit,
    onRename: (String, String) -> Unit,
    onRemove: (String) -> Unit,
) {
    val theme by viewModel.themeMode.collectAsStateWithLifecycle()
    val accent by viewModel.accent.collectAsStateWithLifecycle()
    val backdrop by viewModel.backdropEnabled.collectAsStateWithLifecycle()
    val netUnit by viewModel.widgetNetUnit.collectAsStateWithLifecycle()
    val widgetRefresh by viewModel.widgetRefresh.collectAsStateWithLifecycle()
    var interval by remember { mutableStateOf(viewModel.pollInterval) }
    var editing by remember { mutableStateOf<SavedServer?>(null) }
    var removing by remember { mutableStateOf<SavedServer?>(null) }
    var name by remember { mutableStateOf("") }
    editing?.let { server ->
        AlertDialog(onDismissRequest = { editing = null }, title = { Text("Rename server") },
            text = { OutlinedTextField(value = name, onValueChange = { name = it },
                label = { Text("Server name") }, singleLine = true) },
            confirmButton = { TextButton(enabled = name.isNotBlank(), onClick = {
                onRename(server.id, name); editing = null
            }) { Text("Save") } },
            dismissButton = { TextButton(onClick = { editing = null }) { Text("Cancel") } })
    }
    removing?.let { server ->
        ConfirmDialog(title = "Remove server",
            body = "Forget ${server.name} on this phone? Scan a new pairing code to add it again. " +
                "To revoke access, use Paired Devices in that server's web panel.",
            confirmLabel = "Remove",
            onConfirm = { onRemove(server.id); removing = null }, onDismiss = { removing = null })
    }
    Scaffold(topBar = {
        CenterAlignedTopAppBar(title = { Text("App settings", style = MaterialTheme.typography.titleMedium) },
            navigationIcon = { IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = localizeUiText("Back"))
            } })
    }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)) {
            item { SectionLabel("Appearance") }
            item {
                PanelCard(Modifier.fillMaxWidth()) {
                    SegmentedFilterWrapped(options = ThemeMode.entries.toList(), selected = theme,
                        label = { it.name }, onSelect = viewModel::setThemeMode)
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        MonoText("Accent")
                        MonoText(accent.label)
                    }
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                        AccentChoice.entries.filter { it != AccentChoice.Dynamic || AccentChoice.dynamicSupported }
                            .forEach { choice ->
                                AccentSwatch(choice, selected = choice == accent) { viewModel.setAccent(choice) }
                            }
                    }
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Panel background", style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.weight(1f))
                        Switch(checked = backdrop, onCheckedChange = viewModel::setBackdropEnabled)
                    }
                }
            }
            item { SectionLabel("Refresh interval") }
            item {
                PanelCard(Modifier.fillMaxWidth(), spacing = 4) {
                    SegmentedFilterWrapped(options = listOf(.4f, 1f, 2f, 5f), selected = interval,
                        label = { if (it < 1) "${it}s" else "${it.toInt()}s" },
                        onSelect = { interval = it; viewModel.pollInterval = it })
                    MonoText("Polling pauses when the app is in the background.")
                }
            }
            item { SectionLabel("Home screen widget") }
            item {
                PanelCard(Modifier.fillMaxWidth(), spacing = 6) {
                    MonoText("Follows the last selected server")
                    SegmentedFilterWrapped(options = NetUnit.entries.toList(), selected = netUnit,
                        label = { it.label }, onSelect = viewModel::setWidgetNetUnit)
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    MonoText("Refresh every")
                    SegmentedFilterWrapped(options = listOf(15, 30, 60, 180), selected = widgetRefresh,
                        label = { if (it >= 60) "${it / 60}H" else "${it}M" }, onSelect = viewModel::setWidgetRefresh)
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    SectionLabel("SAVED SERVERS", Modifier.weight(1f))
                    TextButton(onClick = onAdd) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp)); Text("Add server")
                    }
                }
            }
            if (servers.isEmpty()) item { EmptyState("No saved servers", "Add a server to start monitoring") }
            items(servers, key = { it.id }) { server ->
                PanelCard(Modifier.fillMaxWidth(), spacing = 4) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(server.name, style = MaterialTheme.typography.bodyMedium,
                                maxLines = 1, overflow = TextOverflow.Ellipsis)
                            MonoText(server.username)
                        }
                        IconButton(onClick = { name = server.name; editing = server }) {
                            Icon(Icons.Default.Edit, contentDescription = localizeUiText("Rename server"),
                                tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                        }
                        IconButton(onClick = { removing = server }) {
                            Icon(Icons.Default.DeleteOutline, contentDescription = localizeUiText("Remove server"),
                                tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(18.dp))
                        }
                    }
                    server.endpoints.forEach { MonoText(it, maxLines = 1) }
                    if (server.id == activeServerId) StatusPill("Selected", MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
}

@Composable
private fun AccentSwatch(choice: AccentChoice, selected: Boolean, onClick: () -> Unit) {
    val outline = if (selected) MaterialTheme.colorScheme.onSurface else Color.Transparent
    Box(Modifier.size(48.dp).semantics {
        contentDescription = localizeUiText("${choice.label} accent")
        role = Role.RadioButton
        this.selected = selected
    }.clickable(onClick = onClick), contentAlignment = Alignment.Center) {
        Box(Modifier.size(26.dp).clip(CircleShape).background(choice.seed)
            .border(2.dp, outline, CircleShape), contentAlignment = Alignment.Center) {
            if (choice == AccentChoice.Dynamic) {
                Text("You", style = MaterialTheme.typography.labelSmall, color = Color.Black)
            }
        }
    }
}

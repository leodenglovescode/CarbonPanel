package dev.carbonpanel.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.data.AppInfo
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Danger

@Composable
fun AppsScreen(viewModel: PanelViewModel) {
    val state by viewModel.apps.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadApps() }

    var labelling by remember { mutableStateOf<AppInfo?>(null) }
    var killing by remember { mutableStateOf<AppInfo?>(null) }

    labelling?.let { app ->
        var text by remember(app.port) { mutableStateOf(app.custom_label.orEmpty()) }
        AlertDialog(
            onDismissRequest = { labelling = null },
            title = { Text("LABEL PORT ${app.port}", style = MaterialTheme.typography.titleMedium) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    MonoText("Detected as \"${app.auto_label}\"")
                    OutlinedTextField(
                        value = text,
                        onValueChange = { text = it },
                        label = { Text("Custom label") },
                        placeholder = { Text("Leave blank to clear") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.setAppLabel(app.port, text.trim()); labelling = null
                }) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { labelling = null }) { Text("Cancel") } },
            containerColor = MaterialTheme.colorScheme.surface,
        )
    }

    killing?.let { app ->
        ConfirmDialog(
            title = "Kill process",
            body = "Kill ${app.process_name} (pid ${app.pid ?: "?"}) listening on port ${app.port}?",
            confirmLabel = "Kill",
            onConfirm = { viewModel.killApp(app.port, force = false) },
            onDismiss = { killing = null },
        )
    }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadApps(refresh = true) },
        emptyTitle = "Nothing listening",
        header = { item { SectionLabel("Listening ports") } },
    ) { apps ->
        items(apps, key = { "${it.protocol}:${it.port}" }) { app ->
            PanelCard(Modifier.fillMaxWidth()) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            app.label.ifBlank { app.process_name },
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        MonoText(
                            "${app.process_name} · ${app.user}" +
                                (app.pid?.let { " · pid $it" } ?: ""),
                            maxLines = 1,
                        )
                    }
                    StatusPill("${app.protocol.uppercase()}/${app.port}", MaterialTheme.colorScheme.primary)
                }
                if (app.cmdline.isNotBlank()) MonoText(app.cmdline, maxLines = 2)
                Row(
                    horizontalArrangement = Arrangement.spacedBy(2.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if ("port${app.port}" in busy) {
                        InlineSpinner()
                    } else {
                        TextButton(onClick = { labelling = app }) { Text("Label") }
                        if (app.pid != null) {
                            TextButton(onClick = { killing = app }) { Text("Kill", color = Danger) }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ProcessesScreen(viewModel: PanelViewModel) {
    val state by viewModel.processes.collectAsStateWithLifecycle()
    val sort by viewModel.processSort.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadProcesses() }

    var killing by remember { mutableStateOf<dev.carbonpanel.data.ProcessMetrics?>(null) }

    killing?.let { p ->
        ConfirmDialog(
            title = "Kill process",
            body = "Send SIGTERM to ${p.name} (pid ${p.pid})?",
            confirmLabel = "Kill",
            onConfirm = { viewModel.killProcess(p.pid, p.name, force = false) },
            onDismiss = { killing = null },
        )
    }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadProcesses(refresh = true) },
        emptyTitle = "No processes",
        header = {
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SectionLabel("Top processes")
                    Row {
                        TextButton(onClick = { viewModel.setProcessSort("cpu") }) {
                            Text(
                                "CPU",
                                color = if (sort == "cpu") MaterialTheme.colorScheme.primary
                                        else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        TextButton(onClick = { viewModel.setProcessSort("memory") }) {
                            Text(
                                "MEM",
                                color = if (sort == "memory") MaterialTheme.colorScheme.primary
                                        else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        },
    ) { procs ->
        // The server ranks by CPU; re-sorting locally avoids a round trip just
        // to reorder a list already in memory.
        val sorted = if (sort == "memory") procs.sortedByDescending { it.memory_mb } else procs
        items(sorted, key = { it.pid }) { p ->
            PanelCard(Modifier.fillMaxWidth(), spacing = 4) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            p.name,
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        MonoText("pid ${p.pid} · ${p.user} · ${p.status}", maxLines = 1)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            "%.1f%%".format(p.cpu_percent),
                            style = MaterialTheme.typography.bodySmall,
                            color = usageColor(p.cpu_percent.coerceAtMost(100.0)),
                        )
                        MonoText(formatMb(p.memory_mb))
                    }
                    if ("pid${p.pid}" in busy) {
                        InlineSpinner()
                    } else {
                        TextButton(onClick = { killing = p }) { Text("Kill", color = Danger) }
                    }
                }
            }
        }
    }
}

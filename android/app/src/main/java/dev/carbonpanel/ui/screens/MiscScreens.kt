package dev.carbonpanel.ui.screens

import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger

@Composable
fun SessionsScreen(viewModel: PanelViewModel) {
    val state by viewModel.sessions.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.loadSessions() }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadSessions(refresh = true) },
        emptyTitle = "No active shell sessions",
        emptyDetail = "Nobody is logged in over SSH or a local TTY right now.",
        header = { item { SectionLabel("Shell sessions") } },
    ) { sessions ->
        items(sessions.size) { i ->
            val s = sessions[i]
            PanelCard(Modifier.fillMaxWidth(), spacing = 4) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text("${s.user}@${s.tty}", style = MaterialTheme.typography.bodyMedium)
                    MonoText(s.login_time)
                }
                MonoText("FROM ${s.from_host.ifBlank { "local" }} · IDLE ${s.idle}")
                if (s.command.isNotBlank()) MonoText(s.command, maxLines = 2)
            }
        }
    }
}

@Composable
fun BookmarksScreen(viewModel: PanelViewModel) {
    val state by viewModel.bookmarks.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(Unit) { viewModel.loadBookmarks() }

    var adding by remember { mutableStateOf(false) }
    var deleting by remember { mutableStateOf<dev.carbonpanel.data.BookmarkOut?>(null) }

    if (adding) {
        var title by remember { mutableStateOf("") }
        var url by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { adding = false },
            title = { Text("New bookmark", style = MaterialTheme.typography.titleMedium) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = title, onValueChange = { title = it },
                        label = { Text("Title") }, singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = url, onValueChange = { url = it },
                        label = { Text("URL") }, singleLine = true,
                        placeholder = { Text("https://…") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = { viewModel.addBookmark(title.trim(), url.trim()); adding = false },
                    enabled = title.isNotBlank() && url.isNotBlank(),
                ) { Text("Add") }
            },
            dismissButton = { TextButton(onClick = { adding = false }) { Text("Cancel") } },
            containerColor = MaterialTheme.colorScheme.surface,
        )
    }

    deleting?.let { bm ->
        ConfirmDialog(
            title = "Delete bookmark",
            body = "Remove \"${bm.title}\"?",
            confirmLabel = "Delete",
            onConfirm = { viewModel.deleteBookmark(bm.id) },
            onDismiss = { deleting = null },
        )
    }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadBookmarks(refresh = true) },
        emptyTitle = "No bookmarks",
        header = {
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SectionLabel("Bookmarks")
                    TextButton(onClick = { adding = true }) { Text("Add") }
                }
            }
        },
    ) { bookmarks ->
        items(bookmarks, key = { it.id }) { bm ->
            PanelCard(
                Modifier
                    .fillMaxWidth()
                    .clickable {
                        runCatching {
                            context.startActivity(Intent(Intent.ACTION_VIEW, bm.url.toUri()))
                        }
                    },
                spacing = 4,
            ) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            bm.title,
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        MonoText(bm.url, maxLines = 1)
                    }
                    if (bm.id in busy) InlineSpinner()
                    else TextButton(onClick = { deleting = bm }) { Text("Delete", color = Danger) }
                }
            }
        }
    }
}

@Composable
fun WebhooksScreen(viewModel: PanelViewModel) {
    val state by viewModel.webhooks.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadWebhooks() }

    var adding by remember { mutableStateOf(false) }
    var deleting by remember { mutableStateOf<dev.carbonpanel.data.WebhookResponse?>(null) }

    if (adding) {
        var label by remember { mutableStateOf("") }
        var url by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { adding = false },
            title = { Text("New webhook", style = MaterialTheme.typography.titleMedium) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = label, onValueChange = { label = it },
                        label = { Text("Label") }, singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = url, onValueChange = { url = it },
                        label = { Text("URL") }, singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    MonoText("Events can be configured from the web panel.")
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.addWebhook(label.trim(), url.trim(), emptyList()); adding = false
                    },
                    enabled = url.isNotBlank(),
                ) { Text("Add") }
            },
            dismissButton = { TextButton(onClick = { adding = false }) { Text("Cancel") } },
            containerColor = MaterialTheme.colorScheme.surface,
        )
    }

    deleting?.let { wh ->
        ConfirmDialog(
            title = "Delete webhook",
            body = "Remove \"${wh.label.ifBlank { wh.url }}\"?",
            confirmLabel = "Delete",
            onConfirm = { viewModel.deleteWebhook(wh.id) },
            onDismiss = { deleting = null },
        )
    }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadWebhooks(refresh = true) },
        emptyTitle = "No webhooks",
        emptyDetail = "Webhooks fire when a metric crosses its alert threshold.",
        header = {
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SectionLabel("Webhooks")
                    TextButton(onClick = { adding = true }) { Text("Add") }
                }
            }
        },
    ) { hooks ->
        items(hooks, key = { it.id }) { wh ->
            PanelCard(Modifier.fillMaxWidth()) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            wh.label.ifBlank { "(unlabelled)" },
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 1,
                        )
                        MonoText(wh.url, maxLines = 1)
                    }
                    Switch(
                        checked = wh.enabled,
                        onCheckedChange = { viewModel.toggleWebhook(wh.id, it) },
                        enabled = wh.id !in busy,
                    )
                }
                if (wh.events.isNotEmpty()) MonoText(wh.events.joinToString(", "), maxLines = 2)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (wh.id in busy) InlineSpinner()
                    else TextButton(onClick = { deleting = wh }) { Text("Delete", color = Danger) }
                }
            }
        }
    }
}

@Composable
fun LogsScreen(viewModel: PanelViewModel) {
    val state by viewModel.logs.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.loadLogs() }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadLogs(refresh = true) },
        emptyTitle = "No log output",
        emptyDetail = "journalctl returned nothing for the update services.",
        header = { item { SectionLabel("Update service logs") } },
    ) { lines ->
        item {
            PanelCard(Modifier.fillMaxWidth(), spacing = 2) {
                // Log lines are long and their alignment carries meaning, so
                // they scroll horizontally rather than wrapping.
                Column(Modifier.horizontalScroll(rememberScrollState())) {
                    lines.forEach { line ->
                        Text(
                            line,
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 1,
                            color = when {
                                line.contains("error", true) -> Danger
                                line.contains("warn", true) -> dev.carbonpanel.ui.theme.Warning
                                line.contains("success", true) -> Accent
                                else -> MaterialTheme.colorScheme.onSurfaceVariant
                            },
                        )
                    }
                }
            }
        }
    }
}

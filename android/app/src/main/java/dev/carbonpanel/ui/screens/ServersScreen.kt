package dev.carbonpanel.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.carbonpanel.data.SavedServer
import dev.carbonpanel.ui.components.ConfirmDialog
import dev.carbonpanel.ui.components.MonoText
import dev.carbonpanel.ui.components.PanelCard
import dev.carbonpanel.ui.components.LocalizedText as Text

@Composable
fun ServersScreen(
    servers: List<SavedServer>,
    onSelect: (String) -> Unit,
    onAdd: () -> Unit,
    onRename: (String, String) -> Unit,
    onRemove: (String) -> Unit,
) {
    var editing by remember { mutableStateOf<SavedServer?>(null) }
    var removing by remember { mutableStateOf<SavedServer?>(null) }
    var name by remember { mutableStateOf("") }
    editing?.let { server ->
        AlertDialog(
            onDismissRequest = { editing = null },
            title = { Text("Rename server") },
            text = {
                OutlinedTextField(value = name, onValueChange = { name = it },
                    label = { Text("Server name") }, singleLine = true)
            },
            confirmButton = {
                TextButton(enabled = name.isNotBlank(), onClick = {
                    onRename(server.id, name); editing = null
                }) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { editing = null }) { Text("Cancel") } },
        )
    }
    removing?.let { server ->
        ConfirmDialog(
            title = "Remove server",
            body = "Forget ${server.name} on this phone? Scan a new pairing code to add it again. " +
                "To revoke this phone's access, use Paired Devices in that server's web panel.",
            confirmLabel = "Remove",
            onConfirm = { onRemove(server.id); removing = null },
            onDismiss = { removing = null },
        )
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Text("Your servers", style = MaterialTheme.typography.headlineMedium)
            MonoText("Choose a server to open its overview")
        }
        items(servers, key = { it.id }) { server ->
            PanelCard(Modifier.fillMaxWidth().clickable { onSelect(server.id) }) {
                Text(server.name, style = MaterialTheme.typography.titleMedium)
                server.endpoints.forEach { MonoText(it) }
                MonoText(server.username)
                Row {
                    TextButton(onClick = { onSelect(server.id) }) { Text("Open") }
                    TextButton(onClick = { name = server.name; editing = server }) { Text("Rename") }
                    TextButton(onClick = { removing = server }) { Text("Remove") }
                }
            }
        }
        item { Button(onClick = onAdd, modifier = Modifier.fillMaxWidth()) { Text("Add server") } }
    }
}

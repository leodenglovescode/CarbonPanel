package dev.carbonpanel.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import dev.carbonpanel.ui.components.LocalizedText as Text
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
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger
import dev.carbonpanel.ui.theme.Warning

@Composable
fun SettingsScreen(viewModel: PanelViewModel, onUnpair: () -> Unit, onAppSettings: () -> Unit) {
    val account by viewModel.account.collectAsStateWithLifecycle()
    val devices by viewModel.devices.collectAsStateWithLifecycle()
    val version by viewModel.version.collectAsStateWithLifecycle()
    val endpoints by viewModel.endpoints.collectAsStateWithLifecycle()
    val activeEndpoint by viewModel.activeEndpoint.collectAsStateWithLifecycle()
    val reachability by viewModel.reachability.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    val widgetDisk by viewModel.widgetDisk.collectAsStateWithLifecycle()
    val widgetIface by viewModel.widgetIface.collectAsStateWithLifecycle()
    val diskChoices = viewModel.diskChoices
    val ifaceChoices = viewModel.ifaceChoices

    LaunchedEffect(Unit) {
        viewModel.loadSettings()
        viewModel.refreshEndpoints()
    }

    var confirmUnpair by remember { mutableStateOf(false) }

    if (confirmUnpair) ConfirmDialog(
        title = "Unpair device",
        body = "This phone will forget this server's token and addresses. Other saved servers are kept. " +
            "You'll need to scan a new pairing code to get back in.",
        confirmLabel = "Unpair",
        onConfirm = { viewModel.unpair(); onUnpair() },
        onDismiss = { confirmUnpair = false },
    )

    LazyColumn(
        modifier = Modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        // ── connection ─────────────────────────────────────────────────────
        item { SectionLabel("Server") }
        item {
            PanelCard {
                DetailRow("Panel", viewModel.serverName)
                DetailRow("Signed in as", viewModel.username)
                DetailRow("Connected via", activeEndpoint?.substringAfter("://") ?: "—")
                Row {
                    TextButton(onClick = { viewModel.reconnect() }) { Text("Reconnect") }
                    TextButton(onClick = { viewModel.testAllEndpoints() }) { Text("Test all") }
                }
            }
        }

        // ── server addresses ───────────────────────────────────────────────
        item { SectionLabel("Server addresses") }
        item {
            PanelCard {
                MonoText(
                    "Tried top to bottom until one answers. Keep an address that works " +
                        "away from home — a VPN address or a public domain — so the app " +
                        "keeps working off your LAN.",
                )
            }
        }
        items(endpoints.size) { i ->
            val url = endpoints[i]
            EndpointRow(
                url = url,
                isActive = url == activeEndpoint,
                isFirst = i == 0,
                reachable = reachability[url],
                onTest = { viewModel.testEndpoint(url) },
                onPromote = { viewModel.promoteEndpoint(url) },
                onRemove = { viewModel.removeEndpoint(url) },
            )
        }

        item {
            PanelCard {
                Text("App settings", style = MaterialTheme.typography.bodyMedium)
                MonoText("Appearance, refresh interval and saved servers")
                TextButton(onClick = onAppSettings) { Text("Open app settings") }
            }
        }

        // ── widget ─────────────────────────────────────────────────────────
        item {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                SectionLabel("Home screen widget")
                TextButton(onClick = { viewModel.refreshWidgetNow() }) { Text("Refresh now") }
            }
        }
        item {
            PanelCard {
                MonoText("Disk ring")
                if (diskChoices.isEmpty()) {
                    MonoText("Open Storage once so the app knows your disks.")
                } else {
                    SegmentedFilterWrapped(
                        options = listOf("") + diskChoices,
                        selected = widgetDisk,
                        label = { if (it.isBlank()) "Largest" else it },
                        onSelect = viewModel::setWidgetDisk,
                    )
                }

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                MonoText("Network interface")
                if (ifaceChoices.isEmpty()) {
                    MonoText("Open Status once so the app knows your interfaces.")
                } else {
                    SegmentedFilterWrapped(
                        options = listOf("") + ifaceChoices,
                        selected = widgetIface,
                        label = { if (it.isBlank()) "Busiest" else it },
                        onSelect = viewModel::setWidgetIface,
                    )
                }

                TextButton(onClick = onAppSettings) { Text("Widget refresh and units") }

            }
        }

        // ── account ────────────────────────────────────────────────────────
        item { SectionLabel("Account") }
        item {
            LoadContent(account) { user ->
                PanelCard {
                    DetailRow("Username", user.username)
                    DetailRow("Two-factor", if (user.totp_enabled) "Enabled" else "Disabled")
                    MonoText("Change your password or 2FA from the web panel.")
                }
            }
        }

        // ── paired devices ─────────────────────────────────────────────────
        item { SectionLabel("Sessions & devices") }
        item {
            LoadContent(devices) { list ->
                PanelCard {
                    if (list.isEmpty()) {
                        MonoText("No active sessions.")
                    } else {
                        list.forEach { d ->
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(
                                        d.name,
                                        style = MaterialTheme.typography.bodySmall,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    MonoText("${d.kind} · ${d.ip_address ?: "unknown IP"}")
                                }
                                if (d.id in busy) InlineSpinner()
                                else TextButton(onClick = { viewModel.revokeDevice(d.id) }) {
                                    Text("Revoke", color = Danger)
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── updates ────────────────────────────────────────────────────────
        item { SectionLabel("Version") }
        item {
            LoadContent(version) { v ->
                PanelCard {
                    DetailRow("Installed", v.current_version ?: v.current_commit?.take(8) ?: "—")
                    v.latest_version?.let { DetailRow("Latest", it) }
                    v.checked_at?.let { DetailRow("Checked", it) }
                    when {
                        v.error != null -> InfoBanner(v.error, Warning)
                        v.update_in_progress -> InfoBanner("Update in progress…", Accent)
                        v.update_available -> InfoBanner("Update available", Accent)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if ("update" in busy) InlineSpinner()
                        else TextButton(onClick = { viewModel.checkUpdates() }) {
                            Text("Check for updates")
                        }
                    }
                    MonoText("Installing updates is done from the web panel.")
                }
            }
        }

        // ── danger zone ────────────────────────────────────────────────────
        item { SectionLabel("This device") }
        item {
            PanelCard {
                MonoText(
                    "Unpairing forgets the token stored on this phone. The server-side " +
                        "device can also be revoked from the web panel at any time.",
                )
                TextButton(onClick = { confirmUnpair = true }) {
                    Text("Unpair this device", color = Danger)
                }
            }
        }
    }
}

@Composable
private fun EndpointRow(
    url: String,
    isActive: Boolean,
    isFirst: Boolean,
    reachable: Boolean?,
    onTest: () -> Unit,
    onPromote: () -> Unit,
    onRemove: () -> Unit,
) {
    PanelCard(Modifier.fillMaxWidth(), spacing = 6) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                url,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            when (reachable) {
                null -> if (isActive) StatusPill("active", Accent) else Unit
                true -> StatusPill(if (isActive) "active" else "reachable", Accent)
                false -> StatusPill("no reply", Danger)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
            TextButton(onClick = onTest) { Text("Test") }
            if (!isFirst) TextButton(onClick = onPromote) { Text("Move up") }
            TextButton(onClick = onRemove) { Text("Remove", color = Danger) }
        }
    }
}

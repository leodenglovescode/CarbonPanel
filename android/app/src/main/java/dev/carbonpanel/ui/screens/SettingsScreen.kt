package dev.carbonpanel.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
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
import dev.carbonpanel.data.NetUnit
import dev.carbonpanel.ui.Load
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.AccentChoice
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger
import dev.carbonpanel.ui.theme.ThemeMode
import dev.carbonpanel.ui.theme.Warning

@Composable
fun SettingsScreen(viewModel: PanelViewModel, onUnpair: () -> Unit) {
    val account by viewModel.account.collectAsStateWithLifecycle()
    val devices by viewModel.devices.collectAsStateWithLifecycle()
    val version by viewModel.version.collectAsStateWithLifecycle()
    val endpoints by viewModel.endpoints.collectAsStateWithLifecycle()
    val activeEndpoint by viewModel.activeEndpoint.collectAsStateWithLifecycle()
    val reachability by viewModel.reachability.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    val themeMode by viewModel.themeMode.collectAsStateWithLifecycle()
    val accent by viewModel.accent.collectAsStateWithLifecycle()
    val backdrop by viewModel.backdropEnabled.collectAsStateWithLifecycle()
    val widgetDisk by viewModel.widgetDisk.collectAsStateWithLifecycle()
    val widgetIface by viewModel.widgetIface.collectAsStateWithLifecycle()
    val netUnit by viewModel.widgetNetUnit.collectAsStateWithLifecycle()
    val widgetRefresh by viewModel.widgetRefresh.collectAsStateWithLifecycle()
    val diskChoices = viewModel.diskChoices
    val ifaceChoices = viewModel.ifaceChoices
    val interval = viewModel.pollInterval

    LaunchedEffect(Unit) {
        viewModel.loadSettings()
        viewModel.refreshEndpoints()
    }

    var confirmUnpair by remember { mutableStateOf(false) }

    if (confirmUnpair) ConfirmDialog(
        title = "Unpair device",
        body = "This phone will forget its token and every saved server address. " +
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

        // ── appearance ─────────────────────────────────────────────────────
        item { SectionLabel("Appearance") }
        item {
            PanelCard {
                MonoText("Theme")
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    ThemeMode.entries.forEach { mode ->
                        FilterChip(
                            selected = themeMode == mode,
                            onClick = { viewModel.setThemeMode(mode) },
                            label = { Text(mode.name) },
                        )
                    }
                }

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                MonoText("Accent")
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    AccentChoice.entries
                        .filter { it != AccentChoice.Dynamic || AccentChoice.dynamicSupported }
                        .forEach { choice ->
                            AccentSwatch(
                                choice = choice,
                                selected = accent == choice,
                                onClick = { viewModel.setAccent(choice) },
                            )
                        }
                }
                MonoText(
                    if (accent == AccentChoice.Dynamic)
                        "Material You — colours follow your wallpaper"
                    else accent.label,
                )

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("Panel background", style = MaterialTheme.typography.bodyMedium)
                        MonoText("Use the background image configured on the server")
                    }
                    Switch(
                        checked = backdrop,
                        onCheckedChange = { viewModel.setBackdropEnabled(it) },
                    )
                }
            }
        }

        // ── refresh rate ───────────────────────────────────────────────────
        item { SectionLabel("Refresh") }
        item {
            var current by remember { mutableStateOf(interval) }
            PanelCard {
                MonoText("How often the dashboard polls while it's on screen.")
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf(0.4f, 1f, 2f, 5f).forEach { s ->
                        FilterChip(
                            selected = current == s,
                            onClick = { current = s; viewModel.pollInterval = s },
                            label = { Text(if (s < 1f) "${s}s" else "${s.toInt()}s") },
                        )
                    }
                }
                MonoText("Polling stops entirely when the app is in the background.")
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

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                MonoText("Throughput unit")
                SegmentedFilterWrapped(
                    options = NetUnit.entries.toList(),
                    selected = netUnit,
                    label = { it.label },
                    onSelect = viewModel::setWidgetNetUnit,
                )
                MonoText(
                    // Bits vs bytes is an 8x difference; saying which is which
                    // avoids the widget looking wrong to whoever reads it.
                    if (netUnit == NetUnit.Mbps || netUnit == NetUnit.Gbps)
                        "Bits per second — matches how link speeds are quoted."
                    else "Bytes per second — matches file-transfer speeds.",
                )

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                MonoText("Refresh every")
                SegmentedFilterWrapped(
                    options = listOf(15, 30, 60, 180),
                    selected = widgetRefresh,
                    label = { if (it >= 60) "${it / 60}H" else "${it}M" },
                    onSelect = viewModel::setWidgetRefresh,
                )
                MonoText(
                    "Android won't run widget updates more often than every 15 minutes, " +
                        "so a live gauge isn't possible — the widget shows its age instead.",
                )
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

@Composable
private fun AccentSwatch(choice: AccentChoice, selected: Boolean, onClick: () -> Unit) {
    val ring = if (selected) MaterialTheme.colorScheme.onSurface else Color.Transparent
    Box(
        Modifier
            .sizeIn(minWidth = 48.dp, minHeight = 48.dp)
            .semantics {
                contentDescription = localizeUiText("${choice.label} accent")
                role = Role.RadioButton
                this.selected = selected
            }
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            Modifier
                .size(30.dp)
                .clip(CircleShape)
                .background(choice.seed)
                .border(2.dp, ring, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            // Material You has no fixed colour of its own, so it's marked rather
            // than shown as a swatch that would misrepresent the result.
            if (choice == AccentChoice.Dynamic) {
                Text("You", style = MaterialTheme.typography.labelSmall, color = Color.Black)
            }
        }
    }
}

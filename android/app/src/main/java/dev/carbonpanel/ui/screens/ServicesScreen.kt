package dev.carbonpanel.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.outlined.StarBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.data.SystemServiceInfo
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.UnitKind
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger

@Composable
fun ServicesScreen(viewModel: PanelViewModel) {
    val state by viewModel.services.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    val showAll by viewModel.showAllServices.collectAsStateWithLifecycle()
    val kind by viewModel.serviceKind.collectAsStateWithLifecycle()
    val query by viewModel.serviceQuery.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadServices() }

    var confirm by remember { mutableStateOf<Pair<String, String>?>(null) }

    confirm?.let { (name, action) ->
        ConfirmDialog(
            title = "${action.replaceFirstChar { it.uppercase() }} unit",
            body = "$action $name?",
            confirmLabel = action.replaceFirstChar { it.uppercase() },
            destructive = action != "start",
            onConfirm = { viewModel.serviceAction(name, action) },
            onDismiss = { confirm = null },
        )
    }

    // Filtering happens here rather than server-side: the unit list is already
    // in memory, and a round trip per keystroke would be worse in every way.
    val filtered = (state.dataOrNull ?: emptyList()).filter { svc ->
        kind.matches(svc.service_name) &&
            (query.isBlank() ||
                svc.service_name.contains(query, ignoreCase = true) ||
                svc.description?.contains(query, ignoreCase = true) == true)
    }
    val display = when (state) {
        is dev.carbonpanel.ui.Load.Ok -> dev.carbonpanel.ui.Load.Ok(
            filtered,
            (state as dev.carbonpanel.ui.Load.Ok).refreshing,
        )
        else -> state
    }

    LoadList(
        state = display,
        onRefresh = { viewModel.loadServices(refresh = true) },
        emptyTitle = if (query.isNotBlank()) "No matches" else "Nothing to show",
        emptyDetail = when {
            query.isNotBlank() -> "No unit matches \"$query\"."
            kind == UnitKind.Timers -> "No timers found in this scope."
            !showAll -> "Star the units you care about in the web panel, or show all."
            else -> null
        },
        header = {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    SearchField(
                        value = query,
                        onValueChange = viewModel::setServiceQuery,
                        placeholder = "Search units…",
                    )
                    SegmentedFilter(
                        options = UnitKind.entries.toList(),
                        selected = kind,
                        label = { it.label },
                        onSelect = viewModel::setServiceKind,
                    )
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        SectionLabel(
                            if (showAll) "ALL UNITS · ${filtered.size}"
                            else "STARRED · ${filtered.size}",
                        )
                        TextButton(onClick = { viewModel.toggleShowAllServices() }) {
                            Text(if (showAll) "Show starred" else "Show all")
                        }
                    }
                }
            }
        },
    ) { services ->
        items(services, key = { it.service_name }) { svc ->
            ServiceRow(
                service = svc,
                busy = svc.service_name in busy,
                onAction = { confirm = svc.service_name to it },
                onStar = { viewModel.serviceStar(svc.service_name, !svc.starred) },
                onAutostart = { viewModel.serviceAutostart(svc.service_name, it) },
            )
        }
    }
}

@Composable
private fun ServiceRow(
    service: SystemServiceInfo,
    busy: Boolean,
    onAction: (String) -> Unit,
    onStar: () -> Unit,
    onAutostart: (Boolean) -> Unit,
) {
    val isTimer = service.service_name.endsWith(".timer")

    PanelCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                // Unit names and descriptions stay verbatim — they're
                // identifiers, and uppercasing them would misrepresent them.
                Text(
                    service.service_name,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                service.description?.takeIf { it.isNotBlank() }?.let { MonoText(it, maxLines = 1) }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (isTimer) StatusPill("Timer", MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.width(4.dp))
                StatusPill(
                    service.sub_state.ifBlank { service.active_state }.replaceFirstChar { it.uppercase() },
                    service.isActive,
                )
                IconButton(onClick = onStar, modifier = Modifier.size(32.dp)) {
                    Icon(
                        if (service.starred) Icons.Filled.Star else Icons.Outlined.StarBorder,
                        contentDescription = localizeUiText(if (service.starred) "Unstar" else "Star"),
                        tint = if (service.starred) Accent
                               else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(17.dp),
                    )
                }
            }
        }

        service.uptime?.takeIf { it.isNotBlank() }?.let { MonoText("Since $it") }

        // Actions and the autostart toggle are on separate rows. Sharing one
        // row squeezed the label against the Switch, and forcing the Switch
        // below its natural size made the thumb overlap the text.
        Row(
            horizontalArrangement = Arrangement.spacedBy(2.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (busy) {
                InlineSpinner()
            } else if (service.isActive) {
                TextButton(onClick = { onAction("restart") }) { Text("Restart") }
                TextButton(onClick = { onAction("stop") }) { Text("Stop", color = Danger) }
            } else {
                TextButton(onClick = { onAction("start") }) { Text("Start", color = Accent) }
            }
        }
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            MonoText("Autostart on boot")
            Switch(
                checked = service.autostart_enabled,
                onCheckedChange = onAutostart,
                enabled = !busy,
            )
        }
    }
}

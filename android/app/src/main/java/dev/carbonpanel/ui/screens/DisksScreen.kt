package dev.carbonpanel.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.items
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
import dev.carbonpanel.data.DiskInfo
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger
import dev.carbonpanel.ui.theme.Warning

@Composable
fun DisksScreen(viewModel: PanelViewModel) {
    val state by viewModel.disks.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadDisks() }

    var unmountTarget by remember { mutableStateOf<String?>(null) }

    unmountTarget?.let { mp ->
        ConfirmDialog(
            title = "Unmount",
            body = "Unmount $mp? Anything reading or writing there will fail.",
            confirmLabel = "Unmount",
            onConfirm = { viewModel.unmount(mp) },
            onDismiss = { unmountTarget = null },
        )
    }

    var showPseudo by remember { mutableStateOf(false) }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadDisks(refresh = true) },
        emptyTitle = "No disks reported",
        header = {
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SectionLabel("Physical disks")
                    if ("smart" in busy) InlineSpinner()
                    else TextButton(onClick = { viewModel.refreshSmart() }) { Text("Rescan SMART") }
                }
            }
        },
    ) { disks ->
        // A desktop-derived install has 20+ snap mounts and every container
        // layer besides; those are not disks and burying three real ones under
        // them makes the screen useless. The server's is_virtual flag misses
        // snap mounts (they're real mounts of real loop devices), so the
        // mountpoint/device heuristic does the work — see isPseudoMount.
        val (pseudo, real) = disks.partition {
            it.is_virtual || isPseudoMount(it.mountpoint, it.device, it.fstype)
        }
        items(real, key = { it.mountpoint }) { disk ->
            DiskCard(disk, disk.mountpoint in busy) { unmountTarget = disk.mountpoint }
        }
        if (pseudo.isNotEmpty()) {
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SectionLabel("PSEUDO & SNAP MOUNTS · ${pseudo.size}")
                    TextButton(onClick = { showPseudo = !showPseudo }) {
                        Text(if (showPseudo) "Hide" else "Show")
                    }
                }
            }
            if (showPseudo) {
                items(pseudo, key = { it.mountpoint }) { disk ->
                    PanelCard(spacing = 2) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(
                                disk.mountpoint,
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f),
                            )
                            MonoText("%.0f%%".format(disk.usage_percent))
                        }
                        MonoText("${disk.device} · ${disk.fstype}", maxLines = 1)
                    }
                }
            }
        }
    }
}

@Composable
private fun DiskCard(disk: DiskInfo, busy: Boolean, onUnmount: () -> Unit) {
    PanelCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    disk.mountpoint,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                MonoText("${disk.device} · ${disk.fstype}", maxLines = 1)
            }
            Text(
                "%.0f%%".format(disk.usage_percent),
                style = MaterialTheme.typography.bodyMedium,
                color = usageColor(disk.usage_percent),
            )
        }

        Meter(disk.usage_percent)

        MonoText(
            "${formatGb(disk.used_gb)} used · ${formatGb(disk.free_gb)} free · " +
                "${formatGb(disk.total_gb)} total",
        )
        MonoText("Read ${formatRate(disk.read_mb_s)} · write ${formatRate(disk.write_mb_s)}")

        // Bind mounts into snap dirs are noise for the same reason the snap
        // mounts themselves are.
        val extras = disk.extra_mounts.filterNot { isPseudoMount(it) }
        if (extras.isNotEmpty()) {
            MonoText("Also at ${extras.joinToString(", ")}", maxLines = 2)
        }

        disk.smart?.let { smart ->
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                SectionLabel("SMART")
                if (smart.error != null) {
                    StatusPill("Unavailable", MaterialTheme.colorScheme.onSurfaceVariant)
                } else {
                    StatusPill(
                        smart.health.ifBlank { "Unknown" },
                        if (smart.isHealthy) Accent else Danger,
                    )
                }
            }
            if (smart.error != null) {
                MonoText(smart.error, maxLines = 2)
            } else {
                if (smart.model.isNotBlank()) DetailRow("Model", smart.model)
                smart.temperature_c?.let { DetailRow("Temperature", "$it °C") }
                smart.power_on_hours?.let {
                    DetailRow("Power on", "$it h  (${it / 24 / 365}y ${it / 24 % 365}d)")
                }
                // Non-zero on any of these is the early warning that matters —
                // surface them even when overall health still says PASSED.
                smart.reallocated_sectors?.takeIf { it > 0 }?.let {
                    InfoBanner("$it reallocated sectors", Warning)
                }
                smart.pending_sectors?.takeIf { it > 0 }?.let {
                    InfoBanner("$it pending sectors", Warning)
                }
                smart.uncorrectable_errors?.takeIf { it > 0 }?.let {
                    InfoBanner("$it uncorrectable errors", Danger)
                }
            }
        }

        if (disk.can_unmount) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (busy) InlineSpinner()
                else TextButton(onClick = onUnmount) { Text("Unmount", color = Danger) }
            }
        }
    }
}

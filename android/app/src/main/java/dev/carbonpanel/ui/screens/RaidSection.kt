package dev.carbonpanel.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import dev.carbonpanel.data.*
import dev.carbonpanel.ui.RaidState
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.components.LocalizedText as Text
import dev.carbonpanel.ui.theme.Warning

@Composable
fun RaidSection(state: RaidState, onRefresh: () -> Unit) {
    val colors = MaterialTheme.colorScheme
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            SectionLabel("RAID", Modifier.weight(1f))
            StatusPill("Read only", colors.onSurfaceVariant)
            TextButton(onClick = onRefresh, enabled = !state.loading) { Text("Refresh") }
        }
        state.error?.let { ErrorBanner(it) }
        if (state.loading && state.inventory == null) LoadingBlock(label = "Reading arrays…")
        state.inventory?.let { inventory ->
            inventory.errors.forEach { InfoBanner(it, Warning) }
            if (inventory.arrays.isEmpty()) PanelCard(Modifier.fillMaxWidth(), spacing = 4) {
                Text(if (inventory.available) "No RAID arrays detected" else "RAID inventory unavailable",
                    style = MaterialTheme.typography.bodySmall)
                MonoText("Linux MD software RAID. Hardware and vendor RAID controllers are not reported.")
            }
            inventory.arrays.forEach { array -> RaidCard(array, stale = state.error != null) }
        }
    }
}

@Composable
private fun RaidCard(array: RaidArray, stale: Boolean) {
    val colors = MaterialTheme.colorScheme
    val tone = when (array.health) {
        RaidHealth.Healthy -> colors.primary
        RaidHealth.Degraded, RaidHealth.Inactive -> colors.error
        RaidHealth.Unknown -> colors.onSurfaceVariant
    }
    PanelCard(Modifier.fillMaxWidth(), spacing = 6) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(array.device, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
            MonoText(array.level?.uppercase() ?: "Unknown level")
            StatusPill(if (stale) "Last known" else array.health.name, if (stale) Warning else tone)
        }
        val capacity = array.size_bytes?.let { formatGb(it / 1_073_741_824.0) } ?: "—"
        MonoText("$capacity · ${array.raid_disks ?: "?"} slots · ${array.degraded ?: "?"} degraded")
        if ((array.degraded ?: 0) > 0) {
            InfoBanner("${array.degraded} missing/degraded", colors.error)
        }
        if (array.isSyncing) {
            val progress = array.sync_percent?.takeIf { it.isFinite() }?.coerceIn(0.0, 100.0)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                MonoText("${array.state ?: "Unknown"} · ${array.sync_action}", color = Warning)
                MonoText(progress?.let { "%.1f%%".format(it) } ?: "In progress", color = Warning)
            }
            if (progress != null) LinearProgressIndicator(progress = { progress.toFloat() / 100f },
                modifier = Modifier.fillMaxWidth().height(4.dp), color = Warning,
                trackColor = Warning.copy(alpha = .12f))
            else LinearProgressIndicator(modifier = Modifier.fillMaxWidth().height(4.dp), color = Warning)
        } else MonoText("${array.state ?: "Not reported"} · sync ${array.sync_action ?: "not reported"}")
        if (array.members.isNotEmpty()) {
            HorizontalDivider(color = colors.outlineVariant)
            array.members.forEach { member ->
                val memberTone = when {
                    member.isFaulty -> colors.error
                    member.state.orEmpty().split(',').any { it.trim() == "in_sync" } -> colors.primary
                    else -> colors.onSurfaceVariant
                }
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.size(5.dp).background(memberTone, CircleShape))
                    Text(member.device, style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    MonoText("Slot ${member.slot ?: "—"}")
                    Text(member.state?.replace('_', ' ') ?: "Unknown", color = memberTone,
                        style = MaterialTheme.typography.bodySmall, maxLines = 2,
                        modifier = Modifier.widthIn(max = 110.dp))
                }
            }
        } else MonoText("Member details not reported")
    }
}

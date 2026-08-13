package dev.carbonpanel.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import dev.carbonpanel.ui.components.LocalizedText as Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger
import dev.carbonpanel.ui.theme.LocalHasBackdrop
import dev.carbonpanel.ui.theme.Warning
import kotlin.math.roundToInt

/** Shared colour ramp for every meter: green until it matters, red when it does. */
fun usageColor(percent: Double): Color = when {
    percent >= 90 -> Danger
    percent >= 75 -> Warning
    else -> Accent
}

/**
 * The panel's card.
 *
 * Uses an explicit surface colour and a hairline outline rather than Material's
 * elevation shadows — the web UI is flat and borders read better against a
 * background photo, where a shadow just muddies the edge.
 */
@Composable
fun PanelCard(
    modifier: Modifier = Modifier,
    contentPadding: PaddingValues = PaddingValues(14.dp),
    spacing: Int = 8,
    content: @Composable ColumnScope.() -> Unit,
) {
    val backdrop = LocalHasBackdrop.current
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        // Over a photo the card has to be near-opaque to stay legible; over
        // flat colour a little translucency keeps it from looking pasted on.
        color = MaterialTheme.colorScheme.surface.copy(alpha = if (backdrop) 0.90f else 1f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(
            modifier = Modifier.padding(contentPadding),
            verticalArrangement = Arrangement.spacedBy(spacing.dp),
            content = content,
        )
    }
}

@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(
        text,
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier.padding(start = 2.dp, top = 4.dp),
    )
}

@Composable
fun Meter(percent: Double, modifier: Modifier = Modifier, height: Int = 5) {
    val target = (percent / 100.0).coerceIn(0.0, 1.0).toFloat()
    val fraction by animateFloatAsState(target, tween(400), label = "meter")
    val color by animateColorAsState(usageColor(percent), tween(400), label = "meterColor")
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(height.dp)
            .clip(RoundedCornerShape(height.dp / 2))
            .background(MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Box(
            Modifier
                .fillMaxWidth(fraction)
                .height(height.dp)
                .clip(RoundedCornerShape(height.dp / 2))
                .background(color),
        )
    }
}

@Composable
fun StatusPill(text: String, tone: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(4.dp))
            .background(tone.copy(alpha = 0.14f))
            .border(1.dp, tone.copy(alpha = 0.35f), RoundedCornerShape(4.dp))
            .padding(horizontal = 7.dp, vertical = 3.dp),
    ) {
        Text(text, style = MaterialTheme.typography.labelSmall, color = tone, maxLines = 1)
    }
}

@Composable
fun StatusPill(text: String, ok: Boolean, modifier: Modifier = Modifier) =
    StatusPill(text, if (ok) Accent else MaterialTheme.colorScheme.onSurfaceVariant, modifier)

/** Label/value row used throughout detail screens. */
@Composable
fun DetailRow(label: String, value: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.Top,
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.width(12.dp))
        Text(
            value,
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.End,
            modifier = Modifier.weight(1f, fill = false),
        )
    }
}

@Composable
fun EmptyState(
    title: String,
    detail: String? = null,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 48.dp, horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(title, style = MaterialTheme.typography.bodyMedium)
        if (detail != null) {
            Text(
                detail,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
fun ErrorBanner(message: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(Danger.copy(alpha = 0.12f))
            .border(1.dp, Danger.copy(alpha = 0.3f), RoundedCornerShape(6.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(message, style = MaterialTheme.typography.bodySmall, color = Danger)
    }
}

@Composable
fun InfoBanner(message: String, tone: Color = Warning, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(tone.copy(alpha = 0.12f))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(message, style = MaterialTheme.typography.bodySmall, color = tone)
    }
}

@Composable
fun LoadingBlock(modifier: Modifier = Modifier, label: String = "Loading…") {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 40.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
fun InlineSpinner(modifier: Modifier = Modifier, size: Int = 15) {
    CircularProgressIndicator(modifier.size(size.dp), strokeWidth = 2.dp)
}

/**
 * Confirmation for anything that stops, kills or deletes.
 *
 * The web UI gained these for start/stop/restart because a misplaced tap on a
 * container is expensive; on a phone the target is smaller and the stakes are
 * identical.
 */
@Composable
fun ConfirmDialog(
    title: String,
    body: String,
    confirmLabel: String,
    destructive: Boolean = true,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title, style = MaterialTheme.typography.titleMedium) },
        text = { Text(body, style = MaterialTheme.typography.bodySmall) },
        confirmButton = {
            TextButton(onClick = { onDismiss(); onConfirm() }) {
                Text(
                    confirmLabel,
                    color = if (destructive) Danger else MaterialTheme.colorScheme.primary,
                )
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        },
        containerColor = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(10.dp),
    )
}

@Composable
fun MonoText(
    text: String,
    modifier: Modifier = Modifier,
    maxLines: Int = Int.MAX_VALUE,
    color: Color = MaterialTheme.colorScheme.onSurfaceVariant,
) {
    Text(
        text,
        style = MaterialTheme.typography.bodySmall,
        color = color,
        maxLines = maxLines,
        overflow = TextOverflow.Ellipsis,
        modifier = modifier,
    )
}

// ── formatting helpers ─────────────────────────────────────────────────────

fun formatUptime(seconds: Double): String {
    val total = seconds.roundToInt()
    val d = total / 86_400
    val h = (total % 86_400) / 3_600
    val m = (total % 3_600) / 60
    return when {
        d > 0 -> "${d}d ${h}h"
        h > 0 -> "${h}h ${m}m"
        else -> "${m}m"
    }
}

fun formatMb(mb: Double): String = when {
    mb >= 1_048_576 -> "%.1f TB".format(mb / 1_048_576)
    mb >= 1024 -> "%.1f GB".format(mb / 1024)
    else -> "%.0f MB".format(mb)
}

fun formatGb(gb: Double): String =
    if (gb >= 1024) "%.1f TB".format(gb / 1024) else "%.1f GB".format(gb)

fun formatRate(mbPerSec: Double): String = when {
    mbPerSec >= 1 -> "%.1f MB/s".format(mbPerSec)
    // Below ~1 KB/s the reading is rounding noise, not throughput, so it reads
    // as idle rather than as a suspiciously precise "0 KB/s".
    mbPerSec * 1024 >= 1 -> "%.0f KB/s".format(mbPerSec * 1024)
    else -> "idle"
}

fun formatBytes(bytes: Long): String {
    val units = listOf("B", "KB", "MB", "GB", "TB")
    var v = bytes.toDouble()
    var i = 0
    while (v >= 1024 && i < units.lastIndex) { v /= 1024; i++ }
    return if (i == 0) "$bytes B" else "%.1f %s".format(v, units[i])
}

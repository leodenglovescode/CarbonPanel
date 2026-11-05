package dev.carbonpanel.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import dev.carbonpanel.ui.components.LocalizedText as Text

@Composable
fun MetricRing(label: String, percent: Double?, modifier: Modifier = Modifier, tint: Color = MaterialTheme.colorScheme.primary) {
    val value = percent?.takeIf { it.isFinite() }?.coerceIn(0.0, 100.0)
    val fraction by animateFloatAsState((value ?: 0.0).toFloat() / 100f, tween(650), label = "ring")
    val track = MaterialTheme.colorScheme.outlineVariant
    val tone = if ((value ?: 0.0) >= 90) MaterialTheme.colorScheme.error else tint
    val formatted = value?.let { "%.0f%%".format(it) } ?: "—"
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Box(Modifier.fillMaxWidth().aspectRatio(1f).semantics {
            contentDescription = "$label: $formatted"
        }, contentAlignment = Alignment.Center) {
            Canvas(Modifier.fillMaxSize().padding(4.dp)) {
                val stroke = 3.dp.toPx()
                val inset = stroke / 2
                val arcSize = Size(size.width - stroke, size.height - stroke)
                drawArc(track, 135f, 270f, false, Offset(inset, inset), arcSize, style = Stroke(stroke, cap = StrokeCap.Round))
                if (value != null && fraction > 0) drawArc(tone, 135f, 270f * fraction, false,
                    Offset(inset, inset), arcSize, style = Stroke(stroke, cap = StrokeCap.Round))
            }
            Text(formatted, style = MaterialTheme.typography.titleMedium,
                color = if (value != null) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

package dev.carbonpanel.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

/**
 * Line chart for a percentage series over time.
 *
 * Hand-drawn on a Canvas rather than pulling in a charting library: the app
 * needs exactly one chart shape, and every Android charting dependency is
 * larger than this file by orders of magnitude.
 *
 * The y-axis is pinned to 0..100 rather than auto-scaled to the data. An
 * autoscaled CPU trace makes 3% idle noise look like a crisis, which is the
 * opposite of what a monitoring panel should communicate at a glance.
 */
@Composable
fun PercentChart(
    series: List<Series>,
    modifier: Modifier = Modifier,
    height: Int = 120,
    showAxis: Boolean = true,
    axisMax: String = "100%",
    axisMid: String = "50%",
    axisMin: String = "0",
) {
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        if (showAxis) {
            // Drawn as real Text rather than canvas glyphs so it inherits the
            // theme's font and scales with the user's font-size setting.
            Column(
                modifier = Modifier.height(height.dp).padding(end = 6.dp),
                verticalArrangement = Arrangement.SpaceBetween,
                horizontalAlignment = Alignment.End,
            ) {
                listOf(axisMax, axisMid, axisMin).forEach {
                    Text(
                        it,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        ChartCanvas(series, Modifier.weight(1f), height)
    }
}

@Composable
private fun ChartCanvas(series: List<Series>, modifier: Modifier, height: Int) {
    val gridColor = MaterialTheme.colorScheme.outlineVariant
    val hasData = series.any { it.values.size >= 2 }

    Box(modifier.fillMaxWidth().height(height.dp)) {
        Canvas(Modifier.fillMaxWidth().height(height.dp)) {
            val w = size.width
            val h = size.height

            // Gridlines at 25/50/75%. 0 and 100 are the frame, so drawing them
            // too just thickens the edges.
            val dash = PathEffect.dashPathEffect(floatArrayOf(3f, 6f))
            listOf(0.25f, 0.5f, 0.75f).forEach { f ->
                val y = h * (1f - f)
                drawLine(
                    color = gridColor,
                    start = Offset(0f, y),
                    end = Offset(w, y),
                    strokeWidth = 1f,
                    pathEffect = dash,
                )
            }

            if (!hasData) return@Canvas

            series.forEach { s ->
                if (s.values.size < 2) return@forEach
                val step = w / (s.values.size - 1).toFloat()
                fun pointAt(i: Int): Offset {
                    val v = s.values[i].coerceIn(0.0, 100.0).toFloat()
                    return Offset(i * step, h * (1f - v / 100f))
                }

                // Filled area under the line, faded out downward so overlapping
                // series stay readable where they cross.
                val fill = Path().apply {
                    moveTo(0f, h)
                    for (i in s.values.indices) {
                        val p = pointAt(i)
                        lineTo(p.x, p.y)
                    }
                    lineTo(w, h)
                    close()
                }
                drawPath(
                    fill,
                    Brush.verticalGradient(
                        listOf(s.color.copy(alpha = 0.22f), s.color.copy(alpha = 0f)),
                    ),
                )

                val line = Path().apply {
                    val first = pointAt(0)
                    moveTo(first.x, first.y)
                    for (i in 1 until s.values.size) {
                        val p = pointAt(i)
                        lineTo(p.x, p.y)
                    }
                }
                drawPath(line, s.color, style = Stroke(width = 2.dp.toPx()))
            }
        }
    }
}

data class Series(val label: String, val values: List<Double>, val color: Color)

/**
 * Compact trace with no axes, for embedding in a card next to a number.
 */
@Composable
fun Sparkline(
    values: List<Double>,
    color: Color,
    modifier: Modifier = Modifier,
    height: Int = 28,
) {
    Canvas(modifier.fillMaxWidth().height(height.dp)) {
        if (values.size < 2) return@Canvas
        val w = size.width
        val h = size.height
        val step = w / (values.size - 1).toFloat()
        val path = Path()
        values.forEachIndexed { i, v ->
            val y = h * (1f - (v.coerceIn(0.0, 100.0).toFloat() / 100f))
            if (i == 0) path.moveTo(0f, y) else path.lineTo(i * step, y)
        }
        drawPath(path, color, style = Stroke(width = 1.5.dp.toPx()))
    }
}

/**
 * Horizontal stacked bar — used for HTTP status class breakdowns.
 */
@Composable
fun StackedBar(
    segments: List<Pair<Int, Color>>,
    modifier: Modifier = Modifier,
    height: Int = 8,
) {
    val total = segments.sumOf { it.first }.coerceAtLeast(1)
    Canvas(modifier.fillMaxWidth().height(height.dp)) {
        var x = 0f
        segments.forEach { (count, color) ->
            if (count <= 0) return@forEach
            val w = size.width * (count.toFloat() / total)
            drawRect(color = color, topLeft = Offset(x, 0f), size = androidx.compose.ui.geometry.Size(w, size.height))
            x += w
        }
    }
}

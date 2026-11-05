package dev.carbonpanel.widget

import android.appwidget.AppWidgetManager
import android.content.Context
import androidx.compose.runtime.Composable
import androidx.datastore.preferences.core.Preferences
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.currentState
import androidx.glance.GlanceModifier
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.LocalContext
import androidx.glance.LocalSize
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.SizeMode
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.state.PreferencesGlanceStateDefinition
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.size
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import dev.carbonpanel.MainActivity
import dev.carbonpanel.data.NetUnit
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.data.WidgetState
import java.util.concurrent.TimeUnit
import kotlin.math.min
import kotlin.math.ceil


/**
 * Home-screen widget: ring gauges plus a throughput line, sized to whatever
 * cell the user drops it into.
 *
 * Deliberately not live. WorkManager's floor is 15 minutes and the platform
 * ignores widget update periods under 30, so a real-time gauge isn't
 * achievable regardless of how it's written. Showing a stale number as current
 * would be worse than showing it with its age, so the timestamp is part of the
 * design rather than an apology for it.
 */
class StatusWidget : GlanceAppWidget() {

    // Exact rather than Responsive: the layout scales continuously off the real
    // measured size instead of snapping between a few hand-declared buckets.
    override val sizeMode = SizeMode.Exact

    // Composing from Glance's own store rather than reading SharedPreferences
    // directly. currentState is observable Compose state, so a change actually
    // invalidates the running composition — a plain preference read is not
    // observed by anything, and with a live SessionWorker the composable is
    // simply skipped and the previous RemoteViews re-sent. See WidgetBridge.
    override val stateDefinition = PreferencesGlanceStateDefinition

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        provideContent {
            val store = currentState<Preferences>()
            val appPrefs = Prefs.get(context)

            val state = WidgetState.decode(
                WidgetBridge.snapshot(store) ?: appPrefs.widgetState,
            )
            val unit = NetUnit.from(WidgetBridge.netUnit(store))
            val serverName =
                state?.serverName?.ifBlank { null } ?: appPrefs.serverName ?: "CarbonPanel"
            val paired = appPrefs.isPaired
            val palette = WidgetPalette.from(
                context = context,
                themeMode = WidgetBridge.theme(store),
                accentName = WidgetBridge.accent(store),
            )

            val size = LocalSize.current
            val layout = widgetLayout(
                size.width, size.height, state?.gpuPresent == true,
                LocalContext.current.resources.displayMetrics.density,
                LocalContext.current.resources.configuration.fontScale,
                state?.stale == true,
            )

            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .background(palette.ground)
                    .cornerRadius(16.dp)
                    .padding(layout.pad)
                    .clickable(actionStartActivity<MainActivity>()),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (layout.showHeader) {
                    Row(
                        modifier = GlanceModifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            serverName,
                            maxLines = 1,
                            style = TextStyle(
                                color = ColorProvider(palette.accent),
                                fontSize = layout.headerSp,
                                fontWeight = FontWeight.Bold,
                            ),
                            modifier = GlanceModifier.defaultWeight(),
                        )
                        Text(
                            if (state == null || state.updatedAt == 0L) "—"
                            else age(state.updatedAt),
                            maxLines = 1,
                            style = TextStyle(color = ColorProvider(palette.dim), fontSize = layout.tinySp),
                        )
                    }
                    Spacer(GlanceModifier.height(layout.gap))
                }

                if (state == null) {
                    Text(
                        if (paired) "No data yet" else "Not paired",
                        style = TextStyle(color = ColorProvider(palette.dim), fontSize = layout.headerSp),
                    )
                } else {
                    // Each gauge takes an equal share of the width, so the row
                    // fills the widget instead of huddling in a wide cell.
                    Row(
                        modifier = GlanceModifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Gauge("CPU", state.cpuPercent, null, layout, palette, GlanceModifier.defaultWeight())
                        Gauge("RAM", state.memPercent, null, layout, palette, GlanceModifier.defaultWeight())
                        if (state.gpuPresent) {
                            Gauge(
                                "GPU",
                                state.gpuPercent,
                                // Core utilisation in the ring, VRAM under it —
                                // different numbers, and conflating them is the
                                // classic GPU-monitor mistake.
                                sub = if (layout.showSubLabels)
                                    "${gb(state.gpuMemUsedMb)}/${gb(state.gpuMemTotalMb)}" else null,
                                layout = layout,
                                palette = palette,
                                modifier = GlanceModifier.defaultWeight(),
                            )
                        }
                        Gauge(
                            state.diskMount.ifBlank { "Disk" },
                            state.diskPercent,
                            sub = if (layout.showSubLabels)
                                compactPair(state.diskUsedGb, state.diskTotalGb) else null,
                            layout = layout,
                            palette = palette,
                            modifier = GlanceModifier.defaultWeight(),
                        )
                    }

                    if (layout.showNetwork && state.netIface.isNotBlank()) {
                        Spacer(GlanceModifier.height(layout.gap))
                        Row(
                            modifier = GlanceModifier
                                .fillMaxWidth()
                                .background(palette.card)
                                .cornerRadius(8.dp)
                                .padding(horizontal = 10.dp, vertical = layout.netPadV),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "${state.netIface}:",
                                maxLines = 1,
                                style = TextStyle(
                                    color = ColorProvider(palette.fg),
                                    fontSize = layout.bodySp,
                                    fontWeight = FontWeight.Medium,
                                ),
                                modifier = GlanceModifier.defaultWeight(),
                            )
                            Text(
                                "↓ ${unit.format(state.netRxMbPerSec)}",
                                maxLines = 1,
                                style = TextStyle(
                                    color = ColorProvider(WidgetPalette.Blue), fontSize = layout.bodySp,
                                ),
                                modifier = GlanceModifier.defaultWeight(),
                            )
                            Spacer(GlanceModifier.width(10.dp))
                            Text(
                                "↑ ${unit.format(state.netTxMbPerSec)}",
                                maxLines = 1,
                                style = TextStyle(
                                    color = ColorProvider(palette.accent), fontSize = layout.bodySp,
                                ),
                                modifier = GlanceModifier.defaultWeight(),
                            )
                        }
                    }

                    if (layout.showStale) {
                        Spacer(GlanceModifier.height(4.dp))
                        Text(
                            "Server unreachable — showing last known",
                            maxLines = 1,
                            style = TextStyle(color = ColorProvider(WidgetPalette.Amber), fontSize = layout.tinySp),
                        )
                    }
                }
            }
        }
    }

    private fun gb(mb: Double): String =
        if (mb >= 1024) "%.1fG".format(mb / 1024) else "%.0fM".format(mb)

    /** "1.1/3.6T" rather than "1081/3666G" — shorter and easier to read. */
    private fun compactPair(usedGb: Double, totalGb: Double): String =
        if (totalGb >= 1024) "%.1f/%.1fT".format(usedGb / 1024, totalGb / 1024)
        else "%.0f/%.0fG".format(usedGb, totalGb)

    private fun age(timestampMillis: Long): String {
        val m = TimeUnit.MILLISECONDS.toMinutes(System.currentTimeMillis() - timestampMillis)
        return when {
            m < 1 -> "just now"
            m < 60 -> "${m}m ago"
            m < 1440 -> "${m / 60}h ago"
            else -> "${m / 1440}d ago"
        }
    }
}

/**
 * Everything that varies with the widget's cell size.
 *
 * Derived from the measured size rather than a handful of breakpoints, so the
 * widget grows smoothly instead of jumping between two fixed looks. Chrome is
 * dropped in priority order as space runs out — sub-labels, then the network
 * row, then the header. The rings are the point and are the last thing to go.
 */
internal data class Layout(
    val ring: Dp,
    val ringPx: Int,
    val pad: Dp,
    val gap: Dp,
    val netPadV: Dp,
    val headerSp: TextUnit,
    val bodySp: TextUnit,
    val tinySp: TextUnit,
    val labelSp: TextUnit,
    val showHeader: Boolean,
    val showNetwork: Boolean,
    val showSubLabels: Boolean,
    val showStale: Boolean,
    val requiredHeight: Dp,
)

// Bitmaps reach the launcher inside a Binder transaction capped near 1MB for
// the whole RemoteViews tree, and the launcher holds them resident for as long
// as the widget is placed. At 200px the four rings measured 1.1MB of bitmap
// memory in `dumpsys appwidget` — updating without error, but with no headroom
// and more launcher memory than a status widget deserves. 160px is ~410KB and
// is at most a 1.4x upscale at typical widget sizes.
private const val MAX_RING_PX = 160

/** Budget every rendered row, including font padding and accessibility scaling. */
internal fun widgetLayout(
    width: Dp,
    height: Dp,
    hasGpu: Boolean,
    density: Float,
    fontScale: Float,
    stale: Boolean,
): Layout {
    val gaugeCount = if (hasGpu) 4 else 3
    val pad = if (height < 100.dp) 8.dp else 12.dp
    val gap = if (height < 120.dp) 6.dp else 10.dp
    val netPadV = if (height < 160.dp) 6.dp else 8.dp
    val byWidth = ((width - pad * 2 - 6.dp * (gaugeCount - 1)) / gaugeCount)
        .value.coerceIn(1f, 104f)
    // TextView includes font padding. Leave room for its whole line rather than
    // treating a sp font size as the measured height in dp.
    fun line(sp: Float) = ceil(sp * fontScale.coerceAtLeast(1f) * 1.5f).dp
    var showHeader = height >= 96.dp
    var showNetwork = height >= 132.dp
    var ring = byWidth
    while (true) {
        val scale = (ring / 54f).coerceIn(0.85f, 1.5f)
        val header = 12 * scale
        val tiny = 10 * scale
        val label = (9 * scale).coerceAtMost(12f)
        val showStale = stale && showHeader
        val required = pad * 2 + ring.dp + 3.dp + line(label) +
            (if (showHeader) line(header) + gap else 0.dp) +
            (if (showNetwork) line(header) + netPadV * 2 + gap else 0.dp) +
            (if (showStale) 4.dp + line(tiny) else 0.dp)
        if (required <= height || ring <= 1f) {
            return Layout(
                ring = ring.dp,
                ringPx = min((ring * density).toInt(), MAX_RING_PX).coerceAtLeast(72),
                pad = pad,
                gap = gap,
                netPadV = netPadV,
                headerSp = header.sp,
                bodySp = header.sp,
                tinySp = tiny.sp,
                labelSp = label.sp,
                showHeader = showHeader,
                showNetwork = showNetwork,
                showSubLabels = ring >= 64f,
                showStale = showStale,
                requiredHeight = required,
            )
        }
        if (ring > 36f) {
            ring = (ring - 1f).coerceAtLeast(36f.coerceAtMost(byWidth))
        } else if (showNetwork) {
            showNetwork = false
            ring = byWidth
        } else if (showHeader) {
            showHeader = false
            ring = byWidth
        } else {
            ring -= 1f
        }
    }
}

@Composable
private fun Gauge(
    label: String,
    percent: Double,
    sub: String?,
    layout: Layout,
    palette: WidgetPalette,
    modifier: GlanceModifier = GlanceModifier,
) {
    val bitmap = RingRenderer.draw(
        percent = percent,
        color = WidgetPalette.usage(percent, palette.accent).toArgb(),
        trackColor = palette.track.toArgb(),
        textColor = palette.fg.toArgb(),
        sizePx = layout.ringPx,
        label = sub,
    )
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Image(
            provider = ImageProvider(bitmap),
            contentDescription = "$label ${percent.toInt()} percent",
            modifier = GlanceModifier.size(layout.ring),
        )
        Spacer(GlanceModifier.height(3.dp))
        Text(
            // Mountpoints double as labels; trimmed to the last segment so
            // "/mnt/storage" doesn't wrap under a narrow ring.
            label.substringAfterLast('/').ifBlank { label }.take(9),
            maxLines = 1,
            style = TextStyle(color = ColorProvider(palette.dim), fontSize = layout.labelSp),
        )
    }
}

class StatusWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = StatusWidget()

    /**
     * Fetch as soon as a widget is placed.
     *
     * Periodic work has a 15-minute floor and defaults to 30, and enqueuing it
     * does not run it now — so without this a freshly added widget sits on
     * "No data yet" for up to half an hour while the app itself shows live
     * numbers.
     */
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
    ) {
        super.onUpdate(context, appWidgetManager, appWidgetIds)
        StatusWidgetWorker.refreshNow(context)
    }
}

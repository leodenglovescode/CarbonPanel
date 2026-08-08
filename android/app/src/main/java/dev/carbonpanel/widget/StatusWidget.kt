package dev.carbonpanel.widget

import android.content.Context
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.padding
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.sp
import dev.carbonpanel.MainActivity
import dev.carbonpanel.data.Prefs
import java.util.concurrent.TimeUnit

/**
 * Home-screen widget showing the last known server state.
 *
 * Deliberately not live. WorkManager's minimum periodic interval is 15
 * minutes and the platform ignores widget update periods under 30, so a
 * real-time gauge is not achievable here regardless of how it's written.
 * Showing a stale number as though it were current would be worse than
 * showing it with an explicit age, so the timestamp is part of the design.
 */
class StatusWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val prefs = Prefs.get(context)
        val summary = prefs.widgetSummary
        val updatedAt = prefs.widgetUpdatedAt

        provideContent {
            GlanceTheme {
                Column(
                    modifier = GlanceModifier
                        .fillMaxSize()
                        .background(Color(0xFF0A0E0D))
                        .padding(12.dp())
                        .clickable(actionStartActivity<MainActivity>()),
                    verticalAlignment = Alignment.Vertical.CenterVertically,
                ) {
                    Text(
                        prefs.serverName ?: "CarbonPanel",
                        style = TextStyle(
                            color = ColorProvider(Color(0xFF00FF88)),
                            fontSize = 13.sp,
                        ),
                    )
                    Text(
                        summary ?: "Not paired",
                        style = TextStyle(
                            color = ColorProvider(Color(0xFFD8E0DC)),
                            fontSize = 12.sp,
                        ),
                    )
                    Text(
                        if (updatedAt > 0) relativeAge(updatedAt) else "—",
                        style = TextStyle(
                            color = ColorProvider(Color(0xFF8A9691)),
                            fontSize = 10.sp,
                        ),
                    )
                }
            }
        }
    }

    private fun relativeAge(timestampMillis: Long): String {
        val deltaMinutes = TimeUnit.MILLISECONDS.toMinutes(
            System.currentTimeMillis() - timestampMillis
        )
        return when {
            deltaMinutes < 1 -> "just now"
            deltaMinutes < 60 -> "${deltaMinutes}m ago"
            deltaMinutes < 1440 -> "${deltaMinutes / 60}h ago"
            else -> "${deltaMinutes / 1440}d ago"
        }
    }
}

private fun Int.dp() = androidx.compose.ui.unit.Dp(this.toFloat())

class StatusWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = StatusWidget()
}

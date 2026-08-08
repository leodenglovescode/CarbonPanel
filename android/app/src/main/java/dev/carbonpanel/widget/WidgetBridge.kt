package dev.carbonpanel.widget

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.glance.appwidget.state.updateAppWidgetState
import androidx.glance.appwidget.updateAll
import androidx.glance.state.PreferencesGlanceStateDefinition
import dev.carbonpanel.data.Prefs

/**
 * Pushes app state into Glance's own store, which is what the widget composes
 * from.
 *
 * Glance keeps a live composition in a SessionWorker. Plain reads inside the
 * composable — `Prefs.get(context).themeMode` and friends — are not Compose
 * state, so nothing observes them: with a session already running there is no
 * invalidation, the composable is skipped, and the previous RemoteViews are
 * re-sent unchanged. That is why the first theme switch repainted (session
 * started fresh) and every one after it appeared to do nothing.
 *
 * Writing through updateAppWidgetState makes the values real Compose state
 * backed by DataStore, so a change invalidates the composition and the widget
 * actually redraws.
 */
object WidgetBridge {

    val KEY_STATE = stringPreferencesKey("state")
    val KEY_THEME = stringPreferencesKey("theme")
    val KEY_ACCENT = stringPreferencesKey("accent")
    val KEY_NET_UNIT = stringPreferencesKey("net_unit")

    /**
     * Mirrors the current app preferences (and optionally a fresh data
     * snapshot) into every placed widget, then asks them to redraw.
     */
    suspend fun push(context: Context, snapshotJson: String? = null) {
        val prefs = Prefs.get(context)
        val json = snapshotJson ?: prefs.widgetState

        val manager = androidx.glance.appwidget.GlanceAppWidgetManager(context)
        val ids = manager.getGlanceIds(StatusWidget::class.java)
        for (id in ids) {
            updateAppWidgetState(context, PreferencesGlanceStateDefinition, id) { store ->
                store.toMutablePreferences().apply {
                    if (json != null) this[KEY_STATE] = json
                    this[KEY_THEME] = prefs.themeMode
                    this[KEY_ACCENT] = prefs.accent
                    this[KEY_NET_UNIT] = prefs.widgetNetUnit
                }
            }
        }
        StatusWidget().updateAll(context)
    }

    fun theme(prefs: Preferences): String = prefs[KEY_THEME] ?: "System"
    fun accent(prefs: Preferences): String = prefs[KEY_ACCENT] ?: "Carbon"
    fun netUnit(prefs: Preferences): String = prefs[KEY_NET_UNIT] ?: "Mbps"
    fun snapshot(prefs: Preferences): String? = prefs[KEY_STATE]
}

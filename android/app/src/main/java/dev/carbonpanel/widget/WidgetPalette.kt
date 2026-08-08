package dev.carbonpanel.widget

import android.content.Context
import android.content.res.Configuration
import androidx.compose.ui.graphics.Color
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.ui.theme.AccentChoice
import dev.carbonpanel.ui.theme.ThemeMode

/**
 * Colours for the widget, resolved from the same theme setting as the app.
 *
 * A widget can't read the app's Compose theme — it renders in the launcher's
 * process from RemoteViews — so the setting has to be re-resolved here against
 * the stored preference. Without this the widget stayed dark while the app
 * followed the user's choice, which looks like a bug even though both were
 * "working".
 */
data class WidgetPalette(
    val ground: Color,
    val card: Color,
    val track: Color,
    val fg: Color,
    val dim: Color,
    val accent: Color,
) {
    companion object {
        // Usage colours are semantic — "fine", "watch this", "wrong" — so they
        // are identical in both schemes and unaffected by the accent choice.
        val Amber = Color(0xFFFFB020)
        val Red = Color(0xFFFF4444)
        val Blue = Color(0xFF4DA6FF)

        fun forContext(context: Context): WidgetPalette {
            val prefs = Prefs.get(context)
            val mode = runCatching { ThemeMode.valueOf(prefs.themeMode) }
                .getOrDefault(ThemeMode.System)

            val dark = when (mode) {
                ThemeMode.Dark -> true
                ThemeMode.Light -> false
                // The launcher's configuration is the only signal available
                // here; there is no Compose composition to ask.
                ThemeMode.System ->
                    (context.resources.configuration.uiMode and
                        Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
            }

            val choice = AccentChoice.from(prefs.accent)
            // Material You seeds itself from the wallpaper at runtime and has no
            // fixed colour to copy here, so the widget falls back to the brand
            // accent rather than guessing.
            val seed = if (choice == AccentChoice.Dynamic) AccentChoice.Carbon.seed
                       else choice.seed

            return if (dark) {
                WidgetPalette(
                    ground = Color(0xFF0A0E0D),
                    card = Color(0xFF141A18),
                    track = Color(0xFF243029),
                    fg = Color(0xFFD8E0DC),
                    dim = Color(0xFF8A9691),
                    accent = seed,
                )
            } else {
                WidgetPalette(
                    ground = Color(0xFFF6F8F7),
                    card = Color(0xFFE9EEEC),
                    track = Color(0xFFD6DEDA),
                    fg = Color(0xFF141A18),
                    dim = Color(0xFF56635E),
                    // The neon accent is illegible on a light ground.
                    accent = darken(seed, 0.35f),
                )
            }
        }

        /** Usage ramp — identical in both schemes, since it carries meaning. */
        fun usage(percent: Double, accent: Color): Color = when {
            percent >= 90 -> Red
            percent >= 75 -> Amber
            else -> accent
        }

        private fun darken(c: Color, amount: Float) = Color(
            red = c.red * (1 - amount),
            green = c.green * (1 - amount),
            blue = c.blue * (1 - amount),
            alpha = c.alpha,
        )
    }
}

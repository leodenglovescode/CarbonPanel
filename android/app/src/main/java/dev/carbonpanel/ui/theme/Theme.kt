package dev.carbonpanel.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// Status colours are semantic, not decorative — they mean "fine", "watch this"
// and "wrong" — so they stay fixed regardless of the accent the user picks.
// Recolouring a disk-full warning to match a purple accent would lose meaning.
val Danger = Color(0xFFFF4444)
val Warning = Color(0xFFFFB020)
val Info = Color(0xFF4DA6FF)

/** The web panel's accent, and the app's default. */
val CarbonGreen = Color(0xFF00FF88)

/** Kept as `Accent` for call sites that want the brand colour specifically. */
val Accent = CarbonGreen

enum class ThemeMode { System, Light, Dark }

/**
 * Accent options.
 *
 * [Dynamic] defers to Material You, seeded from the user's wallpaper. It needs
 * Android 12; below that it silently falls back to Carbon so the setting never
 * appears broken on an older phone.
 */
enum class AccentChoice(val label: String, val seed: Color) {
    Carbon("Carbon", CarbonGreen),
    Dynamic("Material You", CarbonGreen),
    Emerald("Emerald", Color(0xFF10B981)),
    Cyan("Cyan", Color(0xFF22D3EE)),
    Blue("Blue", Color(0xFF3B82F6)),
    Violet("Violet", Color(0xFF8B5CF6)),
    Magenta("Magenta", Color(0xFFEC4899)),
    Amber("Amber", Color(0xFFF59E0B)),
    Crimson("Crimson", Color(0xFFEF4444));

    companion object {
        fun from(name: String?): AccentChoice =
            entries.firstOrNull { it.name == name } ?: Carbon

        val dynamicSupported: Boolean get() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
    }
}

private fun darkSchemeFor(seed: Color) = darkColorScheme(
    primary = seed,
    onPrimary = Color(0xFF04120C),
    primaryContainer = seed.copy(alpha = 0.18f).compositeOver(Color(0xFF0E1614)),
    onPrimaryContainer = seed,
    secondary = seed.copy(alpha = 0.75f).compositeOver(Color(0xFF0A0E0D)),
    // FilterChip's selected container reads from secondaryContainer; leaving
    // it undefined made every selected chip Material's default purple
    // regardless of the chosen accent.
    secondaryContainer = seed.copy(alpha = 0.22f).compositeOver(Color(0xFF0E1614)),
    onSecondaryContainer = seed,
    background = Color(0xFF0A0E0D),
    onBackground = Color(0xFFD8E0DC),
    surface = Color(0xFF111614),
    onSurface = Color(0xFFD8E0DC),
    surfaceVariant = Color(0xFF161C1A),
    onSurfaceVariant = Color(0xFF8A9691),
    surfaceContainer = Color(0xFF141A18),
    surfaceContainerHigh = Color(0xFF1A211E),
    outline = Color(0xFF2A3330),
    outlineVariant = Color(0xFF1E2624),
    error = Danger,
    onError = Color(0xFF2A0606),
)

private fun lightSchemeFor(seed: Color) = lightColorScheme(
    // The neon accent is unreadable as text on white, so light mode darkens it
    // rather than using the seed directly.
    primary = seed.darken(0.35f),
    onPrimary = Color.White,
    primaryContainer = seed.copy(alpha = 0.20f).compositeOver(Color.White),
    onPrimaryContainer = seed.darken(0.55f),
    secondary = seed.darken(0.25f),
    secondaryContainer = seed.copy(alpha = 0.22f).compositeOver(Color.White),
    onSecondaryContainer = seed.darken(0.55f),
    background = Color(0xFFF6F8F7),
    onBackground = Color(0xFF141A18),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF141A18),
    surfaceVariant = Color(0xFFE8EDEB),
    onSurfaceVariant = Color(0xFF56635E),
    surfaceContainer = Color(0xFFF0F3F2),
    surfaceContainerHigh = Color(0xFFE9EEEC),
    outline = Color(0xFFCBD5D1),
    outlineVariant = Color(0xFFDFE6E3),
    error = Danger,
    onError = Color.White,
)

private fun Color.darken(amount: Float): Color = Color(
    red = red * (1 - amount),
    green = green * (1 - amount),
    blue = blue * (1 - amount),
    alpha = alpha,
)

private fun Color.compositeOver(background: Color): Color {
    val a = alpha
    return Color(
        red = red * a + background.red * (1 - a),
        green = green * a + background.green * (1 - a),
        blue = blue * a + background.blue * (1 - a),
        alpha = 1f,
    )
}

private val Mono = FontFamily.Monospace

private val MonoTypography = Typography().run {
    copy(
        displaySmall = displaySmall.copy(fontFamily = Mono, fontWeight = FontWeight.Medium),
        headlineLarge = headlineLarge.copy(fontFamily = Mono),
        headlineMedium = headlineMedium.copy(fontFamily = Mono, fontWeight = FontWeight.Medium),
        headlineSmall = headlineSmall.copy(fontFamily = Mono),
        titleLarge = titleLarge.copy(fontFamily = Mono, fontSize = 19.sp),
        titleMedium = titleMedium.copy(fontFamily = Mono, fontSize = 15.sp),
        titleSmall = titleSmall.copy(fontFamily = Mono, fontSize = 13.sp),
        bodyLarge = bodyLarge.copy(fontFamily = Mono, fontSize = 14.sp),
        bodyMedium = bodyMedium.copy(fontFamily = Mono, fontSize = 13.sp),
        bodySmall = bodySmall.copy(fontFamily = Mono, fontSize = 11.sp, lineHeight = 16.sp),
        labelLarge = labelLarge.copy(fontFamily = Mono, fontSize = 13.sp),
        labelMedium = labelMedium.copy(fontFamily = Mono, fontSize = 11.sp),
        labelSmall = labelSmall.copy(fontFamily = Mono, fontSize = 10.sp, letterSpacing = 0.8.sp),
    )
}

/** Big numeric readouts (the percentage on a metric card). */
val NumericStyle = TextStyle(fontFamily = Mono, fontSize = 30.sp, fontWeight = FontWeight.Medium)

/**
 * Whether a background image is painted behind the content. Cards need more
 * opacity over a photo, and threading a boolean through every composable
 * would be noise.
 */
val LocalHasBackdrop = staticCompositionLocalOf { false }

@Composable
fun CarbonTheme(
    mode: ThemeMode = ThemeMode.System,
    accent: AccentChoice = AccentChoice.Carbon,
    hasBackdrop: Boolean = false,
    content: @Composable () -> Unit,
) {
    val dark = when (mode) {
        ThemeMode.System -> isSystemInDarkTheme()
        ThemeMode.Light -> false
        ThemeMode.Dark -> true
    }
    val context = LocalContext.current

    val scheme: ColorScheme = when {
        accent == AccentChoice.Dynamic && AccentChoice.dynamicSupported ->
            if (dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        dark -> darkSchemeFor(accent.seed)
        else -> lightSchemeFor(accent.seed)
    }

    CompositionLocalProvider(LocalHasBackdrop provides hasBackdrop) {
        MaterialTheme(colorScheme = scheme, typography = MonoTypography, content = content)
    }
}

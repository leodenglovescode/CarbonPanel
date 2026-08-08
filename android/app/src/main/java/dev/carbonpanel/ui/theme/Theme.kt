package dev.carbonpanel.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.sp

// Mirrors the web panel's CSS variables so the two don't look like different
// products: monospace everywhere, near-black ground, #00ff88 accent.
val Accent = Color(0xFF00FF88)
val Danger = Color(0xFFFF4444)
val Warning = Color(0xFFFFB020)

private val DarkColors = darkColorScheme(
    primary = Accent,
    onPrimary = Color(0xFF04120C),
    secondary = Accent,
    background = Color(0xFF0A0E0D),
    onBackground = Color(0xFFD8E0DC),
    surface = Color(0xFF111614),
    onSurface = Color(0xFFD8E0DC),
    surfaceVariant = Color(0xFF161C1A),
    onSurfaceVariant = Color(0xFF8A9691),
    outline = Color(0xFF2A3330),
    error = Danger,
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF00A85A),
    onPrimary = Color.White,
    background = Color(0xFFF6F8F7),
    onBackground = Color(0xFF141A18),
    surface = Color.White,
    onSurface = Color(0xFF141A18),
    surfaceVariant = Color(0xFFE8EDEB),
    onSurfaceVariant = Color(0xFF56635E),
    outline = Color(0xFFCBD5D1),
    error = Danger,
)

private val MonoTypography = Typography().run {
    val mono = FontFamily.Monospace
    copy(
        displayLarge = displayLarge.copy(fontFamily = mono),
        headlineMedium = headlineMedium.copy(fontFamily = mono),
        titleLarge = titleLarge.copy(fontFamily = mono),
        titleMedium = titleMedium.copy(fontFamily = mono),
        bodyLarge = bodyLarge.copy(fontFamily = mono),
        bodyMedium = bodyMedium.copy(fontFamily = mono),
        bodySmall = bodySmall.copy(fontFamily = mono, fontSize = 11.sp),
        labelSmall = labelSmall.copy(fontFamily = mono),
        labelMedium = labelMedium.copy(fontFamily = mono),
    )
}

val NumericStyle = TextStyle(fontFamily = FontFamily.Monospace, fontSize = 28.sp)

@Composable
fun CarbonTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = MonoTypography,
        content = content,
    )
}

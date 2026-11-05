package dev.carbonpanel.ui.components

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.ImageLoader
import coil.compose.AsyncImage
import coil.request.ImageRequest
import dev.carbonpanel.data.BackgroundConfig
import dev.carbonpanel.net.ApiClient
import kotlin.math.cos
import kotlin.math.sin

/** Uses the server's saved Android crop and display settings over the pinned API connection. */
@Composable
fun Backdrop(
    enabled: Boolean,
    config: BackgroundConfig? = null,
    target: String = "android-app",
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val url = if (enabled && config?.type == "image") ApiClient.backgroundImageUrl(context, target, config.version) else null
    Box(modifier.fillMaxSize()) {
        if (enabled && config != null) {
            val b = config.brightness / 100f
            val brightness = ColorFilter.colorMatrix(ColorMatrix(floatArrayOf(
                b, 0f, 0f, 0f, 0f, 0f, b, 0f, 0f, 0f,
                0f, 0f, b, 0f, 0f, 0f, 0f, 0f, 1f, 0f,
            )))
            if (url != null) AsyncImage(
                model = ImageRequest.Builder(context).data(url).crossfade(220).build(),
                imageLoader = rememberAuthedImageLoader(context), contentDescription = null,
                colorFilter = brightness, contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize().blur(config.blur.dp),
            )
            if (config.type == "gradient") {
                val angle = Math.toRadians(config.gradientAngle.toDouble())
                androidx.compose.foundation.Canvas(Modifier.fillMaxSize().blur(config.blur.dp)) {
                    val dx = sin(angle).toFloat()
                    val dy = -cos(angle).toFloat()
                    val extent = (kotlin.math.abs(size.width * dx) + kotlin.math.abs(size.height * dy)) / 2
                    val center = Offset(size.width / 2, size.height / 2)
                    fun parse(value: String): Color {
                        val color = runCatching { Color(android.graphics.Color.parseColor(value)) }.getOrDefault(Color.Black)
                        return Color((color.red * b).coerceIn(0f, 1f), (color.green * b).coerceIn(0f, 1f), (color.blue * b).coerceIn(0f, 1f))
                    }
                    drawRect(Brush.linearGradient(listOf(parse(config.gradientStart), parse(config.gradientEnd)), center - Offset(dx * extent, dy * extent), center + Offset(dx * extent, dy * extent)))
                }
            }
            Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background.copy(alpha = config.overlay / 100f)))
        }
        content()
    }
}

@Composable
private fun rememberAuthedImageLoader(context: Context): ImageLoader = remember {
    ImageLoader.Builder(context).okHttpClient { ApiClient.imageClient(context) }.build()
}

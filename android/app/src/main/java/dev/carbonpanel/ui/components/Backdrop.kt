package dev.carbonpanel.ui.components

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import coil.ImageLoader
import coil.compose.AsyncImage
import coil.request.ImageRequest
import dev.carbonpanel.net.ApiClient

/**
 * Paints the panel's configured background image behind the app.
 *
 * The image is served from `/settings/background-image/app`, which requires
 * authentication and frequently sits behind a self-signed certificate — so it
 * is loaded through the same OkHttp instance the API uses. A stock loader
 * would 401, or fail the TLS handshake outright.
 *
 * A scrim is mandatory rather than decorative: the panel accepts arbitrary
 * user photos, and monospace text on an unmodified photo is unreadable often
 * enough that "sometimes fine" isn't good enough.
 */
@Composable
fun Backdrop(
    enabled: Boolean,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val url = remember(enabled) { if (enabled) ApiClient.backgroundImageUrl(context) else null }

    Box(modifier.fillMaxSize()) {
        if (url != null) {
            AsyncImage(
                model = ImageRequest.Builder(context).data(url).crossfade(220).build(),
                imageLoader = rememberAuthedImageLoader(context),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
            )
            // Slightly heavier at the top and bottom, where the app bar and
            // navigation bar sit, than through the middle.
            Box(
                Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            0f to Color.Black.copy(alpha = 0.80f),
                            0.28f to Color.Black.copy(alpha = 0.62f),
                            0.75f to Color.Black.copy(alpha = 0.66f),
                            1f to Color.Black.copy(alpha = 0.84f),
                        ),
                    ),
            )
        }
        content()
    }
}

@Composable
private fun rememberAuthedImageLoader(context: Context): ImageLoader = remember {
    ImageLoader.Builder(context)
        .okHttpClient { ApiClient.imageClient(context) }
        .build()
}

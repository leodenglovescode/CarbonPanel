package dev.carbonpanel.net

import android.content.Context
import dev.carbonpanel.data.Prefs
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.net.InetAddress
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.X509TrustManager

/**
 * Builds Retrofit clients and decides which base URL to use.
 *
 * A self-hosted panel usually has several addresses and which one works
 * depends on where the phone is: a LAN address is fastest at home and dead
 * everywhere else, while a Tailscale/WireGuard address works from anywhere.
 * Pairing therefore hands over a list, and this class resolves it per session
 * rather than committing to one at pair time.
 */
object ApiClient {

    private val json = Json {
        ignoreUnknownKeys = true   // server adds fields faster than the app adopts them
        coerceInputValues = true
        explicitNulls = false
    }

    @Volatile
    private var cached: Pair<String, Api>? = null

    fun clearCache() {
        cached = null
    }

    private fun okHttp(context: Context): OkHttpClient {
        val prefs = Prefs.get(context)
        val trustManager = TofuTrustManager(prefs)
        val sslContext = SSLContext.getInstance("TLS").apply {
            init(null, arrayOf(trustManager), java.security.SecureRandom())
        }

        return OkHttpClient.Builder()
            .sslSocketFactory(sslContext.socketFactory, trustManager as X509TrustManager)
            // Short timeouts: with several candidate endpoints, failing fast and
            // moving to the next one beats waiting out a dead LAN address.
            .connectTimeout(4, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .callTimeout(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .addInterceptor(authInterceptor(prefs))
            .build()
    }

    private fun authInterceptor(prefs: Prefs) = Interceptor { chain ->
        val builder = chain.request().newBuilder()
        prefs.token?.let { builder.header("Authorization", "Bearer $it") }
        // Lets the server distinguish this device among several polling
        // clients when it tracks per-client collection rates.
        builder.header("X-Device-Id", prefs.deviceId)
        chain.proceed(builder.build())
    }

    fun forBaseUrl(context: Context, baseUrl: String): Api {
        cached?.let { (url, api) -> if (url == baseUrl) return api }
        val api = Retrofit.Builder()
            .baseUrl(baseUrl.trimEnd('/') + "/")
            .client(okHttp(context))
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(Api::class.java)
        cached = baseUrl to api
        return api
    }

    /**
     * Pick a working endpoint, preferring the one that worked last time.
     *
     * Tried sequentially rather than raced: a race would fire an authenticated
     * request at every address the user has configured, including ones that
     * leave the local network, every time the app cold-starts. Sequential with
     * a short timeout is slower in the worst case and much better behaved.
     */
    suspend fun resolve(context: Context): Pair<String, Api>? = withContext(Dispatchers.IO) {
        val prefs = Prefs.get(context)
        val candidates = buildList {
            prefs.lastGoodEndpoint?.let { add(it) }
            addAll(prefs.endpoints.filter { it != prefs.lastGoodEndpoint })
        }.filter { isPermittedEndpoint(it) }

        for (url in candidates) {
            val api = forBaseUrl(context, url)
            val ok = withTimeoutOrNull(5_000) {
                runCatching { api.ping().isSuccessful }.getOrDefault(false)
            } ?: false
            if (ok) {
                prefs.lastGoodEndpoint = url
                return@withContext url to api
            }
        }
        null
    }

    /**
     * Refuse cleartext to anything that isn't plainly a private or overlay
     * address.
     *
     * The manifest permits cleartext app-wide because a network-security-config
     * cannot express "private ranges only" (no CIDR support), so the narrowing
     * happens here: an http:// endpoint pointing at a public address would put
     * the bearer token on the open internet in plaintext, and no self-hosted
     * setup needs that.
     */
    fun isPermittedEndpoint(url: String): Boolean {
        if (url.startsWith("https://", ignoreCase = true)) return true
        if (!url.startsWith("http://", ignoreCase = true)) return false

        val host = runCatching { java.net.URI(url).host }.getOrNull() ?: return false
        val bare = host.trim('[', ']')
        if (bare.equals("localhost", ignoreCase = true)) return true

        val addr = runCatching { InetAddress.getByName(bare) }.getOrNull() ?: return false
        if (addr.isLoopbackAddress || addr.isSiteLocalAddress || addr.isLinkLocalAddress) return true

        // Tailscale/Headscale CGNAT range (100.64.0.0/10), which Java does not
        // classify as site-local.
        val bytes = addr.address
        if (bytes.size == 4) {
            val first = bytes[0].toInt() and 0xFF
            val second = bytes[1].toInt() and 0xFF
            if (first == 100 && second in 64..127) return true
        }
        // IPv6 unique-local (fc00::/7), which covers Tailscale's fd7a:… prefix.
        if (bytes.size == 16 && (bytes[0].toInt() and 0xFE) == 0xFC) return true

        return false
    }
}

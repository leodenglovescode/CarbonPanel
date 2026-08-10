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
import java.net.URI
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

    @Volatile
    private var sharedClient: OkHttpClient? = null

    /** Base URL most recently confirmed working, for building absolute URLs. */
    @Volatile
    var activeBaseUrl: String? = null
        private set

    fun clearCache() {
        cached = null
        sharedClient = null
    }

    /**
     * The same OkHttp instance the API uses — shared with Coil so background
     * images inherit the bearer token and the pinned-certificate trust manager.
     * Loading them with a stock client would 401, and on a self-signed host it
     * would fail the handshake outright.
     */
    fun imageClient(context: Context): OkHttpClient =
        sharedClient ?: synchronized(this) {
            sharedClient ?: okHttp(context).also { sharedClient = it }
        }

    /** Absolute URL of the panel's app background image, or null if unpaired. */
    fun backgroundImageUrl(context: Context): String? {
        val base = activeBaseUrl ?: Prefs.get(context).lastGoodEndpoint ?: return null
        return base.trimEnd('/') + "/api/v1/settings/background-image/app"
    }

    private fun okHttp(context: Context): OkHttpClient {
        val prefs = Prefs.get(context)
        val trustManager = PinnedTrustManager(prefs)
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
                activeBaseUrl = url
                return@withContext url to api
            }
        }
        null
    }

    /** Bearer tokens are never sent over cleartext, even on a private network. */
    fun isPermittedEndpoint(url: String): Boolean {
        val parsed = runCatching { URI(url) }.getOrNull() ?: return false
        return parsed.scheme.equals("https", ignoreCase = true) &&
            !parsed.host.isNullOrBlank() &&
            parsed.userInfo == null &&
            parsed.rawQuery == null &&
            parsed.rawFragment == null
    }
}

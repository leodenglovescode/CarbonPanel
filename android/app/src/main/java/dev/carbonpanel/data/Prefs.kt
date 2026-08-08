package dev.carbonpanel.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Persistent state for a paired server.
 *
 * The bearer token is the whole of the app's authority over the panel, so it
 * lives in EncryptedSharedPreferences (AES-256, key held in the Android
 * keystore) rather than plain prefs. Everything else here is stored alongside
 * it for simplicity — none of it is secret, but splitting stores would buy
 * nothing.
 */
class Prefs(context: Context) {

    private val prefs: SharedPreferences = run {
        val key = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "carbonpanel.secure",
            key,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    var token: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(v) = prefs.edit().putString(KEY_TOKEN, v).apply()

    var username: String?
        get() = prefs.getString(KEY_USERNAME, null)
        set(v) = prefs.edit().putString(KEY_USERNAME, v).apply()

    var serverName: String?
        get() = prefs.getString(KEY_SERVER_NAME, null)
        set(v) = prefs.edit().putString(KEY_SERVER_NAME, v).apply()

    /** Candidate base URLs, best-first, as delivered in the pairing QR. */
    var endpoints: List<String>
        get() = prefs.getString(KEY_ENDPOINTS, null)
            ?.split('\n')?.filter { it.isNotBlank() } ?: emptyList()
        set(v) = prefs.edit().putString(KEY_ENDPOINTS, v.joinToString("\n")).apply()

    /**
     * The endpoint that most recently worked. Tried first on the next
     * connection so the common case — same network as last time — costs one
     * request rather than a walk down the whole list.
     */
    var lastGoodEndpoint: String?
        get() = prefs.getString(KEY_LAST_GOOD, null)
        set(v) = prefs.edit().putString(KEY_LAST_GOOD, v).apply()

    /** Poll interval in seconds while the app is foregrounded. */
    var pollIntervalSeconds: Float
        get() = prefs.getFloat(KEY_POLL_INTERVAL, 2.0f)
        set(v) = prefs.edit().putFloat(KEY_POLL_INTERVAL, v).apply()

    val isPaired: Boolean get() = !token.isNullOrBlank() && endpoints.isNotEmpty()

    /**
     * Stable per-install identifier, sent as X-Device-Id. Lets the server tell
     * this client apart from other pollers when tracking per-client collection
     * rates, and lets a re-pair update the existing device row instead of
     * creating a duplicate.
     */
    val deviceId: String
        get() = prefs.getString(KEY_DEVICE_ID, null) ?: java.util.UUID.randomUUID().toString()
            .also { prefs.edit().putString(KEY_DEVICE_ID, it).apply() }

    // ── Certificate pinning (trust on first use) ───────────────────────────

    fun pinnedCert(host: String): String? = prefs.getString(pinKey(host), null)

    fun setPinnedCert(host: String, sha256: String) {
        prefs.edit().putString(pinKey(host), sha256).apply()
    }

    // ── Widget cache ───────────────────────────────────────────────────────

    /** Last snapshot rendered on the home-screen widget, as a summary line. */
    var widgetSummary: String?
        get() = prefs.getString(KEY_WIDGET_SUMMARY, null)
        set(v) = prefs.edit().putString(KEY_WIDGET_SUMMARY, v).apply()

    var widgetUpdatedAt: Long
        get() = prefs.getLong(KEY_WIDGET_TS, 0L)
        set(v) = prefs.edit().putLong(KEY_WIDGET_TS, v).apply()

    fun clear() {
        prefs.edit().clear().apply()
    }

    private fun pinKey(host: String) = "$KEY_PIN_PREFIX${host.lowercase()}"

    companion object {
        private const val KEY_TOKEN = "token"
        private const val KEY_USERNAME = "username"
        private const val KEY_SERVER_NAME = "server_name"
        private const val KEY_ENDPOINTS = "endpoints"
        private const val KEY_LAST_GOOD = "last_good_endpoint"
        private const val KEY_POLL_INTERVAL = "poll_interval"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_PIN_PREFIX = "pin:"
        private const val KEY_WIDGET_SUMMARY = "widget_summary"
        private const val KEY_WIDGET_TS = "widget_ts"

        @Volatile
        private var instance: Prefs? = null

        fun get(context: Context): Prefs =
            instance ?: synchronized(this) {
                instance ?: Prefs(context.applicationContext).also { instance = it }
            }
    }
}

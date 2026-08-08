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

    /**
     * Whether to paint the panel's configured background image behind the app.
     * Off by default: it costs a network fetch on launch, and a photo behind
     * dense monospace readouts is a taste call rather than an obvious win.
     */
    var backdropEnabled: Boolean
        get() = prefs.getBoolean(KEY_BACKDROP, false)
        set(v) = prefs.edit().putBoolean(KEY_BACKDROP, v).apply()

    /** "System" | "Light" | "Dark" — resolved by CarbonTheme. */
    var themeMode: String
        get() = prefs.getString(KEY_THEME_MODE, "System") ?: "System"
        set(v) = prefs.edit().putString(KEY_THEME_MODE, v).apply()

    /** Name of an AccentChoice entry. */
    var accent: String
        get() = prefs.getString(KEY_ACCENT, "Carbon") ?: "Carbon"
        set(v) = prefs.edit().putString(KEY_ACCENT, v).apply()

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

    // ── Widget ─────────────────────────────────────────────────────────────

    /** Serialised WidgetState from the last successful refresh. */
    var widgetState: String?
        get() = prefs.getString(KEY_WIDGET_STATE, null)
        set(v) = prefs.edit().putString(KEY_WIDGET_STATE, v).apply()

    /**
     * Mountpoint the widget's disk ring tracks. Blank means "largest disk",
     * which is a better default than picking `/` — on a server the big data
     * volume is usually the one worth watching.
     */
    var widgetDisk: String
        get() = prefs.getString(KEY_WIDGET_DISK, "") ?: ""
        set(v) = prefs.edit().putString(KEY_WIDGET_DISK, v).apply()

    /** Interface the widget's throughput line tracks. Blank means "busiest". */
    var widgetIface: String
        get() = prefs.getString(KEY_WIDGET_IFACE, "") ?: ""
        set(v) = prefs.edit().putString(KEY_WIDGET_IFACE, v).apply()

    /** Name of a NetUnit entry. */
    var widgetNetUnit: String
        get() = prefs.getString(KEY_WIDGET_NET_UNIT, "Mbps") ?: "Mbps"
        set(v) = prefs.edit().putString(KEY_WIDGET_NET_UNIT, v).apply()

    /**
     * Minutes between widget refreshes. 15 is WorkManager's floor; the default
     * is deliberately higher because a home-screen widget is glanced at, not
     * watched, and each refresh is a radio wake-up.
     */
    var widgetRefreshMinutes: Int
        get() = prefs.getInt(KEY_WIDGET_REFRESH, 30)
        set(v) = prefs.edit().putInt(KEY_WIDGET_REFRESH, v.coerceAtLeast(15)).apply()

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
        private const val KEY_BACKDROP = "backdrop_enabled"
        private const val KEY_THEME_MODE = "theme_mode"
        private const val KEY_ACCENT = "accent"
        private const val KEY_PIN_PREFIX = "pin:"
        private const val KEY_WIDGET_STATE = "widget_state"
        private const val KEY_WIDGET_DISK = "widget_disk"
        private const val KEY_WIDGET_IFACE = "widget_iface"
        private const val KEY_WIDGET_NET_UNIT = "widget_net_unit"
        private const val KEY_WIDGET_REFRESH = "widget_refresh_minutes"

        @Volatile
        private var instance: Prefs? = null

        fun get(context: Context): Prefs =
            instance ?: synchronized(this) {
                instance ?: Prefs(context.applicationContext).also { instance = it }
            }
    }
}

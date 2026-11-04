package dev.carbonpanel.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

data class SavedServer(
    val id: String,
    val name: String,
    val username: String,
    val endpoints: List<String>,
)

/**
 * Persistent state for a paired server.
 *
 * The bearer token is the whole of the app's authority over the panel, so it
 * lives in EncryptedSharedPreferences (AES-256, key held in the Android
 * keystore) rather than plain prefs. Everything else here is stored alongside
 * it for simplicity — none of it is secret, but splitting stores would buy
 * nothing.
 */
class Prefs internal constructor(
    private val prefs: SharedPreferences,
    val serverId: String,
) {
    private fun scoped(key: String) = "server:$serverId:$key"

    val activeServerId: String? get() = prefs.getString("active_server", null)
    val servers: List<SavedServer> get() =
        prefs.getString("servers", "").orEmpty().split('\n').filter { it.isNotBlank() }.map { id ->
            val server = forServer(id)
            SavedServer(id, server.serverName ?: "CarbonPanel", server.username.orEmpty(),
                server.endpoints)
        }

    fun forServer(id: String) = Prefs(prefs, id)
    fun newServer() = forServer(java.util.UUID.randomUUID().toString())

    fun activate(id: String) {
        require(servers.any { it.id == id })
        prefs.edit().putString("active_server", id).commit()
    }

    fun saveServer() {
        val ids = (servers.map { it.id } + serverId).distinct()
        prefs.edit().putString("servers", ids.joinToString("\n"))
            .putString("active_server", serverId).commit()
    }

    fun renameServer(id: String, name: String) {
        if (name.isNotBlank()) forServer(id).serverName = name.trim()
    }

    fun removeServer(id: String) {
        val remaining = servers.map { it.id }.filterNot { it == id }
        val editor = prefs.edit().putString("servers", remaining.joinToString("\n"))
        prefs.all.keys.filter { it.startsWith("server:$id:") }.forEach { editor.remove(it) }
        if (activeServerId == id) editor.putString("active_server", remaining.firstOrNull())
        editor.commit()
    }

    companion object {
        @Volatile private var instance: Prefs? = null

        fun get(context: Context): Prefs {
            val root = instance ?: synchronized(this) {
                instance ?: open(context.applicationContext).also { instance = it }
            }
            return root.forServer(root.activeServerId ?: "unpaired")
        }

        private fun open(context: Context): Prefs {
            val key = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            val prefs = EncryptedSharedPreferences.create(
                context,
                "carbonpanel.secure",
                key,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
            migrateLegacyPrefs(prefs)
            return Prefs(prefs, prefs.getString("active_server", null) ?: "unpaired")
        }

        internal fun migrateLegacyPrefs(prefs: SharedPreferences) {
            // Upgrade the original single-server store without losing its pairing or pins.
            if (!prefs.contains("servers") && !prefs.getString(KEY_TOKEN, null).isNullOrBlank()) {
                val editor = prefs.edit()
                val keys = setOf(KEY_TOKEN, KEY_USERNAME, KEY_SERVER_NAME, KEY_ENDPOINTS,
                    KEY_LAST_GOOD, KEY_WIDGET_STATE, KEY_WIDGET_DISK, KEY_WIDGET_IFACE)
                prefs.all.forEach { (key, value) ->
                    if (key in keys || key.startsWith(KEY_PIN_PREFIX)) {
                        editor.putString("server:legacy:$key", value as? String).remove(key)
                    }
                }
                editor.putString("servers", "legacy").putString("active_server", "legacy").commit()
            }
        }

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
    }

    var token: String?
        get() = prefs.getString(scoped(KEY_TOKEN), null)
        set(v) = prefs.edit().putString(scoped(KEY_TOKEN), v).apply()

    var username: String?
        get() = prefs.getString(scoped(KEY_USERNAME), null)
        set(v) = prefs.edit().putString(scoped(KEY_USERNAME), v).apply()

    var serverName: String?
        get() = prefs.getString(scoped(KEY_SERVER_NAME), null)
        set(v) = prefs.edit().putString(scoped(KEY_SERVER_NAME), v).apply()

    /** Candidate base URLs, best-first, as delivered in the pairing QR. */
    var endpoints: List<String>
        get() = prefs.getString(scoped(KEY_ENDPOINTS), null)
            ?.split('\n')?.filter { it.isNotBlank() } ?: emptyList()
        set(v) = prefs.edit().putString(scoped(KEY_ENDPOINTS), v.joinToString("\n")).apply()

    /**
     * The endpoint that most recently worked. Tried first on the next
     * connection so the common case — same network as last time — costs one
     * request rather than a walk down the whole list.
     */
    var lastGoodEndpoint: String?
        get() = prefs.getString(scoped(KEY_LAST_GOOD), null)
        set(v) = prefs.edit().putString(scoped(KEY_LAST_GOOD), v).apply()

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

    // ── Certificate pinning (fingerprint delivered out-of-band by QR) ─────

    fun pinnedCert(host: String): String? = prefs.getString(pinKey(host), null)

    fun setPinnedCert(host: String, sha256: String) {
        prefs.edit().putString(pinKey(host), sha256).commit()
    }

    fun removePinnedCert(host: String) {
        prefs.edit().remove(pinKey(host)).commit()
    }

    // ── Widget ─────────────────────────────────────────────────────────────

    /** Serialised WidgetState from the last successful refresh. */
    var widgetState: String?
        get() = prefs.getString(scoped(KEY_WIDGET_STATE), null)
        set(v) = prefs.edit().putString(scoped(KEY_WIDGET_STATE), v).apply()

    /**
     * Mountpoint the widget's disk ring tracks. Blank means "largest disk",
     * which is a better default than picking `/` — on a server the big data
     * volume is usually the one worth watching.
     */
    var widgetDisk: String
        get() = prefs.getString(scoped(KEY_WIDGET_DISK), "") ?: ""
        set(v) = prefs.edit().putString(scoped(KEY_WIDGET_DISK), v).apply()

    /** Interface the widget's throughput line tracks. Blank means "busiest". */
    var widgetIface: String
        get() = prefs.getString(scoped(KEY_WIDGET_IFACE), "") ?: ""
        set(v) = prefs.edit().putString(scoped(KEY_WIDGET_IFACE), v).apply()

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
        removeServer(serverId)
    }

    private fun pinKey(host: String) = scoped("$KEY_PIN_PREFIX${host.lowercase()}")

}

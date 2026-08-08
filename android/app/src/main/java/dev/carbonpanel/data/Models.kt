package dev.carbonpanel.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Field names mirror the server's Pydantic schemas exactly rather than being
// renamed to Kotlin conventions. The panel's API is the source of truth and a
// rename layer here would be one more place for the two to drift apart.

// ── Pairing ────────────────────────────────────────────────────────────────

/**
 * Payload encoded in the QR code shown by the web panel.
 *
 * Single-letter keys because a QR's capacity is finite and the endpoint list
 * can be long — several URLs, some of them IPv6 literals.
 */
@Serializable
data class QrPayload(
    val v: Int = 1,
    val c: String,
    val e: List<String> = emptyList(),
    val n: String? = null,
)

@Serializable
data class ClaimRequest(val code: String, val device_name: String? = null)

@Serializable
data class ClaimResponse(
    val token: String,
    val username: String,
    val expires_at: String,
    val server_name: String,
)

// ── Metrics ────────────────────────────────────────────────────────────────

@Serializable
data class CpuTemp(
    val sensor: String = "",
    val label: String = "",
    val temp_c: Double = 0.0,
    val high_c: Double? = null,
    val critical_c: Double? = null,
)

@Serializable
data class CpuMetrics(
    val aggregate: Double = 0.0,
    val per_core: List<Double> = emptyList(),
    val load_avg: List<Double> = emptyList(),
    val frequency_mhz: Double = 0.0,
    val cpu_name: String = "",
    val temps: List<CpuTemp> = emptyList(),
)

@Serializable
data class MemoryMetrics(
    val total_mb: Double = 0.0,
    val used_mb: Double = 0.0,
    val free_mb: Double = 0.0,
    val percent: Double = 0.0,
    val swap_total_mb: Double = 0.0,
    val swap_used_mb: Double = 0.0,
)

@Serializable
data class GpuDevice(
    val index: Int = 0,
    val name: String = "",
    val utilization_percent: Double = 0.0,
    val memory_used_mb: Double = 0.0,
    val memory_total_mb: Double = 0.0,
    val temperature_c: Double = 0.0,
    val power_draw_w: Double = 0.0,
)

@Serializable
data class GpuMetrics(val available: Boolean = false, val devices: List<GpuDevice> = emptyList())

@Serializable
data class DiskMetrics(
    val device: String = "",
    val mountpoint: String = "",
    val usage_percent: Double = 0.0,
    val used_gb: Double = 0.0,
    val total_gb: Double = 0.0,
    val read_mb_s: Double = 0.0,
    val write_mb_s: Double = 0.0,
)

/** `interface` is a Kotlin keyword, hence the rename. */
@Serializable
data class NetIface(
    @SerialName("interface") val iface: String = "",
    val rx_mb_s: Double = 0.0,
    val tx_mb_s: Double = 0.0,
    val rx_total_mb: Double = 0.0,
    val tx_total_mb: Double = 0.0,
)

@Serializable
data class ProcessMetrics(
    val pid: Int = 0,
    val name: String = "",
    val cpu_percent: Double = 0.0,
    val memory_mb: Double = 0.0,
    val status: String = "",
    val user: String = "",
)

@Serializable
data class SystemMetrics(
    val hostname: String = "",
    val uptime_seconds: Double = 0.0,
    val boot_time_ts: Double = 0.0,
    /** Server's zone abbreviation, e.g. "CST". Empty on older servers. */
    val timezone: String = "",
    /** Server's UTC offset. Epoch ts alone can't convey this. */
    val utc_offset_seconds: Int = 0,
)

@Serializable
data class MetricsSnapshot(
    val ts: Double = 0.0,
    val cpu: CpuMetrics? = null,
    val memory: MemoryMetrics? = null,
    val gpu: GpuMetrics? = null,
    val disks: List<DiskMetrics> = emptyList(),
    val network: List<NetIface> = emptyList(),
    val processes: List<ProcessMetrics> = emptyList(),
    val system: SystemMetrics? = null,
)

@Serializable
data class HistoryPoint(
    val ts: Double = 0.0,
    val cpu: Double = 0.0,
    val mem: Double = 0.0,
    val gpu: Double? = null,
)

// ── Docker ─────────────────────────────────────────────────────────────────

@Serializable
data class ContainerInfo(
    val id: String = "",
    val name: String = "",
    val image: String = "",
    val status: String = "",
    val state: String = "",
    val ports: String = "",
    val created: String = "",
    val cpu_percent: Double = 0.0,
    val mem_usage_mb: Double = 0.0,
    val mem_limit_mb: Double = 0.0,
    val mem_percent: Double = 0.0,
) {
    val isRunning: Boolean get() = state.equals("running", ignoreCase = true)
}

@Serializable
data class ActionResponse(val success: Boolean = false, val output: String = "")

// ── System services ────────────────────────────────────────────────────────

@Serializable
data class SystemServiceInfo(
    val service_name: String = "",
    val description: String? = null,
    val load_state: String = "",
    val active_state: String = "",
    val sub_state: String = "",
    val uptime: String? = null,
    val pid: Int? = null,
    val unit_file_state: String = "",
    val autostart_enabled: Boolean = false,
    val starred: Boolean = false,
) {
    val isActive: Boolean get() = active_state.equals("active", ignoreCase = true)
}

@Serializable data class ServiceActionRequest(val action: String)
@Serializable data class ServiceAutostartRequest(val enabled: Boolean)
@Serializable data class ServiceStarRequest(val starred: Boolean)

// ── Sites ──────────────────────────────────────────────────────────────────

@Serializable
data class SiteStatus(
    val status: String = "",
    val uptime: String? = null,
    val pid: Int? = null,
)

@Serializable
data class SiteResponse(
    val id: String = "",
    val name: String = "",
    val type: String = "",
    val service_name: String = "",
    val service_manager: String = "",
    val config_file_path: String? = null,
    val log_paths: List<String> = emptyList(),
    val description: String? = null,
    val created_at: String = "",
    val updated_at: String = "",
    val status: SiteStatus? = null,
) {
    val isRunning: Boolean get() = status?.status.equals("running", ignoreCase = true)
}

@Serializable data class SiteActionRequest(val action: String)
@Serializable data class SiteActionResponse(val success: Boolean = false, val output: String = "")
@Serializable data class ConfigReadResponse(val content: String = "", val path: String = "")
@Serializable data class ConfigWriteRequest(val content: String)

@Serializable data class TrafficBucket(val minute: String = "", val count: Int = 0)
@Serializable data class TrafficTopEntry(val value: String = "", val count: Int = 0)

@Serializable
data class SiteTrafficResponse(
    val site_id: String = "",
    val window_minutes: Int = 0,
    val total_requests: Int = 0,
    val total_bytes: Long = 0,
    val status_2xx: Int = 0,
    val status_3xx: Int = 0,
    val status_4xx: Int = 0,
    val status_5xx: Int = 0,
    val requests_per_minute: List<TrafficBucket> = emptyList(),
    val top_paths: List<TrafficTopEntry> = emptyList(),
    val top_ips: List<TrafficTopEntry> = emptyList(),
)

// ── Disks ──────────────────────────────────────────────────────────────────

@Serializable
data class SmartResult(
    val model: String = "",
    val serial: String = "",
    val firmware: String = "",
    val health: String = "",
    val temperature_c: Int? = null,
    val power_on_hours: Int? = null,
    val reallocated_sectors: Int? = null,
    val pending_sectors: Int? = null,
    val uncorrectable_errors: Int? = null,
    val last_checked: String = "",
    val error: String? = null,
) {
    val isHealthy: Boolean get() = health.equals("PASSED", ignoreCase = true) ||
        health.equals("OK", ignoreCase = true)
}

@Serializable
data class DiskInfo(
    val device: String = "",
    val mountpoint: String = "",
    val extra_mounts: List<String> = emptyList(),
    val physical_device: String = "",
    val fstype: String = "",
    val opts: String = "",
    val total_gb: Double = 0.0,
    val used_gb: Double = 0.0,
    val free_gb: Double = 0.0,
    val usage_percent: Double = 0.0,
    val read_mb_s: Double = 0.0,
    val write_mb_s: Double = 0.0,
    val is_removable: Boolean = false,
    val is_virtual: Boolean = false,
    val can_unmount: Boolean = false,
    val bus_type: String = "",
    val smart: SmartResult? = null,
)

@Serializable data class UnmountRequest(val mountpoint: String)

// ── Cron ───────────────────────────────────────────────────────────────────

@Serializable
data class CronEntry(
    val source: String = "",
    val user: String = "",
    val schedule: String = "",
    val command: String = "",
    val raw: String = "",
)

@Serializable
data class CronJob(
    val id: String = "",
    val label: String = "",
    val schedule: String = "",
    val command: String = "",
)

@Serializable
data class CronJobIn(val label: String = "", val schedule: String, val command: String)

// ── Apps / ports ───────────────────────────────────────────────────────────

@Serializable
data class AppInfo(
    val port: Int = 0,
    val protocol: String = "",
    val pid: Int? = null,
    val process_name: String = "",
    val user: String = "",
    val cmdline: String = "",
    val auto_label: String = "",
    val custom_label: String? = null,
) {
    val label: String get() = custom_label?.takeIf { it.isNotBlank() } ?: auto_label
}

@Serializable data class LabelRequest(val label: String)
@Serializable data class KillRequest(val force: Boolean = false)
@Serializable data class KillResponse(val success: Boolean = false, val message: String = "")

// ── Sessions ───────────────────────────────────────────────────────────────

@Serializable
data class SessionInfo(
    val user: String = "",
    val tty: String = "",
    val from_host: String = "",
    val login_time: String = "",
    val idle: String = "",
    val cpu_time: String = "",
    val command: String = "",
)

// ── Bookmarks ──────────────────────────────────────────────────────────────

@Serializable
data class BookmarkOut(
    val id: String = "",
    val title: String = "",
    val url: String = "",
    val icon_url: String? = null,
    val sort_order: Int = 0,
)

@Serializable
data class BookmarkIn(
    val title: String,
    val url: String,
    val icon_url: String? = null,
    val sort_order: Int = 0,
)

// ── Webhooks ───────────────────────────────────────────────────────────────

@Serializable
data class WebhookResponse(
    val id: String = "",
    val label: String = "",
    val url: String = "",
    val enabled: Boolean = false,
    val events: List<String> = emptyList(),
)

@Serializable
data class WebhookCreate(
    val label: String = "",
    val url: String,
    val enabled: Boolean = true,
    val events: List<String> = emptyList(),
)

@Serializable
data class WebhookUpdate(
    val label: String? = null,
    val url: String? = null,
    val enabled: Boolean? = null,
    val events: List<String>? = null,
)

@Serializable
data class TriggerRequest(
    val event: String,
    val metric: String,
    val value: Double,
    val threshold: Double,
)

// ── Devices / account / settings ───────────────────────────────────────────

@Serializable
data class DeviceOut(
    val id: String = "",
    val name: String = "",
    val kind: String = "browser",
    val ip_address: String? = null,
    val last_seen: String = "",
    val created_at: String = "",
    val expires_at: String? = null,
)

@Serializable
data class UserInfo(
    val id: String = "",
    val username: String = "",
    val totp_enabled: Boolean = false,
    val onboarding_completed: Boolean = false,
)

@Serializable
data class ProxyConfig(
    val enabled: Boolean = false,
    val type: String = "http",
    val host: String = "127.0.0.1",
    val port: Int = 7890,
)

@Serializable
data class ChangeProfileRequest(
    val current_password: String,
    val new_username: String? = null,
    val new_password: String? = null,
)

@Serializable data class SuccessResponse(val success: Boolean = false)

@Serializable
data class TotpSetupResponse(
    val secret: String = "",
    val otpauth_uri: String = "",
    val qr_png_b64: String = "",
)

@Serializable data class TotpConfirmRequest(val totp_code: String)

// ── System / updates ───────────────────────────────────────────────────────

@Serializable
data class VersionStatus(
    val configured: Boolean = false,
    val repo_url: String? = null,
    val current_version: String? = null,
    val current_commit: String? = null,
    val current_source_type: String? = null,
    val installed_at: String? = null,
    val latest_version: String? = null,
    val latest_commit: String? = null,
    val checked_at: String? = null,
    val update_available: Boolean = false,
    val update_in_progress: Boolean = false,
    val check_in_progress: Boolean = false,
    val status: String? = null,
    val error: String? = null,
    val release_url: String? = null,
    val notes_url: String? = null,
)

@Serializable data class ServiceLogs(val lines: List<String> = emptyList())

/** Free-form JSON blobs the panel round-trips without interpreting. */
@Serializable data class PrefsPayload(val prefs: Map<String, kotlinx.serialization.json.JsonElement> = emptyMap())

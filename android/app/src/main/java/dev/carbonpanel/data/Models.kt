package dev.carbonpanel.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ── Pairing ────────────────────────────────────────────────────────────────

/**
 * Payload encoded in the QR code shown by the web panel.
 *
 * Field names are single letters because a QR's capacity is finite and the
 * endpoint list can be long — several URLs, some of them IPv6 literals.
 */
@Serializable
data class QrPayload(
    val v: Int = 1,
    val c: String,                       // pairing code
    val e: List<String> = emptyList(),   // candidate endpoint URLs, best first
    val n: String? = null,               // server name
)

@Serializable
data class ClaimRequest(
    val code: String,
    val device_name: String? = null,
)

@Serializable
data class ClaimResponse(
    val token: String,
    val username: String,
    val expires_at: String,
    val server_name: String,
)

// ── Metrics ────────────────────────────────────────────────────────────────

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
data class CpuTemp(
    val sensor: String = "",
    val label: String = "",
    val temp_c: Double = 0.0,
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
data class GpuMetrics(
    val available: Boolean = false,
    val devices: List<GpuDevice> = emptyList(),
)

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

/** Network interface entry. `interface` is a Kotlin keyword, hence the rename. */
@Serializable
data class NetIface(
    @SerialName("interface") val iface: String = "",
    val rx_mb_s: Double = 0.0,
    val tx_mb_s: Double = 0.0,
    val rx_total_mb: Double = 0.0,
    val tx_total_mb: Double = 0.0,
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
data class ActionResponse(
    val success: Boolean = false,
    val output: String = "",
)

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

@Serializable
data class SiteActionResponse(
    val success: Boolean = false,
    val output: String = "",
)

/** Body for POST /sites/system-services/{name}/action — "start"|"stop"|"restart". */
@Serializable
data class ServiceActionRequest(val action: String)

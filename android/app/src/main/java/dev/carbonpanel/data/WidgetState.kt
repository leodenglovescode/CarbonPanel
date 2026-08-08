package dev.carbonpanel.data

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * Units the widget can show network throughput in.
 *
 * The server reports MB/s. Bits and bytes differ by 8x, so picking the wrong
 * one misreports the link by nearly an order of magnitude — worth being
 * explicit about rather than guessing. Link speeds are quoted in bits
 * (a "1 Gbps" NIC), file transfers in bytes, so both are legitimate defaults
 * depending on what you're watching.
 */
@Serializable
enum class NetUnit(val label: String, private val fromMbPerSec: Double, val suffix: String) {
    Mbps("mbps", 8.0, "mbps"),
    MBps("MB/s", 1.0, "MB/s"),
    Gbps("gbps", 8.0 / 1024.0, "gbps"),
    GBps("GB/s", 1.0 / 1024.0, "GB/s");

    fun format(mbPerSec: Double): String {
        val v = mbPerSec * fromMbPerSec
        val digits = when {
            this == Gbps || this == GBps -> 2
            v >= 100 -> 0
            v >= 10 -> 1
            else -> 1
        }
        return "%.${digits}f $suffix".format(v)
    }

    companion object {
        fun from(name: String?): NetUnit = entries.firstOrNull { it.name == name } ?: Mbps
    }
}

/**
 * Snapshot the widget renders from.
 *
 * Cached rather than fetched at render time: provideGlance runs on a tight
 * budget and can be called when the network is unavailable, so the widget draws
 * from the last successful poll and shows its age instead of blanking.
 */
@Serializable
data class WidgetState(
    val serverName: String = "",
    val cpuPercent: Double = 0.0,
    val memPercent: Double = 0.0,
    val memUsedMb: Double = 0.0,
    val memTotalMb: Double = 0.0,
    val gpuPresent: Boolean = false,
    val gpuPercent: Double = 0.0,
    val gpuMemUsedMb: Double = 0.0,
    val gpuMemTotalMb: Double = 0.0,
    val diskMount: String = "",
    val diskPercent: Double = 0.0,
    val diskUsedGb: Double = 0.0,
    val diskTotalGb: Double = 0.0,
    val netIface: String = "",
    val netRxMbPerSec: Double = 0.0,
    val netTxMbPerSec: Double = 0.0,
    val updatedAt: Long = 0L,
    val stale: Boolean = false,
) {
    companion object {
        private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

        fun encode(state: WidgetState): String =
            json.encodeToString(serializer(), state)

        fun decode(raw: String?): WidgetState? =
            raw?.let { runCatching { json.decodeFromString<WidgetState>(it) }.getOrNull() }
    }
}

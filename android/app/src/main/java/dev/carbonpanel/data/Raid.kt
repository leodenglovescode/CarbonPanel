package dev.carbonpanel.data

import kotlinx.serialization.Serializable

/** Only the read-only RAID portion of /disks/nas is consumed by Android. */
@Serializable
data class NasInventory(val raid: RaidInventory = RaidInventory())

@Serializable
data class RaidInventory(
    val available: Boolean = true,
    val arrays: List<RaidArray> = emptyList(),
    val errors: List<String> = emptyList(),
)

enum class RaidHealth { Healthy, Degraded, Inactive, Unknown }

@Serializable
data class RaidArray(
    val device: String,
    val level: String? = null,
    val state: String? = null,
    val size_bytes: Long? = null,
    val raid_disks: Int? = null,
    val degraded: Int? = null,
    val sync_action: String? = null,
    val sync_percent: Double? = null,
    val members: List<RaidMember> = emptyList(),
) {
    val health: RaidHealth get() = when {
        (degraded ?: 0) > 0 || members.any { it.isFaulty } -> RaidHealth.Degraded
        state in listOf("inactive", "clear", "suspended", "broken") -> RaidHealth.Inactive
        degraded == null || state !in listOf("clean", "active", "active-idle", "readonly", "read-auto", "write-pending") -> RaidHealth.Unknown
        else -> RaidHealth.Healthy
    }
    val isSyncing: Boolean get() = sync_action in listOf("resync", "recover", "recovery", "reshape", "check", "repair")
}

@Serializable
data class RaidMember(
    val device: String,
    val state: String? = null,
    val slot: String? = null,
) {
    val isFaulty: Boolean get() = state.orEmpty().split(',').any {
        it.trim() in listOf("faulty", "blocked", "write_error")
    }
}

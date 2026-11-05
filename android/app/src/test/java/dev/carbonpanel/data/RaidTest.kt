package dev.carbonpanel.data

import kotlinx.serialization.json.Json
import org.junit.Assert.*
import org.junit.Test

class RaidTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test fun nasPayloadParsesNullsLargeCapacitiesAndStringMemberSlots() {
        val inventory = json.decodeFromString<NasInventory>("""{
          "raid": {"available":true,"arrays":[{
            "device":"/dev/md0","level":"raid5","state":"active","size_bytes":12000000000000,
            "raid_disks":4,"degraded":1,"sync_action":"recover","sync_percent":32.5,
            "members":[{"device":"/dev/sda1","state":"in_sync","slot":"0"},
              {"device":"/dev/sdb1","state":null,"slot":null}]}],"errors":[]},
          "lvm":{"volume_groups":[]},"fans":{"chips":[]}
        }""")
        val array = inventory.raid.arrays.single()
        assertEquals(12000000000000L, array.size_bytes)
        assertEquals(RaidHealth.Degraded, array.health)
        assertTrue(array.isSyncing)
        assertEquals(32.5, array.sync_percent!!, 0.01)
        assertEquals("0", array.members[0].slot)
        assertNull(array.members[1].slot)
    }

    @Test fun missingHealthFieldsCannotProduceHealthyStatus() {
        val array = json.decodeFromString<RaidArray>("""{"device":"/dev/md0"}""")
        assertEquals(RaidHealth.Unknown, array.health)
        assertNull(array.sync_percent)
        assertFalse(array.isSyncing)
    }

    @Test fun cleanCompleteArrayIsHealthy() {
        assertEquals(RaidHealth.Healthy, RaidArray("/dev/md0", state = "clean", degraded = 0).health)
    }

    @Test fun faultyMemberOverridesZeroDegradedCount() {
        val array = RaidArray("/dev/md0", state = "active", degraded = 0,
            members = listOf(RaidMember("/dev/sda1", "faulty,blocked", "0")))
        assertEquals(RaidHealth.Degraded, array.health)
    }

    @Test fun inactiveArrayIsNotHealthyEvenWithAllSlotsPresent() {
        assertEquals(RaidHealth.Inactive, RaidArray("/dev/md0", state = "inactive", degraded = 0).health)
    }

    @Test fun pausedAndIdleSyncAreNotPresentedAsActiveRebuilds() {
        assertFalse(RaidArray("/dev/md0", sync_action = "idle").isSyncing)
        assertFalse(RaidArray("/dev/md0", sync_action = "frozen").isSyncing)
        assertTrue(RaidArray("/dev/md0", sync_action = "reshape").isSyncing)
    }
}

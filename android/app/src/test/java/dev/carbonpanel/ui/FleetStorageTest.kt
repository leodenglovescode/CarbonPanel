package dev.carbonpanel.ui

import dev.carbonpanel.data.DiskInfo
import org.junit.Assert.*
import org.junit.Test

class FleetStorageTest {
    @Test fun weightedUsageExcludesPseudoMountsAndDuplicateDevices() {
        val system = DiskInfo(device = "/dev/sda1", mountpoint = "/", total_gb = 100.0, used_gb = 50.0)
        val data = DiskInfo(device = "/dev/sdb1", mountpoint = "/data", total_gb = 900.0, used_gb = 90.0)
        val snap = DiskInfo(device = "/dev/loop0", mountpoint = "/snap/core/1", total_gb = 100.0, used_gb = 100.0)
        val overlay = DiskInfo(device = "overlay", mountpoint = "/container", is_virtual = true,
            total_gb = 500.0, used_gb = 500.0)
        assertEquals(14.0, fleetStorageUsage(listOf(system, data, data.copy(mountpoint = "/backup"), snap, overlay))!!, .001)
    }

    @Test fun missingCapacityIsUnknownRatherThanZeroUsage() {
        assertNull(fleetStorageUsage(emptyList()))
        assertNull(fleetStorageUsage(listOf(DiskInfo(total_gb = 0.0))))
        assertNull(fleetStorageUsage(listOf(DiskInfo(total_gb = Double.NaN))))
    }
}

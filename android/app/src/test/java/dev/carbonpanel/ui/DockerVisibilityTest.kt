package dev.carbonpanel.ui

import dev.carbonpanel.data.SystemMetrics
import kotlinx.serialization.json.Json
import org.junit.Assert.*
import org.junit.Test

class DockerVisibilityTest {
    @Test fun missingDockerHidesOnlyItsDestination() {
        assertFalse(Dest.primaries(false).contains(Dest.Docker))
        assertTrue(Dest.primaries(false).containsAll(listOf(Dest.Dashboard, Dest.Services, Dest.Disks, Dest.More)))
    }

    @Test fun installedDockerIsVisibleRegardlessOfContainerCountOrDaemonState() {
        assertTrue(Dest.primaries(true).contains(Dest.Docker))
    }

    @Test fun olderServersDoNotLoseTheirDockerEntry() {
        val system = Json.decodeFromString<SystemMetrics>("""{"hostname":"old-server"}""")
        assertNull(system.docker_installed)
        assertTrue(Dest.primaries(system.docker_installed).contains(Dest.Docker))
    }

    @Test fun switchingBackToADockerServerRestoresTheDestination() {
        val without = Json.decodeFromString<SystemMetrics>("""{"docker_installed":false}""")
        val with = Json.decodeFromString<SystemMetrics>("""{"docker_installed":true}""")
        assertFalse(Dest.primaries(without.docker_installed).contains(Dest.Docker))
        assertTrue(Dest.primaries(with.docker_installed).contains(Dest.Docker))
    }
}

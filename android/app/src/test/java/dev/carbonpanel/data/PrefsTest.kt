package dev.carbonpanel.data

import android.content.SharedPreferences
import org.junit.Assert.*
import org.junit.Test
import java.lang.reflect.Proxy

class PrefsTest {
    @Test fun legacyPairingMigratesOnceIncludingPinsAndWidgetChoices() {
        val storage = memoryPrefs(mapOf(
            "token" to "secret", "endpoints" to "https://192.168.1.1",
            "server_name" to "Original", "pin:192.168.1.1" to "PIN",
            "widget_disk" to "/data", "theme_mode" to "Dark", "device_id" to "phone",
        ))
        Prefs.migrateLegacyPrefs(storage)
        val server = Prefs(storage, "legacy")
        assertTrue(server.isPaired)
        assertEquals("secret", server.token)
        assertEquals("PIN", server.pinnedCert("192.168.1.1"))
        assertEquals("/data", server.widgetDisk)
        assertEquals("Dark", server.themeMode)
        assertEquals("phone", server.deviceId)
        assertEquals("legacy", server.activeServerId)
        assertFalse(storage.contains("token"))
        Prefs.migrateLegacyPrefs(storage)
        assertEquals(1, server.servers.size)
    }

    @Test fun serversKeepIndependentCredentialsPinsEndpointsAndWidgetState() {
        val first = Prefs(memoryPrefs(), "one")
        first.token = "token-1"
        first.endpoints = listOf("https://host:8443")
        first.setPinnedCert("host", "PIN-1")
        first.widgetDisk = "/one"
        first.widgetState = "one snapshot"
        first.saveServer()
        val second = first.forServer("two")
        second.token = "token-2"
        second.endpoints = listOf("https://host:9443")
        second.setPinnedCert("host", "PIN-2")
        second.widgetDisk = "/two"
        second.saveServer()
        assertEquals(2, second.servers.size)
        first.activate("one")
        assertEquals("one", second.activeServerId)
        assertEquals("token-1", first.token)
        assertEquals("token-2", second.token)
        assertEquals("PIN-1", first.pinnedCert("HOST"))
        assertEquals("PIN-2", second.pinnedCert("host"))
        assertEquals("/one", first.widgetDisk)
        assertEquals("/two", second.widgetDisk)
        assertNull(second.widgetState)
        assertEquals(listOf("https://host:8443"), first.endpoints)
    }

    @Test fun removingActiveServerKeepsOthersAndAppearance() {
        val first = Prefs(memoryPrefs(), "one")
        first.token = "one"
        first.themeMode = "Dark"
        first.saveServer()
        val second = first.forServer("two")
        second.token = "two"
        second.saveServer()
        second.clear()
        assertEquals("one", first.activeServerId)
        assertEquals("one", first.token)
        assertNull(second.token)
        assertEquals("Dark", second.themeMode)
        assertEquals(listOf("one"), first.servers.map { it.id })
        first.clear()
        assertNull(first.activeServerId)
        assertTrue(first.servers.isEmpty())
        assertEquals("Dark", first.themeMode)
    }

    @Test fun failedPairingDraftDoesNotReplaceSavedServer() {
        val server = Prefs(memoryPrefs(), "one")
        server.token = "keep"
        server.saveServer()
        val draft = server.newServer()
        draft.setPinnedCert("host", "TEMP")
        draft.clear()
        assertEquals("one", server.activeServerId)
        assertEquals("keep", server.token)
        assertEquals(1, server.servers.size)
        assertNull(draft.pinnedCert("host"))
    }

    /** A real map-backed store so these tests exercise production migration/key logic. */
    private fun memoryPrefs(initial: Map<String, Any> = emptyMap()): SharedPreferences {
        val values = initial.toMutableMap()
        val pending = mutableMapOf<String, Any?>()
        lateinit var editor: SharedPreferences.Editor
        editor = Proxy.newProxyInstance(javaClass.classLoader,
            arrayOf(SharedPreferences.Editor::class.java)) { _, method, args ->
            when (method.name) {
                "putString", "putFloat", "putInt", "putBoolean" -> {
                    pending[args!![0] as String] = args[1]; editor
                }
                "remove" -> { pending[args!![0] as String] = null; editor }
                "apply", "commit" -> {
                    pending.forEach { (key, value) ->
                        if (value == null) values.remove(key) else values[key] = value
                    }
                    pending.clear()
                    if (method.name == "commit") true else null
                }
                else -> error("Unexpected editor call: ${method.name}")
            }
        } as SharedPreferences.Editor
        return Proxy.newProxyInstance(javaClass.classLoader,
            arrayOf(SharedPreferences::class.java)) { _, method, args ->
            when (method.name) {
                "getAll" -> values.toMap()
                "contains" -> values.containsKey(args!![0])
                "getString", "getFloat", "getInt", "getBoolean" -> values[args!![0]] ?: args[1]
                "edit" -> editor
                else -> error("Unexpected prefs call: ${method.name}")
            }
        } as SharedPreferences
    }
}

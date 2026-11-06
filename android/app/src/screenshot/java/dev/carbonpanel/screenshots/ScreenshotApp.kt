package dev.carbonpanel.screenshots

import android.app.Application
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.net.PinnedTrustManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import okhttp3.tls.HandshakeCertificates
import okhttp3.tls.HeldCertificate
import java.net.InetAddress

/**
 * Store-artwork fixtures. Only compiled into the .screenshots application ID.
 * Requests stay on loopback HTTPS; no real server account is used or modified.
 * All mutation endpoints are disabled, while the ordinary app UI is unchanged.
 */
class ScreenshotApp : Application() {
    private val servers = mutableListOf<MockWebServer>()

    override fun onCreate() {
        super.onCreate()
        runBlocking(Dispatchers.IO) {
            val certificate = HeldCertificate.Builder()
                .commonName("CarbonPanel screenshot fixture")
                .addSubjectAlternativeName("localhost")
                .build()
            val tls = HandshakeCertificates.Builder().heldCertificate(certificate).build()
            val pin = PinnedTrustManager.sha256(certificate.certificate)
            val prefs = Prefs.get(this@ScreenshotApp)
            prefs.servers.forEach { prefs.removeServer(it.id) }
            prefs.themeMode = "Dark"
            prefs.accent = "Carbon"
            prefs.backdropEnabled = false
            listOf("Atlas", "Harbor", "Forge").forEachIndexed { index, name ->
                val server = MockWebServer().apply {
                    useHttps(tls.sslSocketFactory(), false)
                    dispatcher = fixtures(index)
                    start(InetAddress.getByName("127.0.0.1"), 8443 + index)
                }
                servers += server
                prefs.forServer("demo-$index").apply {
                    serverName = name
                    username = "demo"
                    token = "screenshot-fixture-not-a-real-session"
                    endpoints = listOf("https://localhost:${server.port}")
                    setPinnedCert("localhost", pin)
                    saveServer()
                }
            }
            prefs.activate("demo-0")
        }
    }

    private fun fixtures(index: Int) = object : Dispatcher() {
        override fun dispatch(request: RecordedRequest): MockResponse {
            if (request.method !in setOf("GET", "HEAD")) {
                return MockResponse().setResponseCode(409)
                    .setBody("{\"detail\":\"Read-only screenshot fixture: actions are disabled\"}")
            }
            val path = request.requestUrl?.encodedPath.orEmpty()
            val filename = when (path) {
                "/api/v1/metrics/current" -> "metrics-$index.json"
                "/api/v1/metrics/history" -> "history.json"
                "/api/v1/disks" -> "disks.json"
                "/api/v1/disks/nas" -> "nas.json"
                "/api/v1/docker/containers" -> "containers.json"
                "/api/v1/sites/system-services" -> "services.json"
                "/api/v1/files" -> "files.json"
                "/api/v1/settings/background-image/config" -> "backgrounds.json"
                "/api/v1/preferences" -> "preferences.json"
                "/api/v1/auth/me" -> "user.json"
                "/api/v1/files/preview" -> "preview.html"
                else -> null
            }
            if (filename == null) return MockResponse().setResponseCode(404)
                .setBody("{\"detail\":\"Not part of the screenshot fixture\"}")
            val content = assets.open("demo/$filename").bufferedReader().use { it.readText() }
            return MockResponse().setHeader("Content-Type",
                if (filename.endsWith(".html")) "text/html; charset=utf-8" else "application/json")
                .setBody(content)
        }
    }
}

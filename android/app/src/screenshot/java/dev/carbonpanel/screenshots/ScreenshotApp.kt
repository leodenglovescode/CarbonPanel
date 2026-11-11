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
            if (path == "/api/v1/files") return fileListing(request)
            if (path == "/api/v1/files/content") return MockResponse()
                .setHeader("Content-Type", "text/plain")
                .setHeader("Content-Disposition", "attachment; filename=demo.txt")
                .setBody("CarbonPanel demo file.\n".repeat(30000))
                .throttleBody(32 * 1024, 1000, java.util.concurrent.TimeUnit.MILLISECONDS)
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

    private fun fileListing(request: RecordedRequest): MockResponse {
        val url = request.requestUrl!!
        val path = url.queryParameter("path") ?: "/"
        val source = org.json.JSONObject(assets.open("demo/files.json").bufferedReader().use { it.readText() })
        val original = source.getJSONArray("entries")
        var files = (0 until original.length()).map { original.getJSONObject(it) }
        if (path != "/") {
            files = files.filter { !it.getBoolean("directory") }.filter {
                when (path) {
                    "/Documents" -> it.optString("kind") in listOf("markdown", "text")
                    "/Media" -> it.optString("kind") in listOf("image", "video", "audio")
                    "/Projects" -> it.optString("name").endsWith(".py")
                    else -> false
                }
            }.map { org.json.JSONObject(it.toString()).put("path", "$path/${it.getString("name")}") }
        }
        val search = url.queryParameter("search").orEmpty()
        files = files.filter { it.getString("name").contains(search, ignoreCase = true) &&
            (url.queryParameter("show_hidden") != "false" || !it.getString("name").startsWith(".")) }
        files = when (url.queryParameter("sort")) {
            "size" -> files.sortedByDescending { it.optLong("size", 0) }
            "modified" -> files.sortedByDescending { it.optDouble("modified", 0.0) }
            "kind" -> files.sortedBy { it.optString("kind") }
            else -> files.sortedBy { it.getString("name").lowercase() }
        }.sortedBy { !it.getBoolean("directory") }
        val offset = url.queryParameter("offset")?.toIntOrNull()?.coerceAtLeast(0) ?: 0
        source.put("path", path).put("parent", if (path == "/") org.json.JSONObject.NULL else "/")
            .put("entries", org.json.JSONArray(files.drop(offset).take(200)))
            .put("total", files.size).put("offset", offset).put("has_more", offset + 200 < files.size)
        return MockResponse().setHeader("Content-Type", "application/json").setBody(source.toString())
    }
}

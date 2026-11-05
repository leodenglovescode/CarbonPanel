package dev.carbonpanel.ui.screens

import android.annotation.SuppressLint
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import dev.carbonpanel.data.FileEntry
import dev.carbonpanel.data.FileListing
import dev.carbonpanel.net.ApiClient
import dev.carbonpanel.repo.PanelRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Request
import java.io.ByteArrayInputStream

/** A read-only view of files accessible to the CarbonPanel service account. */
@Composable
fun FilesScreen() {
    val context = LocalContext.current
    val repo = remember { PanelRepository(context.applicationContext) }
    val scope = rememberCoroutineScope()
    var directory by rememberSaveable { mutableStateOf("/") }
    var pathInput by rememberSaveable { mutableStateOf("/") }
    var offset by rememberSaveable { mutableIntStateOf(0) }
    var refresh by remember { mutableIntStateOf(0) }
    var listing by remember { mutableStateOf<FileListing?>(null) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var selected by remember { mutableStateOf<FileEntry?>(null) }
    var download by remember { mutableStateOf<FileEntry?>(null) }
    var downloading by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf<String?>(null) }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri ->
        val file = download
        download = null
        if (uri != null && file != null) scope.launch {
            downloading = true
            try {
                withContext(Dispatchers.IO) {
                    val url = fileUrl(context, file.path, true)
                    ApiClient.imageClient(context).newCall(Request.Builder().url(url).build()).execute().use { response ->
                        check(response.isSuccessful) { "Download failed (HTTP ${response.code})" }
                        val body = response.body ?: error("Empty download response")
                        context.contentResolver.openOutputStream(uri, "w")?.use { output ->
                            body.byteStream().use { it.copyTo(output) }
                        } ?: error("Cannot write to the selected destination")
                    }
                }
                notice = "Downloaded ${file.name}"
            } catch (e: kotlinx.coroutines.CancellationException) { throw e }
            catch (e: Exception) { notice = e.message ?: "Download failed" }
            finally { downloading = false }
        }
    }
    fun open(path: String, pageOffset: Int = 0) { directory = path; offset = pageOffset; refresh++ }
    LaunchedEffect(directory, offset, refresh) {
        busy = true; error = null
        repo.files(directory, offset).onSuccess { listing = it; pathInput = it.path }.onFailure { error = it.message }
        busy = false
    }
    Column(Modifier.fillMaxSize().padding(horizontal = 14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Files · read only", style = MaterialTheme.typography.titleMedium)
        Text("Access follows the CarbonPanel service account. Preview and download only.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        OutlinedTextField(pathInput, { pathInput = it }, enabled = !busy, label = { Text("Directory path") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { listing?.parent?.let { open(it) } }, enabled = !busy && listing?.parent != null) { Text("Up") }
            Button(onClick = { open(pathInput) }, enabled = !busy) { Text("Open") }
            TextButton(onClick = { refresh++ }, enabled = !busy) { Text("Refresh") }
        }
        if (busy || downloading) LinearProgressIndicator(Modifier.fillMaxWidth())
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        notice?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
        listing?.let { data ->
            Text("${data.total} items · ${data.path}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            LazyColumn(Modifier.weight(1f)) {
                items(data.entries, key = { it.path }) { file ->
                    Row(Modifier.fillMaxWidth().clickable { if (file.directory) open(file.path) else selected = file }.padding(vertical = 12.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(if (file.directory) "DIR" else file.kind.uppercase().take(4), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary, modifier = Modifier.width(38.dp))
                        Column(Modifier.weight(1f)) {
                            Text(file.name, style = MaterialTheme.typography.bodyMedium)
                            Text(if (file.directory) "Directory" else fileSize(file.size), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        if (!file.directory) TextButton(onClick = { download = file; save.launch(file.name) }, enabled = !downloading) { Text("Save") }
                        else Text("›")
                    }
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                }
                if (data.entries.isEmpty() && !busy) item { Text("This directory is empty.", modifier = Modifier.padding(vertical = 24.dp)) }
            }
            if (data.offset > 0 || data.has_more) Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                TextButton(onClick = { open(data.path, (data.offset - 200).coerceAtLeast(0)) }, enabled = !busy && data.offset > 0) { Text("Previous") }
                Text("Page ${data.offset / 200 + 1}", style = MaterialTheme.typography.labelSmall)
                TextButton(onClick = { open(data.path, data.offset + 200) }, enabled = !busy && data.has_more) { Text("Next") }
            }
        }
    }
    selected?.let { file ->
        FilePreview(file, repo, onClose = { selected = null }, onDownload = { download = file; save.launch(file.name) }, downloading = downloading)
    }
}

private fun fileSize(size: Long?): String {
    if (size == null) return "—"
    var value = size.toDouble()
    var index = 0
    val units = listOf("B", "KiB", "MiB", "GiB", "TiB")
    while (value >= 1024 && index < units.lastIndex) { value /= 1024; index++ }
    return "%.1f %s".format(value, units[index])
}

private fun fileUrl(context: android.content.Context, path: String, download: Boolean = false): String {
    val base = ApiClient.activeBaseUrl ?: dev.carbonpanel.data.Prefs.get(context).lastGoodEndpoint ?: error("Server unreachable")
    return (base.trimEnd('/') + "/api/v1/files/content").toHttpUrl().newBuilder()
        .addQueryParameter("path", path).addQueryParameter("download", download.toString()).build().toString()
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
private fun FilePreview(file: FileEntry, repo: PanelRepository, onClose: () -> Unit, onDownload: () -> Unit, downloading: Boolean) {
    val context = LocalContext.current
    var html by remember(file.path) { mutableStateOf<String?>(null) }
    var error by remember(file.path) { mutableStateOf<String?>(null) }
    val media = file.kind in listOf("image", "video", "audio")
    LaunchedEffect(file.path) {
        if (media) {
            val tag = when (file.kind) {
                "image" -> "<img src='https://preview.carbonpanel.invalid/media' alt='Image preview'>"
                "audio" -> "<audio controls preload='metadata' src='https://preview.carbonpanel.invalid/media'></audio>"
                else -> "<video controls playsinline preload='metadata' src='https://preview.carbonpanel.invalid/media'></video>"
            }
            html = "<!doctype html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{margin:0;background:#101412;color:#ddd;font:14px system-ui}img,video,audio{max-width:100%;max-height:80vh;display:block;margin:auto}p{padding:16px;line-height:1.6}</style></head><body>$tag<p>If your device cannot display this format or codec, download the original.</p></body></html>"
        } else repo.filePreview(file.path).onSuccess { html = it }.onFailure { error = it.message }
    }
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column {
                Row(Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = onClose) { Text("Close") }
                    Text(file.name, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f).padding(top = 12.dp))
                    TextButton(onClick = onDownload, enabled = !downloading) { Text(if (downloading) "Saving…" else "Download") }
                }
                error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(16.dp)) }
                val document = html
                if (document == null && error == null) LinearProgressIndicator(Modifier.fillMaxWidth())
                if (document != null) key(file.path) {
                    AndroidView(modifier = Modifier.fillMaxSize(), factory = { ctx ->
                        WebView(ctx).apply {
                            settings.javaScriptEnabled = false
                            settings.allowFileAccess = false
                            settings.allowContentAccess = false
                            settings.domStorageEnabled = false
                            settings.setSupportZoom(true)
                            settings.builtInZoomControls = true
                            settings.displayZoomControls = false
                            settings.mediaPlaybackRequiresUserGesture = true
                            webViewClient = object : WebViewClient() {
                                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?) = true
                                override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse {
                                    if (media && request?.url.toString() == "https://preview.carbonpanel.invalid/media") {
                                        return try {
                                            val builder = Request.Builder().url(fileUrl(context, file.path))
                                            request?.requestHeaders?.get("Range")?.let { builder.header("Range", it) }
                                            val response = ApiClient.imageClient(context).newCall(builder.build()).execute()
                                            val body = response.body
                                            if (body == null) { response.close(); blocked() } else {
                                                val mime = body.contentType()?.let { "${it.type}/${it.subtype}" } ?: "application/octet-stream"
                                                WebResourceResponse(mime, null, response.code, response.message.ifBlank { "Response" }, response.headers.toMap(), body.byteStream())
                                            }
                                        } catch (_: Exception) { blocked() }
                                    }
                                    return blocked()
                                }
                            }
                            loadDataWithBaseURL("https://preview.carbonpanel.invalid/", document, "text/html", "UTF-8", null)
                        }
                    }, onRelease = { it.stopLoading(); it.destroy() })
                }
            }
        }
    }
}

private fun blocked() = WebResourceResponse("text/plain", "UTF-8", 403, "Blocked", emptyMap(), ByteArrayInputStream("External resources are disabled".toByteArray()))

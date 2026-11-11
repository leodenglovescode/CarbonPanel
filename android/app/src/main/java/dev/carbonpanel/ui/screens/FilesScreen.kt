package dev.carbonpanel.ui.screens

import android.annotation.SuppressLint
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebChromeClient
import androidx.activity.ComponentActivity
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.InsertDriveFile
import androidx.compose.material.icons.automirrored.filled.ViewList
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil.ImageLoader
import coil.compose.AsyncImage
import coil.request.CachePolicy
import coil.request.ImageRequest
import dev.carbonpanel.data.FileEntry
import dev.carbonpanel.data.FileListing
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.net.ApiClient
import dev.carbonpanel.repo.PanelRepository
import kotlinx.coroutines.delay
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Request
import java.io.ByteArrayInputStream

/** Read-only navigation; all file access uses the existing authenticated, pinned client. */
@Composable
fun FilesScreen() {
    val context = LocalContext.current
    val compactHeight = LocalConfiguration.current.screenHeightDp < 500
    val focusManager = LocalFocusManager.current
    var searchExpanded by rememberSaveable { mutableStateOf(false) }
    val repo = remember { PanelRepository(context.applicationContext) }
    val prefs = remember { Prefs.get(context) }
    val transfers: FileTransferViewModel = viewModel(viewModelStoreOwner = context as ComponentActivity)
    var directory by rememberSaveable { mutableStateOf("/") }
    var pathInput by rememberSaveable { mutableStateOf("/") }
    var pathDialog by remember { mutableStateOf(false) }
    var offset by rememberSaveable { mutableIntStateOf(0) }
    var refresh by remember { mutableIntStateOf(0) }
    var listing by remember { mutableStateOf<FileListing?>(null) }
    var busy by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var selected by remember { mutableStateOf<FileEntry?>(null) }
    var pendingPath by rememberSaveable { mutableStateOf<String?>(null) }
    var pendingName by rememberSaveable { mutableStateOf("") }
    val pendingDownload = pendingPath?.let { FileEntry(name = pendingName, path = it, directory = false) }
    val transfer = transfers.file
    val transferred = transfers.received
    val transferSize = transfers.total
    val notice = transfers.notice
    var filter by rememberSaveable { mutableStateOf("") }
    var search by remember { mutableStateOf("") }
    var sort by rememberSaveable { mutableStateOf("name") }
    var hidden by rememberSaveable { mutableStateOf(false) }
    var grid by rememberSaveable { mutableStateOf(prefs.filesGrid) }
    var options by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val gridState = rememberLazyGridState()
    val snackbar = remember { SnackbarHostState() }
    val imageLoader = remember { ImageLoader.Builder(context).okHttpClient { ApiClient.fileClient(context) }.build() }
    DisposableEffect(Unit) { onDispose { imageLoader.shutdown() } }
    fun open(path: String, pageOffset: Int = 0) {
        if (path.isBlank()) return
        directory = path.trim(); offset = pageOffset
        if (pageOffset == 0) { filter = ""; search = "" }
        refresh++
    }
    val currentPath = if (busy || error != null) directory else listing?.path ?: directory
    val parent = currentPath.trimEnd('/').substringBeforeLast('/', "").ifBlank { "/" }
    BackHandler(enabled = selected == null && currentPath != "/") { open(parent) }
    LaunchedEffect(filter) { delay(250); if (search != filter.trim()) { offset = 0; search = filter.trim() } }
    LaunchedEffect(directory, offset, search, sort, hidden, refresh) {
        busy = true; error = null
        repo.files(directory, offset, search, sort, hidden)
            .onSuccess { listing = it; pathInput = it.path; listState.requestScrollToItem(0); gridState.requestScrollToItem(0) }
            .onFailure { error = it.message ?: "This folder could not be opened." }
        busy = false
    }
    LaunchedEffect(notice, selected) { if (selected == null) notice?.let { snackbar.showSnackbar(it, actionLabel = "Dismiss", duration = if (it.startsWith("Downloaded ")) SnackbarDuration.Short else SnackbarDuration.Indefinite); transfers.clearNotice() } }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri ->
        val file = pendingDownload
        pendingPath = null
        if (uri != null && file != null) {
            transfers.start(file, uri, fileUrl(context, file.path, true), ApiClient.fileClient(context))
        }
    }
    fun download(file: FileEntry) {
        if (transfer == null && pendingDownload == null) {
            transfers.clearNotice(); pendingName = file.name; pendingPath = file.path
            save.launch(file.name)
        }
    }
    Column(Modifier.fillMaxSize().padding(horizontal = 14.dp), verticalArrangement = Arrangement.spacedBy(if (compactHeight) 4.dp else 10.dp)) {
        if (!compactHeight) Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(if (currentPath == "/") "Server files" else currentPath.substringAfterLast('/'), maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleLarge)
                Text("Read only", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconToggleButton(checked = !grid, onCheckedChange = { grid = false; prefs.filesGrid = false }) {
                Icon(Icons.AutoMirrored.Filled.ViewList, contentDescription = "List view")
            }
            IconToggleButton(checked = grid, onCheckedChange = { grid = true; prefs.filesGrid = true }) {
                Icon(Icons.Default.GridView, contentDescription = "Grid view")
            }
            Box {
                IconButton(onClick = { options = true }) { Icon(Icons.Default.MoreVert, contentDescription = "Folder options") }
                DropdownMenu(expanded = options, onDismissRequest = { options = false }) {
                    DropdownMenuItem(text = { Text("Go to folder…") }, onClick = { options = false; pathInput = currentPath; pathDialog = true })
                    DropdownMenuItem(text = { Text(if (hidden) "Hide hidden files" else "Show hidden files") }, onClick = { hidden = !hidden; offset = 0; options = false })
                    DropdownMenuItem(text = { Text("Refresh") }, onClick = { refresh++; options = false })
                }
            }
        }
        Surface(shape = RoundedCornerShape(10.dp), color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = .35f)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { open(parent) }, enabled = currentPath != "/" && !busy) { Icon(Icons.Default.ArrowUpward, contentDescription = "Parent folder") }
                Row(Modifier.weight(1f).horizontalScroll(rememberScrollState()), verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = { open("/") }) { Text("Server") }
                    val parts = currentPath.split('/').filter { it.isNotBlank() }
                    parts.forEachIndexed { index, name ->
                        Text("/", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        TextButton(onClick = { open("/" + parts.take(index + 1).joinToString("/")) }) { Text(name) }
                    }
                }
                if (compactHeight) {
                    IconToggleButton(checked = searchExpanded, onCheckedChange = { searchExpanded = it }) { Icon(Icons.Default.Search, contentDescription = "Search this folder") }
            IconToggleButton(checked = !grid, onCheckedChange = { grid = false; prefs.filesGrid = false }) {
                Icon(Icons.AutoMirrored.Filled.ViewList, contentDescription = "List view")
            }
            IconToggleButton(checked = grid, onCheckedChange = { grid = true; prefs.filesGrid = true }) {
                Icon(Icons.Default.GridView, contentDescription = "Grid view")
            }
            Box {
                IconButton(onClick = { options = true }) { Icon(Icons.Default.MoreVert, contentDescription = "Folder options") }
                DropdownMenu(expanded = options, onDismissRequest = { options = false }) {
                    DropdownMenuItem(text = { Text("Go to folder…") }, onClick = { options = false; pathInput = currentPath; pathDialog = true })
                    DropdownMenuItem(text = { Text(if (hidden) "Hide hidden files" else "Show hidden files") }, onClick = { hidden = !hidden; offset = 0; options = false })
                    DropdownMenuItem(text = { Text("Refresh") }, onClick = { refresh++; options = false })
                }
            }
                }
            }
        }
        if (!compactHeight || searchExpanded) OutlinedTextField(filter, { filter = it.take(200) }, placeholder = { Text("Search this folder") }, singleLine = true,
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            trailingIcon = { if (filter.isNotEmpty()) IconButton(onClick = { filter = "" }) { Icon(Icons.Default.Close, contentDescription = "Clear search") } },
            modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search), keyboardActions = KeyboardActions(onSearch = { focusManager.clearFocus(); if (compactHeight) searchExpanded = false }))
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            Text(if (busy) "Loading folder…" else if (error != null) "Folder unavailable" else "${listing?.total ?: 0} ${if (search.isBlank()) "items" else "matches"}${if (compactHeight && search.isNotBlank()) " · $search" else ""}", modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            var sortMenu by remember { mutableStateOf(false) }
            Box {
                TextButton(onClick = { sortMenu = true }) { Text(when (sort) { "modified" -> "Newest first"; "size" -> "Largest first"; "kind" -> "File type"; else -> "Name A–Z" }); Icon(Icons.Default.ArrowDropDown, contentDescription = null) }
                DropdownMenu(expanded = sortMenu, onDismissRequest = { sortMenu = false }) {
                    listOf("name" to "Name A–Z", "modified" to "Newest first", "size" to "Largest first", "kind" to "File type").forEach { (key, title) ->
                        DropdownMenuItem(text = { Text(title) }, onClick = { offset = 0; sort = key; sortMenu = false })
                    }
                }
            }
        }
        FileTransfer(transfer, transferred, transferSize) { transfers.cancel() }
        Box(Modifier.weight(1f).fillMaxWidth()) {
            val data = listing
            when {
                busy && data == null -> Unit
                error != null -> FileEmpty("Couldn’t open this folder", error.orEmpty(), "Try again", { refresh++ })
                data == null || data.entries.isEmpty() -> FileEmpty(if (search.isNotBlank()) "No matching files" else "This folder is empty", if (search.isNotBlank()) "Search checks names in this folder, not its subfolders." else "${if (hidden) "No files here." else "Hidden files are off."}", if (search.isNotBlank()) "Clear search" else null, { filter = "" })
                grid -> LazyVerticalGrid(columns = GridCells.Adaptive(145.dp), state = gridState, horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp), contentPadding = PaddingValues(bottom = 12.dp)) {
                    gridItems(data.entries, key = { it.path }) { file -> FileTile(file, imageLoader, { if (file.directory) open(file.path) else selected = file }, { download(file) }, transfer == null && pendingDownload == null) }
                }
                else -> LazyColumn(state = listState, contentPadding = PaddingValues(bottom = 12.dp)) {
                    items(data.entries, key = { it.path }) { file ->
                        Row(Modifier.fillMaxWidth().clickable { if (file.directory) open(file.path) else selected = file }.padding(vertical = if (compactHeight) 6.dp else 10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Icon(fileIcon(file), contentDescription = null, tint = if (file.directory) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(30.dp))
                            Column(Modifier.weight(1f)) { Text(file.name, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium); Text(if (file.directory) "Folder" else "${fileSize(file.size)} · ${fileKind(file)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            if (file.directory) Icon(Icons.Default.ChevronRight, contentDescription = null) else IconButton(onClick = { download(file) }, enabled = transfer == null && pendingDownload == null) { Icon(Icons.Default.Download, contentDescription = "Download ${file.name}") }
                        }
                        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = .4f))
                    }
                }
            }
        }
        listing?.takeIf { !busy && error == null }?.let { data ->
            if (data.offset > 0 || data.has_more) Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = { offset = (data.offset - 200).coerceAtLeast(0) }, enabled = data.offset > 0) { Text("Previous") }
                Text("${data.offset + 1}–${data.offset + data.entries.size} of ${data.total}", style = MaterialTheme.typography.labelSmall)
                TextButton(onClick = { offset = data.offset + 200 }, enabled = data.has_more) { Text("Next") }
            }
        }
        SnackbarHost(snackbar)
    }
    if (pathDialog) AlertDialog(onDismissRequest = { pathDialog = false }, title = { Text("Go to folder") }, text = {
        OutlinedTextField(pathInput, { pathInput = it }, singleLine = true, label = { Text("Folder path") }, keyboardOptions = KeyboardOptions(imeAction = ImeAction.Go), keyboardActions = KeyboardActions(onGo = { open(pathInput); pathDialog = false }))
    }, confirmButton = { TextButton(onClick = { open(pathInput); pathDialog = false }, enabled = pathInput.isNotBlank()) { Text("Go") } }, dismissButton = { TextButton(onClick = { pathDialog = false }) { Text("Cancel") } })
    selected?.let { file -> FilePreview(file, repo, onClose = { selected = null }, onDownload = { download(file) }, downloading = transfer != null || pendingDownload != null,
        transfer = transfer, transferred = transferred, transferSize = transferSize,
        onCancel = { transfers.cancel() }, notice = notice) }
}

@Composable
private fun FileTransfer(file: FileEntry?, transferred: Long, total: Long, onCancel: () -> Unit) {
    if (file == null) return
    val compact = LocalConfiguration.current.screenHeightDp < 500
    Surface(shape = RoundedCornerShape(10.dp), color = MaterialTheme.colorScheme.primaryContainer) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = if (compact) 0.dp else 12.dp), verticalArrangement = Arrangement.spacedBy(if (compact) 2.dp else 6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Downloading ${file.name}", maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelMedium)
                    Text("${fileSize(transferred)}${if (total >= 0) " / ${fileSize(total)}" else ""}", style = MaterialTheme.typography.bodySmall)
                }
                TextButton(onClick = onCancel) { Text("Cancel") }
            }
            if (total > 0) LinearProgressIndicator(progress = { (transferred.toFloat() / total).coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth()) else LinearProgressIndicator(Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun FileEmpty(title: String, detail: String, action: String?, onAction: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
        Icon(Icons.Default.FolderOpen, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(44.dp))
        Spacer(Modifier.height(16.dp)); Text(title, style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(8.dp)); Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (action != null) TextButton(onClick = onAction) { Text(action) }
    }
}

private fun fileIcon(file: FileEntry): ImageVector = when {
    file.directory -> Icons.Default.Folder
    file.kind == "image" -> Icons.Default.Image
    file.kind == "video" -> Icons.Default.VideoFile
    file.kind == "audio" -> Icons.Default.AudioFile
    file.kind == "markdown" || file.kind == "text" -> Icons.Default.Description
    else -> Icons.AutoMirrored.Filled.InsertDriveFile
}
private fun fileKind(file: FileEntry) = when (file.kind) { "image" -> "Image"; "video" -> "Video"; "audio" -> "Audio"; "markdown" -> "Markdown"; "text" -> "Text / code"; else -> "File" }

@Composable
private fun FileTile(file: FileEntry, imageLoader: ImageLoader, onOpen: () -> Unit, onDownload: () -> Unit, downloadEnabled: Boolean) {
    val context = LocalContext.current
    Surface(shape = RoundedCornerShape(12.dp), color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = .3f)) {
        Column {
            Column(Modifier.fillMaxWidth().clickable(onClick = onOpen).padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.fillMaxWidth().height(86.dp).clip(RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) {
                    Icon(fileIcon(file), contentDescription = null, tint = if (file.directory) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(44.dp))
                    if (file.kind == "image" && (file.size ?: 0L) <= 8L * 1024 * 1024) {
                        var loading by remember(file.path) { mutableStateOf(true) }
                        AsyncImage(model = ImageRequest.Builder(context).data(fileUrl(context, file.path)).memoryCachePolicy(CachePolicy.DISABLED).diskCachePolicy(CachePolicy.DISABLED).crossfade(true).build(), imageLoader = imageLoader, contentDescription = null, modifier = Modifier.fillMaxSize(), onSuccess = { loading = false }, onError = { loading = false })
                        if (loading) CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                    }
                }
                Spacer(Modifier.height(8.dp)); Text(file.name, maxLines = 2, minLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
                Text(if (file.directory) "Folder" else fileSize(file.size), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (!file.directory) { HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = .4f)); TextButton(onClick = onDownload, enabled = downloadEnabled, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp)); Spacer(Modifier.width(6.dp)); Text("Download") } }
        }
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
private fun FilePreview(file: FileEntry, repo: PanelRepository, onClose: () -> Unit, onDownload: () -> Unit, downloading: Boolean,
    transfer: FileEntry?, transferred: Long, transferSize: Long, onCancel: () -> Unit, notice: String?) {
    val context = LocalContext.current
    var html by remember(file.path) { mutableStateOf<String?>(null) }
    var error by remember(file.path) { mutableStateOf<String?>(null) }
    var pageProgress by remember(file.path) { mutableIntStateOf(0) }
    val unsupported = file.kind == "file"
    val media = file.kind in listOf("image", "video", "audio")
    LaunchedEffect(file.path) {
        if (unsupported) return@LaunchedEffect
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
                FileTransfer(transfer, transferred, transferSize, onCancel)
                notice?.let { Text(it, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodySmall) }
                error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(16.dp)) }
                if (unsupported) FileEmpty("Preview isn’t available", "Download this file to open it in a compatible app.", if (downloading) null else "Download", onDownload)
                val document = html
                if (!unsupported && error == null && (document == null || pageProgress < 100)) {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                    Text("Loading preview…", modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodySmall)
                }
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
                            webChromeClient = object : WebChromeClient() {
                                override fun onProgressChanged(view: WebView?, newProgress: Int) { pageProgress = newProgress }
                            }
                            webViewClient = object : WebViewClient() {
                                override fun onPageFinished(view: WebView?, url: String?) { pageProgress = 100 }
                                override fun onReceivedError(view: WebView?, request: WebResourceRequest?, failure: android.webkit.WebResourceError?) {
                                    if (request?.isForMainFrame == true) { error = "Preview could not be loaded. Download the original to open it in another app."; pageProgress = 100 }
                                }
                                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?) = true
                                override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse {
                                    if (media && request?.url.toString() == "https://preview.carbonpanel.invalid/media") {
                                        return try {
                                            val builder = Request.Builder().url(fileUrl(context, file.path))
                                            request?.requestHeaders?.get("Range")?.let { builder.header("Range", it) }
                                            val response = ApiClient.fileClient(context).newCall(builder.build()).execute()
                                            if (!response.isSuccessful) {
                                                val status = response.code; response.close()
                                                view?.post { error = "The file could not be read (HTTP $status)."; pageProgress = 100 }
                                                return blocked()
                                            }
                                            val body = response.body
                                            if (body == null) { response.close(); blocked() } else {
                                                val mime = body.contentType()?.let { "${it.type}/${it.subtype}" } ?: "application/octet-stream"
                                                WebResourceResponse(mime, null, response.code, response.message.ifBlank { "Response" }, response.headers.toMap(), body.byteStream())
                                            }
                                        } catch (_: Exception) { view?.post { error = "The media could not be loaded. Check your connection and try again."; pageProgress = 100 }; blocked() }
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

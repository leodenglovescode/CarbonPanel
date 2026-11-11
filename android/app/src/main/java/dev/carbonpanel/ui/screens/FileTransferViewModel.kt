package dev.carbonpanel.ui.screens

import android.app.Application
import android.net.Uri
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dev.carbonpanel.data.FileEntry
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.Call
import okhttp3.OkHttpClient
import okhttp3.Request

/** Activity-owned transfers survive folder/page changes and configuration changes. */
class FileTransferViewModel(app: Application) : AndroidViewModel(app) {
    var file by mutableStateOf<FileEntry?>(null)
        private set
    var received by mutableLongStateOf(0)
        private set
    var total by mutableLongStateOf(-1)
        private set
    var notice by mutableStateOf<String?>(null)
        private set
    private var job: Job? = null
    private var call: Call? = null
    private var cancelRequested = false

    fun clearNotice() { notice = null }
    fun cancel() { cancelRequested = true; call?.cancel(); job?.cancel() }

    fun start(entry: FileEntry, destination: Uri, url: String, client: OkHttpClient) {
        if (file != null) return
        file = entry; received = 0; total = -1; notice = null; cancelRequested = false
        val request = client.newCall(Request.Builder().url(url).build())
        call = request
        job = viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    request.execute().use { response ->
                        check(response.isSuccessful) {
                            when (response.code) {
                                403 -> "The server account cannot read this file."
                                404 -> "This file no longer exists."
                                else -> "Download failed (HTTP ${response.code})"
                            }
                        }
                        val body = response.body ?: error("Empty download response")
                        withContext(Dispatchers.Main) { total = body.contentLength() }
                        val resolver = getApplication<Application>().contentResolver
                        resolver.openOutputStream(destination, "w")?.use { output ->
                            body.byteStream().use { input ->
                                val buffer = ByteArray(128 * 1024)
                                var count = 0L
                                var lastUpdate = 0L
                                while (true) {
                                    ensureActive()
                                    val read = input.read(buffer)
                                    if (read < 0) break
                                    output.write(buffer, 0, read)
                                    count += read
                                    val now = SystemClock.elapsedRealtime()
                                    if (now - lastUpdate > 150) {
                                        lastUpdate = now
                                        withContext(Dispatchers.Main) { received = count }
                                    }
                                }
                                withContext(Dispatchers.Main) { received = count }
                            }
                        } ?: error("Cannot write to the selected destination")
                    }
                }
                notice = "Downloaded ${entry.name}"
            } catch (e: CancellationException) {
                notice = "Download canceled. A partial file may remain."
                throw e
            } catch (e: Exception) {
                notice = e.message ?: "Download failed"
            } finally {
                if (cancelRequested) notice = "Download canceled. A partial file may remain."
                file = null; call = null; job = null
            }
        }
    }

    override fun onCleared() { call?.cancel(); super.onCleared() }
}

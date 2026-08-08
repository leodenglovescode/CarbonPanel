package dev.carbonpanel.pairing

import android.app.Application
import android.os.Build
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dev.carbonpanel.data.ClaimRequest
import dev.carbonpanel.data.Prefs
import dev.carbonpanel.data.QrPayload
import dev.carbonpanel.net.ApiClient
import dev.carbonpanel.widget.StatusWidgetWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.Json

sealed interface PairState {
    data object Idle : PairState
    data object Working : PairState
    data class Failed(val message: String) : PairState
    data class Paired(val serverName: String, val username: String) : PairState
}

class PairingViewModel(app: Application) : AndroidViewModel(app) {

    private val json = Json { ignoreUnknownKeys = true }
    private val prefs get() = Prefs.get(getApplication())

    private val _state = MutableStateFlow<PairState>(PairState.Idle)
    val state: StateFlow<PairState> = _state.asStateFlow()

    fun reset() {
        _state.value = PairState.Idle
    }

    /** Handle a scanned QR payload, or a manually typed code plus URL. */
    fun pairFromQr(raw: String) {
        val payload = runCatching { json.decodeFromString<QrPayload>(raw) }.getOrNull()
        if (payload == null) {
            _state.value = PairState.Failed(
                "That QR code isn't a CarbonPanel pairing code."
            )
            return
        }
        if (payload.v != 1) {
            _state.value = PairState.Failed(
                "This pairing code was made by a newer version of CarbonPanel. Update the app."
            )
            return
        }
        pair(payload.e, payload.c, payload.n)
    }

    fun pairManually(baseUrl: String, code: String) {
        val url = baseUrl.trim().trimEnd('/')
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            _state.value = PairState.Failed("Address must start with http:// or https://")
            return
        }
        pair(listOf(url), code.trim().uppercase(), null)
    }

    private fun pair(endpoints: List<String>, code: String, serverName: String?) {
        if (endpoints.isEmpty()) {
            _state.value = PairState.Failed("The pairing code contains no server address.")
            return
        }
        _state.value = PairState.Working

        viewModelScope.launch {
            val usable = endpoints.filter { ApiClient.isPermittedEndpoint(it) }
            if (usable.isEmpty()) {
                _state.value = PairState.Failed(
                    "Every address in this code is plain HTTP on a public network. " +
                        "Put TLS in front of the panel, or pair over a VPN address."
                )
                return@launch
            }

            // Endpoints arrive best-first, but only some are reachable from
            // wherever the phone is standing — try each until one answers.
            val deviceName = "${Build.MANUFACTURER} ${Build.MODEL}".trim()
            for (url in usable) {
                val result = withContext(Dispatchers.IO) {
                    withTimeoutOrNull(8_000) {
                        runCatching {
                            ApiClient.forBaseUrl(getApplication(), url)
                                .claim(ClaimRequest(code = code, device_name = deviceName))
                        }
                    }
                }
                val claim = result?.getOrNull()
                if (claim != null) {
                    prefs.token = claim.token
                    prefs.username = claim.username
                    prefs.serverName = serverName ?: claim.server_name
                    // Keep every endpoint, not just the one that worked — the
                    // phone will be on a different network tomorrow.
                    prefs.endpoints = usable
                    prefs.lastGoodEndpoint = url
                    ApiClient.clearCache()
                    // Any widget placed before pairing is showing "Not paired".
                    // Nothing else would clear it until the next periodic run,
                    // which is up to 30 minutes away.
                    StatusWidgetWorker.refreshNow(getApplication())
                    _state.value = PairState.Paired(
                        serverName = prefs.serverName ?: "CarbonPanel",
                        username = claim.username,
                    )
                    return@launch
                }
                // A code is single-use: if the server accepted it on an earlier
                // address and only the response was lost, retrying elsewhere
                // will fail too. Surfacing the last error is the honest outcome.
                val error = result?.exceptionOrNull()
                if (error != null && error.message?.contains("400") == true) {
                    _state.value = PairState.Failed(
                        "That pairing code was already used or has expired. Generate a new one."
                    )
                    return@launch
                }
            }
            _state.value = PairState.Failed(
                "Couldn't reach the server at any of its addresses:\n" +
                    usable.joinToString("\n") { "  • $it" }
            )
        }
    }
}

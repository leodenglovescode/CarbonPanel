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
    private var prefs = Prefs.get(app).newServer()

    private val _state = MutableStateFlow<PairState>(PairState.Idle)
    val state: StateFlow<PairState> = _state.asStateFlow()

    fun reset() {
        if (prefs.servers.none { it.id == prefs.serverId }) prefs.clear()
        prefs = Prefs.get(getApplication()).newServer()
        _state.value = PairState.Idle
    }

    /** Handle a scanned QR payload, or a manually typed code plus URL. */
    fun pairFromQr(raw: String) {
        if (_state.value is PairState.Working) return
        val payload = runCatching { json.decodeFromString<QrPayload>(raw) }.getOrNull()
        if (payload == null) {
            _state.value = PairState.Failed(
                "That QR code isn't a CarbonPanel pairing code."
            )
            return
        }
        if (payload.v != 2) {
            _state.value = PairState.Failed(
                "This pairing code uses an unsupported security version. Generate a new code."
            )
            return
        }
        pair(payload.e, payload.c, payload.n, payload.f, payload.p)
    }

    fun pairManually(baseUrl: String, code: String) {
        if (_state.value is PairState.Working) return
        val url = baseUrl.trim().trimEnd('/')
        if (!ApiClient.isPermittedEndpoint(url)) {
            _state.value = PairState.Failed("Address must be a valid https:// URL")
            return
        }
        pair(listOf(url), code.trim().uppercase(), null, null, emptyList())
    }

    private fun pair(
        endpoints: List<String>,
        code: String,
        serverName: String?,
        certificateFingerprint: String?,
        pinnedHosts: List<String>,
    ) {
        if (endpoints.isEmpty()) {
            _state.value = PairState.Failed("The pairing code contains no server address.")
            return
        }
        _state.value = PairState.Working

        viewModelScope.launch {
            val usable = endpoints.filter { ApiClient.isPermittedEndpoint(it) }
            if (usable.isEmpty()) {
                _state.value = PairState.Failed(
                    "This pairing code has no valid HTTPS server address."
                )
                return@launch
            }

            val normalizedFingerprint = certificateFingerprint
                ?.replace(":", "")
                ?.uppercase()
            if (normalizedFingerprint != null &&
                !normalizedFingerprint.matches(Regex("^[0-9A-F]{64}$"))
            ) {
                _state.value = PairState.Failed("The pairing code has an invalid certificate pin.")
                return@launch
            }
            val allowedPinHosts = pinnedHosts.map { it.lowercase() }.toSet()
            val hosts = usable.mapNotNull { runCatching { java.net.URI(it).host }.getOrNull() }
                .filter { it.lowercase() in allowedPinHosts }
                .distinct()
            val previousPins = hosts.associateWith { prefs.pinnedCert(it) }
            if (normalizedFingerprint != null) {
                hosts.forEach { prefs.setPinnedCert(it, normalizedFingerprint) }
                ApiClient.clearCache()
            }

            fun restorePins() {
                if (normalizedFingerprint == null) return
                previousPins.forEach { (host, oldPin) ->
                    if (oldPin == null) prefs.removePinnedCert(host)
                    else prefs.setPinnedCert(host, oldPin)
                }
                ApiClient.clearCache()
            }

            // Endpoints arrive best-first, but only some are reachable from
            // wherever the phone is standing — try each until one answers.
            val deviceName = "${Build.MANUFACTURER} ${Build.MODEL}".trim()
            val failures = mutableListOf<String>()
            for (url in usable) {
                val result = withContext(Dispatchers.IO) {
                    withTimeoutOrNull(8_000) {
                        try {
                            Result.success(ApiClient.forBaseUrl(getApplication(), url, prefs)
                                .claim(ClaimRequest(code = code, device_name = deviceName)))
                        } catch (error: kotlinx.coroutines.CancellationException) {
                            throw error
                        } catch (error: Exception) {
                            Result.failure(error)
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
                    prefs.saveServer()
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
                val error = result?.exceptionOrNull()
                val detail = error?.let(::pairingError) ?: "Connection timed out."
                failures += "$url\n$detail"
                // These responses establish contact with the server; trying
                // other addresses cannot make an expired or rate-limited code work.
                if (error is retrofit2.HttpException && error.code() in listOf(400, 422, 429)) {
                    restorePins()
                    _state.value = PairState.Failed(detail)
                    return@launch
                }
            }
            restorePins()
            _state.value = PairState.Failed(failures.joinToString("\n\n"))
        }
    }
}

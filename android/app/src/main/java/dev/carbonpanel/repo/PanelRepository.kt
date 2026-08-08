package dev.carbonpanel.repo

import android.content.Context
import dev.carbonpanel.data.*
import dev.carbonpanel.net.Api
import dev.carbonpanel.net.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn

sealed interface PollState {
    data object Connecting : PollState
    data class Connected(val snapshot: MetricsSnapshot, val endpoint: String) : PollState
    data class Error(val message: String) : PollState
    data object Unpaired : PollState
}

/**
 * Single entry point to the panel.
 *
 * Every call resolves an endpoint first, so moving between networks is handled
 * in one place rather than in each screen.
 */
class PanelRepository(private val context: Context) {

    private val prefs get() = Prefs.get(context)

    private suspend fun api(): Api =
        ApiClient.resolve(context)?.second ?: error("Server unreachable")

    /**
     * Runs [block] against the panel, mapping failures to a readable message.
     *
     * Retrofit throws HttpException for non-2xx, whose message is just the
     * status line; the server's `detail` field is the part worth showing.
     */
    private suspend fun <T> call(block: suspend (Api) -> T): Result<T> = runCatching {
        block(api())
    }.recoverCatching { t -> throw IllegalStateException(readableError(t), t) }

    private fun readableError(t: Throwable): String {
        val http = t as? retrofit2.HttpException
        if (http != null) {
            val body = runCatching { http.response()?.errorBody()?.string() }.getOrNull()
            val detail = body?.let {
                Regex("\"detail\"\\s*:\\s*\"([^\"]+)\"").find(it)?.groupValues?.get(1)
            }
            return detail ?: "HTTP ${http.code()}"
        }
        return t.message ?: "Request failed"
    }

    // ── metrics ────────────────────────────────────────────────────────────

    /**
     * Emits metrics until cancelled.
     *
     * A cold Flow with no internal scope on purpose: callers collect it under
     * `repeatOnLifecycle(STARTED)`, so backgrounding the app cancels the
     * coroutine and stops every request. That is the whole background-battery
     * story — no service, no wakelock, no socket held open.
     */
    fun metricsStream(fields: String? = null): Flow<PollState> = flow {
        if (!prefs.isPaired) {
            emit(PollState.Unpaired)
            return@flow
        }
        emit(PollState.Connecting)

        var resolved = ApiClient.resolve(context)
        if (resolved == null) {
            emit(PollState.Error("No reachable address for this server"))
            return@flow
        }

        var failures = 0
        while (true) {
            val interval = prefs.pollIntervalSeconds
            try {
                val snapshot = resolved!!.second.metricsCurrent(fields = fields, interval = interval)
                failures = 0
                emit(PollState.Connected(snapshot, resolved!!.first))
            } catch (t: Throwable) {
                failures++
                // The phone may have changed networks, which invalidates the
                // endpoint rather than the pairing. Re-resolve before giving up.
                if (failures >= 2) {
                    ApiClient.clearCache()
                    resolved = ApiClient.resolve(context)
                    if (resolved == null) {
                        emit(PollState.Error("Server unreachable"))
                        delay(5_000)
                        resolved = ApiClient.resolve(context)
                        continue
                    }
                } else {
                    emit(PollState.Error(readableError(t)))
                }
            }
            delay((interval * 1000).toLong().coerceAtLeast(400L))
        }
    }.flowOn(Dispatchers.IO)

    suspend fun history() = call { it.metricsHistory() }
    suspend fun snapshot(fields: String? = null) = call { it.metricsCurrent(fields = fields) }

    // ── docker ─────────────────────────────────────────────────────────────

    suspend fun containers() = call { it.containers() }

    suspend fun containerAction(id: String, action: String) = call { api ->
        val r = when (action) {
            "start" -> api.startContainer(id)
            "stop" -> api.stopContainer(id)
            "restart" -> api.restartContainer(id)
            else -> error("Unknown action $action")
        }
        if (!r.success) error(r.output.ifBlank { "$action failed" })
        r.output
    }

    // ── system services ────────────────────────────────────────────────────

    suspend fun services(includeAll: Boolean = false) =
        call { it.systemServices(includeAll = includeAll) }

    suspend fun serviceAction(name: String, action: String) = call { api ->
        val r = api.systemServiceAction(name, ServiceActionRequest(action))
        if (!r.success) error(r.output.ifBlank { "$action failed" })
        r.output
    }

    suspend fun serviceAutostart(name: String, enabled: Boolean) =
        call { it.systemServiceAutostart(name, ServiceAutostartRequest(enabled)) }

    suspend fun serviceStar(name: String, starred: Boolean) =
        call { it.systemServiceStar(name, ServiceStarRequest(starred)) }

    // ── sites ──────────────────────────────────────────────────────────────

    suspend fun sites() = call { it.sites() }
    suspend fun site(id: String) = call { it.site(id) }
    suspend fun siteConfig(id: String) = call { it.siteConfig(id) }
    suspend fun writeSiteConfig(id: String, content: String) =
        call { it.writeSiteConfig(id, ConfigWriteRequest(content)) }
    suspend fun siteTraffic(id: String, minutes: Int = 60) = call { it.siteTraffic(id, minutes) }

    suspend fun siteAction(id: String, action: String) = call { api ->
        val r = api.siteAction(id, SiteActionRequest(action))
        if (!r.success) error(r.output.ifBlank { "$action failed" })
        r.output
    }

    // ── disks ──────────────────────────────────────────────────────────────

    suspend fun disks() = call { it.disks() }
    suspend fun refreshSmart() = call { it.refreshSmart() }
    suspend fun unmount(mountpoint: String) = call { api ->
        val r = api.unmount(UnmountRequest(mountpoint))
        if (!r.success) error(r.output.ifBlank { "Unmount failed" })
        r.output
    }

    // ── cron ───────────────────────────────────────────────────────────────

    suspend fun cronEntries() = call { it.cronEntries() }
    suspend fun managedCron() = call { it.managedCron() }
    suspend fun createCron(label: String, schedule: String, command: String) =
        call { it.createCron(CronJobIn(label, schedule, command)) }
    suspend fun updateCron(id: String, label: String, schedule: String, command: String) =
        call { it.updateCron(id, CronJobIn(label, schedule, command)) }
    suspend fun deleteCron(id: String) = call { it.deleteCron(id) }

    // ── apps / ports / processes ───────────────────────────────────────────

    suspend fun apps() = call { it.apps() }
    suspend fun setAppLabel(port: Int, label: String) =
        call { it.setAppLabel(port, LabelRequest(label)) }
    suspend fun clearAppLabel(port: Int) = call { it.clearAppLabel(port) }
    suspend fun killApp(port: Int, force: Boolean) =
        call { it.killApp(port, KillRequest(force)) }
    suspend fun killProcess(pid: Int, force: Boolean) = call { api ->
        val r = api.killProcess(pid, KillRequest(force))
        if (!r.success) error(r.message.ifBlank { "Kill failed" })
        r.message
    }

    // ── misc lists ─────────────────────────────────────────────────────────

    suspend fun sessions() = call { it.sessions() }
    suspend fun bookmarks() = call { it.bookmarks() }
    suspend fun createBookmark(title: String, url: String) =
        call { it.createBookmark(BookmarkIn(title = title, url = url)) }
    suspend fun deleteBookmark(id: String) = call { it.deleteBookmark(id) }

    suspend fun webhooks() = call { it.webhooks() }
    suspend fun createWebhook(label: String, url: String, events: List<String>) =
        call { it.createWebhook(WebhookCreate(label = label, url = url, events = events)) }
    suspend fun updateWebhook(id: String, body: WebhookUpdate) = call { it.updateWebhook(id, body) }
    suspend fun deleteWebhook(id: String) = call { it.deleteWebhook(id) }

    // ── account / settings / system ────────────────────────────────────────

    suspend fun me() = call { it.me() }
    suspend fun devices() = call { it.devices() }
    suspend fun revokeDevice(id: String) = call { it.revokeDevice(id) }
    suspend fun proxy() = call { it.proxy() }
    suspend fun setProxy(config: ProxyConfig) = call { it.setProxy(config) }
    suspend fun version() = call { it.version() }
    suspend fun checkUpdates() = call { it.checkUpdates() }
    suspend fun serviceLogs() = call { it.serviceLogs() }
    suspend fun changeProfile(current: String, newUsername: String?, newPassword: String?) =
        call { it.changeProfile(ChangeProfileRequest(current, newUsername, newPassword)) }

    fun unpair() {
        prefs.clear()
        ApiClient.clearCache()
    }
}

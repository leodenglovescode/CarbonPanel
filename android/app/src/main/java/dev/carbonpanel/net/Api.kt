package dev.carbonpanel.net

import dev.carbonpanel.data.ActionResponse
import dev.carbonpanel.data.AppInfo
import dev.carbonpanel.data.BookmarkIn
import dev.carbonpanel.data.BookmarkOut
import dev.carbonpanel.data.ChangeProfileRequest
import dev.carbonpanel.data.ClaimRequest
import dev.carbonpanel.data.ClaimResponse
import dev.carbonpanel.data.ConfigReadResponse
import dev.carbonpanel.data.ConfigWriteRequest
import dev.carbonpanel.data.ContainerInfo
import dev.carbonpanel.data.CronEntry
import dev.carbonpanel.data.CronJob
import dev.carbonpanel.data.CronJobIn
import dev.carbonpanel.data.DeviceOut
import dev.carbonpanel.data.DiskInfo
import dev.carbonpanel.data.HistoryPoint
import dev.carbonpanel.data.KillRequest
import dev.carbonpanel.data.KillResponse
import dev.carbonpanel.data.LabelRequest
import dev.carbonpanel.data.MetricsSnapshot
import dev.carbonpanel.data.ProxyConfig
import dev.carbonpanel.data.ServiceActionRequest
import dev.carbonpanel.data.ServiceAutostartRequest
import dev.carbonpanel.data.ServiceLogs
import dev.carbonpanel.data.ServiceStarRequest
import dev.carbonpanel.data.SessionInfo
import dev.carbonpanel.data.SiteActionRequest
import dev.carbonpanel.data.SiteActionResponse
import dev.carbonpanel.data.SiteResponse
import dev.carbonpanel.data.SiteTrafficResponse
import dev.carbonpanel.data.SuccessResponse
import dev.carbonpanel.data.SystemServiceInfo
import dev.carbonpanel.data.UnmountRequest
import dev.carbonpanel.data.UserInfo
import dev.carbonpanel.data.VersionStatus
import dev.carbonpanel.data.WebhookCreate
import dev.carbonpanel.data.WebhookResponse
import dev.carbonpanel.data.WebhookUpdate
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * The panel's HTTP API.
 *
 * Paths mirror the server's routers one-for-one. Everything is authenticated
 * by the bearer token injected in ApiClient's interceptor, except [claim],
 * which is the one call made before a token exists.
 */
interface Api {

    // ── pairing ────────────────────────────────────────────────────────────

    @POST("api/v1/pairing/claim")
    suspend fun claim(@Body body: ClaimRequest): ClaimResponse

    // ── metrics ────────────────────────────────────────────────────────────

    /**
     * Latest metrics.
     *
     * [fields] trims the payload to the sections actually on screen — the full
     * snapshot is ~20KB and cpu+memory is ~6KB, which at a sub-second poll is
     * the whole mobile-data budget. [interval] tells the server how fast this
     * client intends to poll so the shared collector keeps pace.
     */
    @GET("api/v1/metrics/current")
    suspend fun metricsCurrent(
        @Query("fields") fields: String? = null,
        @Query("interval") interval: Float? = null,
        @Query("sort") sort: String = "cpu",
        @Query("limit") limit: Int = 25,
    ): MetricsSnapshot

    @GET("api/v1/metrics/history")
    suspend fun metricsHistory(): List<HistoryPoint>

    /** Cheap authenticated call used to decide whether an endpoint is alive. */
    @GET("api/v1/metrics/current")
    suspend fun ping(@Query("fields") fields: String = "cpu"): Response<Unit>

    // ── docker ─────────────────────────────────────────────────────────────

    @GET("api/v1/docker/containers")
    suspend fun containers(): List<ContainerInfo>

    @POST("api/v1/docker/containers/{id}/start")
    suspend fun startContainer(@Path("id") id: String): ActionResponse

    @POST("api/v1/docker/containers/{id}/stop")
    suspend fun stopContainer(@Path("id") id: String): ActionResponse

    @POST("api/v1/docker/containers/{id}/restart")
    suspend fun restartContainer(@Path("id") id: String): ActionResponse

    // ── system services ────────────────────────────────────────────────────

    @GET("api/v1/sites/system-services")
    suspend fun systemServices(
        @Query("include_all") includeAll: Boolean = false,
        @Query("starred_only") starredOnly: Boolean = false,
    ): List<SystemServiceInfo>

    @POST("api/v1/sites/system-services/{name}/action")
    suspend fun systemServiceAction(
        @Path("name") name: String,
        @Body body: ServiceActionRequest,
    ): SiteActionResponse

    @POST("api/v1/sites/system-services/{name}/autostart")
    suspend fun systemServiceAutostart(
        @Path("name") name: String,
        @Body body: ServiceAutostartRequest,
    ): SiteActionResponse

    @POST("api/v1/sites/system-services/{name}/star")
    suspend fun systemServiceStar(
        @Path("name") name: String,
        @Body body: ServiceStarRequest,
    ): SiteActionResponse

    // ── sites ──────────────────────────────────────────────────────────────

    @GET("api/v1/sites")
    suspend fun sites(): List<SiteResponse>

    @GET("api/v1/sites/{id}")
    suspend fun site(@Path("id") id: String): SiteResponse

    @POST("api/v1/sites/{id}/action")
    suspend fun siteAction(
        @Path("id") id: String,
        @Body body: SiteActionRequest,
    ): SiteActionResponse

    @GET("api/v1/sites/{id}/config")
    suspend fun siteConfig(@Path("id") id: String): ConfigReadResponse

    @PUT("api/v1/sites/{id}/config")
    suspend fun writeSiteConfig(
        @Path("id") id: String,
        @Body body: ConfigWriteRequest,
    ): SiteActionResponse

    @GET("api/v1/sites/{id}/traffic")
    suspend fun siteTraffic(
        @Path("id") id: String,
        @Query("minutes") minutes: Int = 60,
    ): SiteTrafficResponse

    @DELETE("api/v1/sites/{id}")
    suspend fun deleteSite(@Path("id") id: String): Response<Unit>

    // ── disks ──────────────────────────────────────────────────────────────

    @GET("api/v1/disks")
    suspend fun disks(): List<DiskInfo>

    @POST("api/v1/disks/smart/refresh")
    suspend fun refreshSmart(): ActionResponse

    @POST("api/v1/disks/unmount")
    suspend fun unmount(@Body body: UnmountRequest): ActionResponse

    // ── cron ───────────────────────────────────────────────────────────────

    @GET("api/v1/cron")
    suspend fun cronEntries(): List<CronEntry>

    @GET("api/v1/cron/managed")
    suspend fun managedCron(): List<CronJob>

    @POST("api/v1/cron/managed")
    suspend fun createCron(@Body body: CronJobIn): CronJob

    @PUT("api/v1/cron/managed/{id}")
    suspend fun updateCron(@Path("id") id: String, @Body body: CronJobIn): CronJob

    @DELETE("api/v1/cron/managed/{id}")
    suspend fun deleteCron(@Path("id") id: String): Response<Unit>

    // ── apps / listening ports ─────────────────────────────────────────────

    @GET("api/v1/apps")
    suspend fun apps(): List<AppInfo>

    @PUT("api/v1/apps/{port}/label")
    suspend fun setAppLabel(@Path("port") port: Int, @Body body: LabelRequest): ActionResponse

    @DELETE("api/v1/apps/{port}/label")
    suspend fun clearAppLabel(@Path("port") port: Int): ActionResponse

    @POST("api/v1/apps/{port}/kill")
    suspend fun killApp(@Path("port") port: Int, @Body body: KillRequest): ActionResponse

    // ── processes ──────────────────────────────────────────────────────────

    @POST("api/v1/processes/{pid}/kill")
    suspend fun killProcess(@Path("pid") pid: Int, @Body body: KillRequest): KillResponse

    // ── shell sessions ─────────────────────────────────────────────────────

    @GET("api/v1/sessions")
    suspend fun sessions(): List<SessionInfo>

    // ── bookmarks ──────────────────────────────────────────────────────────

    @GET("api/v1/bookmarks")
    suspend fun bookmarks(): List<BookmarkOut>

    @POST("api/v1/bookmarks")
    suspend fun createBookmark(@Body body: BookmarkIn): BookmarkOut

    @PUT("api/v1/bookmarks/{id}")
    suspend fun updateBookmark(@Path("id") id: String, @Body body: BookmarkIn): BookmarkOut

    @DELETE("api/v1/bookmarks/{id}")
    suspend fun deleteBookmark(@Path("id") id: String): Response<Unit>

    // ── webhooks ───────────────────────────────────────────────────────────

    @GET("api/v1/webhooks")
    suspend fun webhooks(): List<WebhookResponse>

    @POST("api/v1/webhooks")
    suspend fun createWebhook(@Body body: WebhookCreate): WebhookResponse

    @PUT("api/v1/webhooks/{id}")
    suspend fun updateWebhook(@Path("id") id: String, @Body body: WebhookUpdate): WebhookResponse

    @DELETE("api/v1/webhooks/{id}")
    suspend fun deleteWebhook(@Path("id") id: String): Response<Unit>

    // ── account & settings ─────────────────────────────────────────────────

    @GET("api/v1/auth/me")
    suspend fun me(): UserInfo

    @GET("api/v1/devices")
    suspend fun devices(): List<DeviceOut>

    @DELETE("api/v1/devices/{id}")
    suspend fun revokeDevice(@Path("id") id: String): Response<Unit>

    @PUT("api/v1/settings/profile")
    suspend fun changeProfile(@Body body: ChangeProfileRequest): SuccessResponse

    @GET("api/v1/settings/proxy")
    suspend fun proxy(): ProxyConfig

    @PUT("api/v1/settings/proxy")
    suspend fun setProxy(@Body body: ProxyConfig): ProxyConfig

    // ── system / updates ───────────────────────────────────────────────────

    @GET("api/v1/system/version")
    suspend fun version(): VersionStatus

    @POST("api/v1/system/check-updates")
    suspend fun checkUpdates(): Response<Unit>

    @GET("api/v1/system/service-logs")
    suspend fun serviceLogs(): ServiceLogs
}

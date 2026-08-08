package dev.carbonpanel.net

import dev.carbonpanel.data.ActionResponse
import dev.carbonpanel.data.ClaimRequest
import dev.carbonpanel.data.ClaimResponse
import dev.carbonpanel.data.ContainerInfo
import dev.carbonpanel.data.HistoryPoint
import dev.carbonpanel.data.MetricsSnapshot
import dev.carbonpanel.data.ServiceActionRequest
import dev.carbonpanel.data.SiteActionResponse
import dev.carbonpanel.data.SystemServiceInfo
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface Api {

    @POST("api/v1/pairing/claim")
    suspend fun claim(@Body body: ClaimRequest): ClaimResponse

    /**
     * Latest metrics.
     *
     * [fields] trims the payload to the sections actually being rendered — the
     * full snapshot is ~20 KB, cpu+memory is ~6 KB, and at a 0.4s poll that
     * difference is the whole mobile-data budget. [interval] tells the server
     * how fast this client intends to poll so the shared collector keeps up.
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

    @GET("api/v1/docker/containers")
    suspend fun containers(): List<ContainerInfo>

    @POST("api/v1/docker/containers/{id}/start")
    suspend fun startContainer(@Path("id") id: String): ActionResponse

    @POST("api/v1/docker/containers/{id}/stop")
    suspend fun stopContainer(@Path("id") id: String): ActionResponse

    @POST("api/v1/docker/containers/{id}/restart")
    suspend fun restartContainer(@Path("id") id: String): ActionResponse

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

    /** Cheap authenticated call used to decide whether an endpoint is alive. */
    @GET("api/v1/metrics/current")
    suspend fun ping(@Query("fields") fields: String = "cpu"): Response<Unit>
}

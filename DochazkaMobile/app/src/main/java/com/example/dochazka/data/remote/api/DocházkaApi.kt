package com.example.dochazka.data.remote.api

import com.example.dochazka.data.remote.dto.*
import retrofit2.Response
import retrofit2.http.*

interface DocházkaApi {

    // ========== Auth ==========

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<LoginResponse>

    // ========== Projects ==========

    @GET("projects")
    suspend fun getProjects(): Response<ProjectsResponse>

    @POST("projects")
    suspend fun createProject(@Body request: CreateProjectRequest): Response<ProjectDto>

    @DELETE("projects/{project_id}")
    suspend fun deleteProject(@Path("project_id") projectId: Int): Response<MessageResponse>

    // ========== Log Entries ==========

    @GET("logs")
    suspend fun getLogs(
        @Query("since") since: String? = null,
        @Query("project_id") projectId: Int? = null
    ): Response<LogsResponse>

    @POST("logs")
    suspend fun createLog(@Body request: CreateLogRequest): Response<LogEntryDto>

    @PUT("logs/{log_id}")
    suspend fun updateLog(
        @Path("log_id") logId: Int,
        @Body request: UpdateLogRequest
    ): Response<LogEntryDto>

    @DELETE("logs/{log_id}")
    suspend fun deleteLog(@Path("log_id") logId: Int): Response<MessageResponse>

    // ========== Active Log ==========

    @GET("logs/active")
    suspend fun getActiveLog(): Response<ActiveLogResponse>

    @POST("logs/start")
    suspend fun startWork(@Body request: StartWorkRequest): Response<LogEntryDto>

    @POST("logs/stop")
    suspend fun stopWork(): Response<LogEntryDto>

    // ========== Sync ==========

    @GET("sync/status")
    suspend fun getSyncStatus(): Response<SyncStatusResponse>
}

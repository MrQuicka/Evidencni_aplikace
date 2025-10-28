package com.example.dochazka.data.remote.dto

// ========== Auth DTOs ==========

data class LoginRequest(
    val username: String,
    val password: String
)

data class LoginResponse(
    val token: String,
    val user_id: Int,
    val username: String
)

data class RegisterRequest(
    val username: String,
    val password: String
)

// ========== Project DTOs ==========

data class ProjectDto(
    val id: Int,
    val name: String,
    val user_id: Int
)

data class ProjectsResponse(
    val projects: List<ProjectDto>
)

data class CreateProjectRequest(
    val name: String
)

// ========== Log Entry DTOs ==========

data class LogEntryDto(
    val id: Int? = null,
    val project_id: Int,
    val project_name: String? = null,
    val start_time: String,
    val end_time: String? = null,
    val pause_start: String? = null,
    val pause_end: String? = null,
    val note: String? = null
)

data class LogsResponse(
    val logs: List<LogEntryDto>,
    val timestamp: String
)

data class CreateLogRequest(
    val project_id: Int,
    val start_time: String,
    val end_time: String? = null,
    val pause_start: String? = null,
    val pause_end: String? = null,
    val note: String? = null
)

data class UpdateLogRequest(
    val project_id: Int? = null,
    val start_time: String? = null,
    val end_time: String? = null,
    val pause_start: String? = null,
    val pause_end: String? = null,
    val note: String? = null
)

data class ActiveLogResponse(
    val active_log: LogEntryDto?
)

data class StartWorkRequest(
    val project_id: Int,
    val note: String? = null
)

data class SyncStatusResponse(
    val status: String,
    val server_time: String,
    val user_id: Int
)

// ========== Generic DTOs ==========

data class ErrorResponse(
    val error: String
)

data class MessageResponse(
    val message: String
)

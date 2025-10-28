package com.example.dochazka.data.mappers

import com.example.dochazka.data.local.entities.LogEntryEntity
import com.example.dochazka.data.local.entities.ProjectEntity
import com.example.dochazka.data.local.entities.UserEntity
import com.example.dochazka.data.remote.dto.LogEntryDto
import com.example.dochazka.data.remote.dto.ProjectDto
import com.example.dochazka.domain.model.LogEntry
import com.example.dochazka.domain.model.Project
import com.example.dochazka.domain.model.User
import com.example.dochazka.domain.model.toEpochMilli
import com.example.dochazka.domain.model.toLocalDateTime
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

// ========== User Mappers ==========

fun UserEntity.toDomain(): User = User(
    id = id,
    username = username,
    token = token
)

fun User.toEntity(): UserEntity = UserEntity(
    id = id,
    username = username,
    token = token
)

// ========== Project Mappers ==========

fun ProjectEntity.toDomain(): Project = Project(
    id = id,
    name = name,
    userId = userId
)

fun Project.toEntity(isSynced: Boolean = true): ProjectEntity = ProjectEntity(
    id = id,
    name = name,
    userId = userId,
    isSynced = isSynced
)

fun ProjectDto.toEntity(userId: Int): ProjectEntity = ProjectEntity(
    id = id,
    name = name,
    userId = userId,
    isSynced = true
)

fun ProjectDto.toDomain(): Project = Project(
    id = id,
    name = name,
    userId = user_id
)

// ========== LogEntry Mappers ==========

fun LogEntryEntity.toDomain(projectName: String? = null): LogEntry = LogEntry(
    localId = localId,
    serverId = serverId,
    projectId = projectId,
    projectName = projectName,
    startTime = startTime.toLocalDateTime(),
    endTime = endTime?.toLocalDateTime(),
    pauseStart = pauseStart?.toLocalDateTime(),
    pauseEnd = pauseEnd?.toLocalDateTime(),
    note = note,
    isSynced = isSynced
)

fun LogEntry.toEntity(): LogEntryEntity = LogEntryEntity(
    localId = localId,
    serverId = serverId,
    projectId = projectId,
    startTime = startTime.toEpochMilli(),
    endTime = endTime?.toEpochMilli(),
    pauseStart = pauseStart?.toEpochMilli(),
    pauseEnd = pauseEnd?.toEpochMilli(),
    note = note,
    isSynced = isSynced,
    modifiedAt = System.currentTimeMillis()
)

fun LogEntryDto.toEntity(): LogEntryEntity {
    val formatter = DateTimeFormatter.ISO_DATE_TIME

    return LogEntryEntity(
        serverId = id,
        projectId = project_id,
        startTime = LocalDateTime.parse(start_time, formatter).toEpochMilli(),
        endTime = end_time?.let { LocalDateTime.parse(it, formatter).toEpochMilli() },
        pauseStart = pause_start?.let { LocalDateTime.parse(it, formatter).toEpochMilli() },
        pauseEnd = pause_end?.let { LocalDateTime.parse(it, formatter).toEpochMilli() },
        note = note,
        isSynced = true
    )
}

fun LogEntryDto.toDomain(): LogEntry {
    val formatter = DateTimeFormatter.ISO_DATE_TIME

    return LogEntry(
        localId = 0, // nepoužívá se pro DTO z serveru
        serverId = id,
        projectId = project_id,
        projectName = project_name,
        startTime = LocalDateTime.parse(start_time, formatter),
        endTime = end_time?.let { LocalDateTime.parse(it, formatter) },
        pauseStart = pause_start?.let { LocalDateTime.parse(it, formatter) },
        pauseEnd = pause_end?.let { LocalDateTime.parse(it, formatter) },
        note = note,
        isSynced = true
    )
}

fun LogEntry.toDto(): LogEntryDto {
    val formatter = DateTimeFormatter.ISO_DATE_TIME

    return LogEntryDto(
        id = serverId,
        project_id = projectId,
        project_name = projectName,
        start_time = startTime.format(formatter),
        end_time = endTime?.format(formatter),
        pause_start = pauseStart?.format(formatter),
        pause_end = pauseEnd?.format(formatter),
        note = note
    )
}

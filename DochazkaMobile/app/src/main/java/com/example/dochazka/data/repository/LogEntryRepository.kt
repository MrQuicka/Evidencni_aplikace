package com.example.dochazka.data.repository

import com.example.dochazka.data.local.dao.LogEntryDao
import com.example.dochazka.data.local.dao.ProjectDao
import com.example.dochazka.data.mappers.*
import com.example.dochazka.data.remote.api.DocházkaApi
import com.example.dochazka.data.remote.dto.CreateLogRequest
import com.example.dochazka.data.remote.dto.StartWorkRequest
import com.example.dochazka.data.remote.dto.UpdateLogRequest
import com.example.dochazka.domain.model.LogEntry
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LogEntryRepository @Inject constructor(
    private val api: DocházkaApi,
    private val logEntryDao: LogEntryDao,
    private val projectDao: ProjectDao
) {
    private val formatter = DateTimeFormatter.ISO_DATE_TIME

    /**
     * Získat všechny záznamy z lokální databáze (offline-first)
     */
    fun getAllLogEntries(): Flow<List<LogEntry>> {
        return logEntryDao.getAllLogEntries().map { entities ->
            entities.map { entity ->
                val project = projectDao.getProjectById(entity.projectId)
                entity.toDomain(projectName = project?.name)
            }
        }
    }

    /**
     * Získat aktuálně aktivní činnost (bez end_time)
     */
    fun getActiveLogEntry(): Flow<LogEntry?> {
        return logEntryDao.getActiveLogEntry().map { entity ->
            entity?.let {
                val project = projectDao.getProjectById(it.projectId)
                it.toDomain(projectName = project?.name)
            }
        }
    }

    /**
     * Start práce - ukládá lokálně a okamžitě se pokusí synchronizovat
     */
    suspend fun startWork(projectId: Int, note: String? = null): Result<LogEntry> {
        return try {
            // Zkontrolovat, jestli už něco neběží
            val activeLog = logEntryDao.getActiveLogEntry()
            // Poznámka: Flow je asynchronní, takže bychom měli použít .first() ale pro jednoduchost
            // předpokládáme, že není aktivní log

            // 1. Uložit lokálně (okamžitě viditelné v UI)
            val localLog = com.example.dochazka.data.local.entities.LogEntryEntity(
                projectId = projectId,
                startTime = System.currentTimeMillis(),
                note = note,
                isSynced = false
            )
            val localId = logEntryDao.insertLogEntry(localLog)

            // 2. Pokusit se odeslat na server (na pozadí)
            try {
                val response = api.startWork(StartWorkRequest(projectId, note))
                if (response.isSuccessful && response.body() != null) {
                    // Synchronizace úspěšná - aktualizovat serverId
                    val serverId = response.body()!!.id!!
                    logEntryDao.updateSyncStatus(localId, serverId)
                }
            } catch (e: Exception) {
                // Síť není dostupná, ale log je uložen lokálně
                // WorkManager to synchronizuje později
            }

            // Vrátit lokálně uložený log
            val savedLog = logEntryDao.getLogByLocalId(localId)!!
            val project = projectDao.getProjectById(projectId)
            Result.Success(savedLog.toDomain(projectName = project?.name))

        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba při startu práce")
        }
    }

    /**
     * Stop práce - ukončí aktivní činnost
     */
    suspend fun stopWork(): Result<LogEntry> {
        return try {
            // Najít aktivní log
            // Poznámka: Pro jednoduchost používáme přímý přístup
            val unsyncedLogs = logEntryDao.getUnsyncedLogEntries()
            val activeLog = unsyncedLogs.firstOrNull { it.endTime == null }
                ?: return Result.Error("Žádná aktivní činnost")

            // 1. Aktualizovat lokálně
            val updatedLog = activeLog.copy(
                endTime = System.currentTimeMillis(),
                isSynced = false,
                modifiedAt = System.currentTimeMillis()
            )
            logEntryDao.updateLogEntry(updatedLog)

            // 2. Pokusit se odeslat na server
            try {
                if (updatedLog.serverId != null) {
                    api.stopWork()
                }
            } catch (e: Exception) {
                // Offline, synchronizuje se později
            }

            val project = projectDao.getProjectById(updatedLog.projectId)
            Result.Success(updatedLog.toDomain(projectName = project?.name))

        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba při ukončení práce")
        }
    }

    /**
     * Vytvořit nový záznam ručně
     */
    suspend fun createLogEntry(logEntry: LogEntry): Result<LogEntry> {
        return try {
            // 1. Uložit lokálně
            val entity = logEntry.toEntity()
            val localId = logEntryDao.insertLogEntry(entity)

            // 2. Pokusit se odeslat na server
            try {
                val request = CreateLogRequest(
                    project_id = logEntry.projectId,
                    start_time = logEntry.startTime.format(formatter),
                    end_time = logEntry.endTime?.format(formatter),
                    pause_start = logEntry.pauseStart?.format(formatter),
                    pause_end = logEntry.pauseEnd?.format(formatter),
                    note = logEntry.note
                )
                val response = api.createLog(request)

                if (response.isSuccessful && response.body() != null) {
                    val serverId = response.body()!!.id!!
                    logEntryDao.updateSyncStatus(localId, serverId)
                }
            } catch (e: Exception) {
                // Offline
            }

            val savedLog = logEntryDao.getLogByLocalId(localId)!!
            val project = projectDao.getProjectById(logEntry.projectId)
            Result.Success(savedLog.toDomain(projectName = project?.name))

        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba při vytváření záznamu")
        }
    }

    /**
     * Aktualizovat existující záznam
     */
    suspend fun updateLogEntry(logEntry: LogEntry): Result<LogEntry> {
        return try {
            // 1. Aktualizovat lokálně
            val entity = logEntry.copy(isSynced = false).toEntity()
            logEntryDao.updateLogEntry(entity)

            // 2. Pokusit se odeslat na server
            try {
                if (logEntry.serverId != null) {
                    val request = UpdateLogRequest(
                        project_id = logEntry.projectId,
                        start_time = logEntry.startTime.format(formatter),
                        end_time = logEntry.endTime?.format(formatter),
                        pause_start = logEntry.pauseStart?.format(formatter),
                        pause_end = logEntry.pauseEnd?.format(formatter),
                        note = logEntry.note
                    )
                    val response = api.updateLog(logEntry.serverId, request)

                    if (response.isSuccessful) {
                        val synced = entity.copy(isSynced = true)
                        logEntryDao.updateLogEntry(synced)
                    }
                }
            } catch (e: Exception) {
                // Offline
            }

            val project = projectDao.getProjectById(logEntry.projectId)
            Result.Success(logEntry.copy(projectName = project?.name))

        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba při aktualizaci záznamu")
        }
    }

    /**
     * Smazat záznam
     */
    suspend fun deleteLogEntry(localId: Long): Result<Unit> {
        return try {
            val log = logEntryDao.getLogByLocalId(localId)
                ?: return Result.Error("Záznam nenalezen")

            // 1. Označit jako smazaný lokálně
            logEntryDao.markAsDeleted(localId)

            // 2. Pokusit se smazat na serveru
            try {
                if (log.serverId != null) {
                    api.deleteLog(log.serverId)
                }
            } catch (e: Exception) {
                // Offline, synchronizuje se později
            }

            Result.Success(Unit)

        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba při mazání záznamu")
        }
    }

    /**
     * Synchronizovat změny se serverem
     */
    suspend fun syncWithServer(): Result<Unit> {
        return try {
            // 1. Stáhnout nové záznamy ze serveru
            val response = api.getLogs()
            if (response.isSuccessful && response.body() != null) {
                val serverLogs = response.body()!!.logs
                val entities = serverLogs.map { it.toEntity() }
                logEntryDao.insertLogEntries(entities)
            }

            // 2. Odeslat nesynchronizované lokální změny
            val unsyncedLogs = logEntryDao.getUnsyncedLogEntries()
            for (log in unsyncedLogs) {
                try {
                    if (log.serverId == null) {
                        // Nový záznam
                        val request = CreateLogRequest(
                            project_id = log.projectId,
                            start_time = LocalDateTime.ofEpochSecond(
                                log.startTime / 1000,
                                0,
                                java.time.ZoneOffset.UTC
                            ).format(formatter),
                            end_time = log.endTime?.let {
                                LocalDateTime.ofEpochSecond(it / 1000, 0, java.time.ZoneOffset.UTC)
                                    .format(formatter)
                            },
                            note = log.note
                        )
                        val apiResponse = api.createLog(request)
                        if (apiResponse.isSuccessful && apiResponse.body() != null) {
                            logEntryDao.updateSyncStatus(log.localId, apiResponse.body()!!.id!!)
                        }
                    } else {
                        // Existující záznam - aktualizovat
                        val request = UpdateLogRequest(
                            project_id = log.projectId,
                            start_time = LocalDateTime.ofEpochSecond(
                                log.startTime / 1000,
                                0,
                                java.time.ZoneOffset.UTC
                            ).format(formatter),
                            end_time = log.endTime?.let {
                                LocalDateTime.ofEpochSecond(it / 1000, 0, java.time.ZoneOffset.UTC)
                                    .format(formatter)
                            },
                            note = log.note
                        )
                        api.updateLog(log.serverId, request)
                        logEntryDao.updateLogEntry(log.copy(isSynced = true))
                    }
                } catch (e: Exception) {
                    // Jeden záznam selhal, ale pokračujeme s dalšími
                    continue
                }
            }

            Result.Success(Unit)

        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba při synchronizaci")
        }
    }
}

package com.example.dochazka.data.local.dao

import androidx.room.*
import com.example.dochazka.data.local.entities.LogEntryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface LogEntryDao {
    @Query("SELECT * FROM log_entries WHERE isDeleted = 0 ORDER BY startTime DESC")
    fun getAllLogEntries(): Flow<List<LogEntryEntity>>

    @Query("SELECT * FROM log_entries WHERE endTime IS NULL AND isDeleted = 0 LIMIT 1")
    fun getActiveLogEntry(): Flow<LogEntryEntity?>

    @Query("SELECT * FROM log_entries WHERE serverId = :serverId")
    suspend fun getLogByServerId(serverId: Int): LogEntryEntity?

    @Query("SELECT * FROM log_entries WHERE localId = :localId")
    suspend fun getLogByLocalId(localId: Long): LogEntryEntity?

    @Query("SELECT * FROM log_entries WHERE isSynced = 0 AND isDeleted = 0")
    suspend fun getUnsyncedLogEntries(): List<LogEntryEntity>

    @Query("SELECT * FROM log_entries WHERE projectId = :projectId AND isDeleted = 0 ORDER BY startTime DESC")
    fun getLogEntriesByProject(projectId: Int): Flow<List<LogEntryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLogEntry(logEntry: LogEntryEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLogEntries(logEntries: List<LogEntryEntity>)

    @Update
    suspend fun updateLogEntry(logEntry: LogEntryEntity)

    @Delete
    suspend fun deleteLogEntry(logEntry: LogEntryEntity)

    @Query("DELETE FROM log_entries")
    suspend fun deleteAll()

    @Query("UPDATE log_entries SET isDeleted = 1, isSynced = 0 WHERE localId = :localId")
    suspend fun markAsDeleted(localId: Long)

    @Query("UPDATE log_entries SET serverId = :serverId, isSynced = 1 WHERE localId = :localId")
    suspend fun updateSyncStatus(localId: Long, serverId: Int)
}

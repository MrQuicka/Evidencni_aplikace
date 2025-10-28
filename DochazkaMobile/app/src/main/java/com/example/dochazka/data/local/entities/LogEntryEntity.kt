package com.example.dochazka.data.local.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "log_entries")
data class LogEntryEntity(
    @PrimaryKey(autoGenerate = true)
    val localId: Long = 0,
    val serverId: Int? = null, // null pokud ještě není na serveru
    val projectId: Int,
    val startTime: Long, // timestamp v milisekundách
    val endTime: Long? = null,
    val pauseStart: Long? = null,
    val pauseEnd: Long? = null,
    val note: String? = null,
    val isSynced: Boolean = false,
    val isDeleted: Boolean = false,
    val modifiedAt: Long = System.currentTimeMillis()
)

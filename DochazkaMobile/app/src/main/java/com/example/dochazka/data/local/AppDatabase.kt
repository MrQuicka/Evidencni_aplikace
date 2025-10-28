package com.example.dochazka.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.example.dochazka.data.local.dao.LogEntryDao
import com.example.dochazka.data.local.dao.ProjectDao
import com.example.dochazka.data.local.dao.UserDao
import com.example.dochazka.data.local.entities.LogEntryEntity
import com.example.dochazka.data.local.entities.ProjectEntity
import com.example.dochazka.data.local.entities.UserEntity

@Database(
    entities = [
        UserEntity::class,
        ProjectEntity::class,
        LogEntryEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
    abstract fun projectDao(): ProjectDao
    abstract fun logEntryDao(): LogEntryDao

    companion object {
        const val DATABASE_NAME = "dochazka_db"
    }
}

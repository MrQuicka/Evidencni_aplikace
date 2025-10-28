package com.example.dochazka.di

import android.content.Context
import androidx.room.Room
import com.example.dochazka.data.local.AppDatabase
import com.example.dochazka.data.local.dao.LogEntryDao
import com.example.dochazka.data.local.dao.ProjectDao
import com.example.dochazka.data.local.dao.UserDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            AppDatabase.DATABASE_NAME
        )
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    fun provideUserDao(database: AppDatabase): UserDao {
        return database.userDao()
    }

    @Provides
    fun provideProjectDao(database: AppDatabase): ProjectDao {
        return database.projectDao()
    }

    @Provides
    fun provideLogEntryDao(database: AppDatabase): LogEntryDao {
        return database.logEntryDao()
    }
}

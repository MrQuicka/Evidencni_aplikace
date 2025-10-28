package com.example.dochazka.data.local.dao

import androidx.room.*
import com.example.dochazka.data.local.entities.ProjectEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ProjectDao {
    @Query("SELECT * FROM projects WHERE isDeleted = 0 ORDER BY name ASC")
    fun getAllProjects(): Flow<List<ProjectEntity>>

    @Query("SELECT * FROM projects WHERE id = :projectId")
    suspend fun getProjectById(projectId: Int): ProjectEntity?

    @Query("SELECT * FROM projects WHERE isSynced = 0 AND isDeleted = 0")
    suspend fun getUnsyncedProjects(): List<ProjectEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProject(project: ProjectEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProjects(projects: List<ProjectEntity>)

    @Update
    suspend fun updateProject(project: ProjectEntity)

    @Delete
    suspend fun deleteProject(project: ProjectEntity)

    @Query("DELETE FROM projects")
    suspend fun deleteAll()

    @Query("UPDATE projects SET isDeleted = 1, isSynced = 0 WHERE id = :projectId")
    suspend fun markAsDeleted(projectId: Int)
}

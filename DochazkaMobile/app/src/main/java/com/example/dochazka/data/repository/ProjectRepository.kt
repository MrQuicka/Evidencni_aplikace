package com.example.dochazka.data.repository

import com.example.dochazka.data.local.dao.ProjectDao
import com.example.dochazka.data.local.dao.UserDao
import com.example.dochazka.data.mappers.toDomain
import com.example.dochazka.data.mappers.toEntity
import com.example.dochazka.data.remote.api.DocházkaApi
import com.example.dochazka.data.remote.dto.CreateProjectRequest
import com.example.dochazka.domain.model.Project
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProjectRepository @Inject constructor(
    private val api: DocházkaApi,
    private val projectDao: ProjectDao,
    private val userDao: UserDao
) {
    fun getAllProjects(): Flow<List<Project>> {
        return projectDao.getAllProjects().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    suspend fun createProject(name: String): Result<Project> {
        return try {
            val user = userDao.getCurrentUser().first()
                ?: return Result.Error("Uživatel není přihlášen")

            val response = api.createProject(CreateProjectRequest(name))

            if (response.isSuccessful && response.body() != null) {
                val projectDto = response.body()!!
                val entity = projectDto.toEntity(user.id)
                projectDao.insertProject(entity)

                Result.Success(entity.toDomain())
            } else {
                Result.Error("Chyba při vytváření projektu")
            }
        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba připojení")
        }
    }

    suspend fun syncProjects(): Result<Unit> {
        return try {
            val response = api.getProjects()

            if (response.isSuccessful && response.body() != null) {
                val user = userDao.getCurrentUser().first()
                    ?: return Result.Error("Uživatel není přihlášen")

                val projects = response.body()!!.projects
                val entities = projects.map { it.toEntity(user.id) }
                projectDao.insertProjects(entities)

                Result.Success(Unit)
            } else {
                Result.Error("Chyba při synchronizaci projektů")
            }
        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba připojení")
        }
    }
}

package com.example.dochazka.data.repository

import com.example.dochazka.data.local.dao.UserDao
import com.example.dochazka.data.local.entities.UserEntity
import com.example.dochazka.data.mappers.toDomain
import com.example.dochazka.data.remote.api.DocházkaApi
import com.example.dochazka.data.remote.dto.LoginRequest
import com.example.dochazka.data.remote.dto.RegisterRequest
import com.example.dochazka.domain.model.User
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String) : Result<Nothing>()
    object Loading : Result<Nothing>()
}

@Singleton
class AuthRepository @Inject constructor(
    private val api: DocházkaApi,
    private val userDao: UserDao
) {
    val currentUser: Flow<User?> = userDao.getCurrentUser().map { it?.toDomain() }

    suspend fun login(username: String, password: String): Result<User> {
        return try {
            val response = api.login(LoginRequest(username, password))

            if (response.isSuccessful && response.body() != null) {
                val loginResponse = response.body()!!
                val user = UserEntity(
                    id = loginResponse.user_id,
                    username = loginResponse.username,
                    token = loginResponse.token
                )

                // Uložit do lokální databáze
                userDao.deleteAll()
                userDao.insertUser(user)

                Result.Success(user.toDomain())
            } else {
                Result.Error("Neplatné přihlašovací údaje")
            }
        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba připojení k serveru")
        }
    }

    suspend fun register(username: String, password: String): Result<User> {
        return try {
            val response = api.register(RegisterRequest(username, password))

            if (response.isSuccessful && response.body() != null) {
                val registerResponse = response.body()!!
                val user = UserEntity(
                    id = registerResponse.user_id,
                    username = registerResponse.username,
                    token = registerResponse.token
                )

                userDao.deleteAll()
                userDao.insertUser(user)

                Result.Success(user.toDomain())
            } else {
                Result.Error("Uživatel s tímto jménem již existuje")
            }
        } catch (e: Exception) {
            Result.Error(e.message ?: "Chyba připojení k serveru")
        }
    }

    suspend fun logout() {
        userDao.deleteAll()
    }

    suspend fun getToken(): String? {
        return userDao.getCurrentUser().map { it?.token }.toString()
    }
}

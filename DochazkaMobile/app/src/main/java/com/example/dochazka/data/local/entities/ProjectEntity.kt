package com.example.dochazka.data.local.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "projects")
data class ProjectEntity(
    @PrimaryKey
    val id: Int,
    val name: String,
    val userId: Int,
    val isSynced: Boolean = true,
    val isDeleted: Boolean = false
)

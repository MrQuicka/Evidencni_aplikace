package com.example.dochazka.presentation.logging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.dochazka.data.repository.LogEntryRepository
import com.example.dochazka.data.repository.ProjectRepository
import com.example.dochazka.domain.model.LogEntry
import com.example.dochazka.domain.model.Project
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoggingUiState(
    val projects: List<Project> = emptyList(),
    val logEntries: List<LogEntry> = emptyList(),
    val activeLog: LogEntry? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class LoggingViewModel @Inject constructor(
    private val logEntryRepository: LogEntryRepository,
    private val projectRepository: ProjectRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoggingUiState())
    val uiState: StateFlow<LoggingUiState> = _uiState

    init {
        loadData()
    }

    private fun loadData() {
        viewModelScope.launch {
            // Načíst projekty
            projectRepository.getAllProjects().collect { projects ->
                _uiState.update { it.copy(projects = projects) }
            }
        }

        viewModelScope.launch {
            // Načíst záznamy
            logEntryRepository.getAllLogEntries().collect { logs ->
                _uiState.update { it.copy(logEntries = logs) }
            }
        }

        viewModelScope.launch {
            // Načíst aktivní log
            logEntryRepository.getActiveLogEntry().collect { activeLog ->
                _uiState.update { it.copy(activeLog = activeLog) }
            }
        }

        // Synchronizovat se serverem
        viewModelScope.launch {
            projectRepository.syncProjects()
            logEntryRepository.syncWithServer()
        }
    }

    fun startWork(projectId: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            logEntryRepository.startWork(projectId)
            _uiState.update { it.copy(isLoading = false) }
        }
    }

    fun stopWork() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            logEntryRepository.stopWork()
            _uiState.update { it.copy(isLoading = false) }
        }
    }
}

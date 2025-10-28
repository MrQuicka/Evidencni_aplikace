package com.example.dochazka.presentation.logging

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.dochazka.domain.model.LogEntry
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoggingScreen(
    onLogout: () -> Unit,
    viewModel: LoggingViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Docházka") },
                actions = {
                    TextButton(onClick = onLogout) {
                        Text("Odhlásit")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
        ) {
            // Aktivní činnost
            if (uiState.activeLog != null) {
                ActiveLogCard(
                    logEntry = uiState.activeLog!!,
                    onStop = { viewModel.stopWork() }
                )
            } else {
                StartWorkCard(
                    projects = uiState.projects,
                    onStart = { projectId -> viewModel.startWork(projectId) }
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Historie",
                style = MaterialTheme.typography.headlineSmall
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Historie záznamů
            LazyColumn {
                items(uiState.logEntries) { logEntry ->
                    LogEntryItem(logEntry = logEntry)
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
fun ActiveLogCard(
    logEntry: LogEntry,
    onStop: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "Právě probíhá",
                style = MaterialTheme.typography.labelLarge
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = logEntry.projectName ?: "Projekt #${logEntry.projectId}",
                style = MaterialTheme.typography.headlineSmall
            )
            Text(
                text = "Začátek: ${logEntry.startTime.format(DateTimeFormatter.ofPattern("HH:mm"))}",
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(16.dp))
            Button(
                onClick = onStop,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Ukončit práci")
            }
        }
    }
}

@Composable
fun StartWorkCard(
    projects: List<com.example.dochazka.domain.model.Project>,
    onStart: (Int) -> Unit
) {
    var selectedProjectId by remember { mutableStateOf<Int?>(null) }
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "Začít práci",
                style = MaterialTheme.typography.headlineSmall
            )

            Spacer(modifier = Modifier.height(16.dp))

            ExposedDropdownMenuBox(
                expanded = expanded,
                onExpandedChange = { expanded = !expanded }
            ) {
                OutlinedTextField(
                    value = projects.find { it.id == selectedProjectId }?.name ?: "Vyber projekt",
                    onValueChange = {},
                    readOnly = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor(),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) }
                )

                ExposedDropdownMenu(
                    expanded = expanded,
                    onDismissRequest = { expanded = false }
                ) {
                    projects.forEach { project ->
                        DropdownMenuItem(
                            text = { Text(project.name) },
                            onClick = {
                                selectedProjectId = project.id
                                expanded = false
                            }
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = { selectedProjectId?.let { onStart(it) } },
                enabled = selectedProjectId != null,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Začít")
            }
        }
    }
}

@Composable
fun LogEntryItem(logEntry: LogEntry) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(
                    text = logEntry.projectName ?: "Projekt #${logEntry.projectId}",
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = "${logEntry.startTime.format(DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm"))}",
                    style = MaterialTheme.typography.bodySmall
                )
                if (logEntry.endTime != null) {
                    Text(
                        text = "Ukončeno: ${logEntry.endTime.format(DateTimeFormatter.ofPattern("HH:mm"))}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            if (logEntry.getTotalHours() != null) {
                Text(
                    text = String.format("%.2f h", logEntry.getTotalHours()),
                    style = MaterialTheme.typography.titleLarge
                )
            } else {
                Text(
                    text = "Běží...",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

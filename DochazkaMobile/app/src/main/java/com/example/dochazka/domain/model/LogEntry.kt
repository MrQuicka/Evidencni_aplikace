package com.example.dochazka.domain.model

import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds

data class LogEntry(
    val localId: Long,
    val serverId: Int?,
    val projectId: Int,
    val projectName: String? = null,
    val startTime: LocalDateTime,
    val endTime: LocalDateTime? = null,
    val pauseStart: LocalDateTime? = null,
    val pauseEnd: LocalDateTime? = null,
    val note: String? = null,
    val isSynced: Boolean = false
) {
    /**
     * Vypočítá celkový odpracovaný čas (včetně odečtení pauzy)
     */
    fun getTotalDuration(): Duration? {
        if (endTime == null) return null

        val start = startTime.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
        val end = endTime.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()

        var totalMillis = end - start

        // Odečíst pauzu
        if (pauseStart != null && pauseEnd != null) {
            val pauseStartMillis = pauseStart.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
            val pauseEndMillis = pauseEnd.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
            totalMillis -= (pauseEndMillis - pauseStartMillis)
        }

        return totalMillis.milliseconds
    }

    /**
     * Vrátí čas v hodinách s přesností na dvě desetinná místa
     */
    fun getTotalHours(): Double? {
        val duration = getTotalDuration() ?: return null
        return duration.inWholeMinutes / 60.0
    }

    /**
     * Jestli právě běží (nemá end_time)
     */
    fun isActive(): Boolean = endTime == null

    /**
     * Jestli je právě v pauze
     */
    fun isOnPause(): Boolean = pauseStart != null && pauseEnd == null
}

/**
 * Helper pro konverzi mezi Long timestamp a LocalDateTime
 */
fun Long.toLocalDateTime(): LocalDateTime =
    LocalDateTime.ofInstant(Instant.ofEpochMilli(this), ZoneId.systemDefault())

fun LocalDateTime.toEpochMilli(): Long =
    this.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()

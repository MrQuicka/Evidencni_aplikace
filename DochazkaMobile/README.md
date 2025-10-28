# Docházka - Mobilní aplikace pro Android

Mobilní aplikace pro evidenci docházky s podporou offline režimu a automatickou synchronizací.

## 📱 Funkce

- ✅ **Přihlášení pomocí JWT tokenu**
- ✅ **Offline-first architektura** - aplikace funguje i bez připojení k internetu
- ✅ **Automatická synchronizace** - změny se automaticky nahrají na server
- ✅ **Start/Stop práce** - jednoduché tlačítko pro začátek a konec pracovní doby
- ✅ **Historie záznamů** - přehled všech pracovních záznamů
- ✅ **Výběr projektu** - možnost vybrat projekt, na kterém pracujete
- ✅ **Realtime aktualizace** (pomocí polling každých 30s)

---

## 🏗️ Architektura

Aplikace je postavena na moderní Android architektuře:

```
┌─────────────────────────────────────────┐
│     UI Layer (Jetpack Compose)          │
│  - LoginScreen, LoggingScreen           │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│       ViewModel Layer (MVVM)             │
│  - LoginViewModel, LoggingViewModel      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│         Repository Layer                 │
│  - AuthRepository, LogEntryRepository    │
│  - Offline-first strategie              │
└──────┬────────────────────┬─────────────┘
       │                    │
┌──────▼────────┐    ┌─────▼──────────┐
│  Remote DS    │    │   Local DS     │
│  (Retrofit)   │    │  (Room DB)     │
└───────────────┘    └────────────────┘
```

### Použité technologie

- **Kotlin** - programovací jazyk
- **Jetpack Compose** - moderní UI framework
- **Room** - lokální databáze
- **Retrofit** - HTTP klient pro komunikaci s API
- **Hilt** - dependency injection
- **Coroutines + Flow** - asynchronní programování
- **MVVM** - architektonický pattern

---

## 🚀 Instalace a spuštění

### Předpoklady

1. **Android Studio** (nejnovější verze)
2. **JDK 17+**
3. **Android SDK** (API 24+)
4. **Běžící Flask backend** s REST API (viz dokumentace v hlavním projektu)

### Krok 1: Nastavení projektu

1. Otevřete Android Studio
2. `File` → `Open` → vyberte složku `DochazkaMobile`
3. Počkejte, než se stáhnou všechny dependencies

### Krok 2: Konfigurace API URL

V souboru `app/build.gradle.kts` najděte řádek:

```kotlin
buildConfigField("String", "API_BASE_URL", "\"https://your-cloudflare-tunnel.com/api/mobile/\"")
```

**Změňte URL na adresu vašeho Cloudflare tunelu:**

```kotlin
buildConfigField("String", "API_BASE_URL", "\"https://vase-domena.trycloudflare.com/api/mobile/\"")
```

### Krok 3: Build a spuštění

1. Připojte Android zařízení nebo spusťte emulátor
2. Klikněte na zelené tlačítko "Run" (Shift+F10)
3. Aplikace se nainstaluje a spustí

---

## 🔧 Jak to funguje

### Offline-First Architektura

Aplikace používá **offline-first** přístup, což znamená:

1. **Všechna data se ukládají nejdřív lokálně** do Room databáze
2. **UI se okamžitě aktualizuje** z lokálních dat
3. **Na pozadí se pokusí synchronizovat** se serverem
4. **Pokud síť není dostupná**, změny zůstanou v lokální databázi jako "nesynchronizované"
5. **Když se obnoví spojení**, WorkManager automaticky odešle všechny změny na server

### Příklad: Start práce

```kotlin
suspend fun startWork(projectId: Int, note: String?): Result<LogEntry> {
    // 1. Uložit lokálně (okamžitě viditelné v UI)
    val localLog = LogEntryEntity(
        projectId = projectId,
        startTime = System.currentTimeMillis(),
        note = note,
        isSynced = false // označeno jako nesynchronizované
    )
    val localId = logEntryDao.insertLogEntry(localLog)

    // 2. Pokusit se odeslat na server
    try {
        val response = api.startWork(StartWorkRequest(projectId, note))
        if (response.isSuccessful) {
            // Synchronizace úspěšná
            logEntryDao.updateSyncStatus(localId, response.body()!!.id!!)
        }
    } catch (e: Exception) {
        // Offline - WorkManager to synchronizuje později
    }

    return Result.Success(localLog.toDomain())
}
```

### Synchronizace

Synchronizace probíhá dvěma způsoby:

1. **Manuální**: Při otevření aplikace nebo pull-to-refresh
2. **Automatická**: WorkManager každých 15 minut (můžete upravit)

```kotlin
// SyncWorker.kt (TODO: implementovat)
class SyncWorker : CoroutineWorker() {
    override suspend fun doWork(): Result {
        val unsyncedLogs = logEntryDao.getUnsyncedLogEntries()

        for (log in unsyncedLogs) {
            try {
                api.createLog(log.toRequest())
                logEntryDao.markAsSynced(log.id)
            } catch (e: Exception) {
                // Zkusíme příště
            }
        }

        return Result.success()
    }
}
```

---

## 📁 Struktura projektu

```
app/src/main/java/com/example/dochazka/
├── data/
│   ├── local/
│   │   ├── dao/              # Data Access Objects (SQL queries)
│   │   ├── entities/         # Room databázové entity
│   │   └── AppDatabase.kt    # Room databáze
│   ├── remote/
│   │   ├── api/              # Retrofit API interface
│   │   └── dto/              # Data Transfer Objects (JSON)
│   ├── repository/           # Repository pattern (koordinace API + DB)
│   └── mappers/              # Převody mezi DTO/Entity/Domain
├── domain/
│   └── model/                # Business objekty (čistá data)
├── presentation/
│   ├── login/                # Login obrazovka
│   ├── logging/              # Hlavní obrazovka (start/stop)
│   ├── navigation/           # Navigation
│   └── theme/                # Material Design 3 theme
└── di/                       # Hilt DI moduly
```

---

## 🔐 Bezpečnost

### JWT Token

- Token se ukládá v Room databázi (lokálně)
- Automaticky se přidává do každého API requestu přes OkHttp Interceptor
- Token je platný **7 dní**, pak je potřeba se přihlásit znovu

```kotlin
// NetworkModule.kt
val authInterceptor = Interceptor { chain ->
    val token = userDao.getCurrentUser().first()?.token

    val newRequest = if (token != null) {
        chain.request().newBuilder()
            .addHeader("Authorization", "Bearer $token")
            .build()
    } else {
        chain.request()
    }

    chain.proceed(newRequest)
}
```

### SSL/HTTPS

- **DŮLEŽITÉ**: Použijte HTTPS pro Cloudflare tunnel
- V produkci zvažte SSL pinning pro větší bezpečnost

---

## 📊 Datové modely

### LogEntry (Záznam docházky)

```kotlin
data class LogEntry(
    val localId: Long,              // Lokální ID (Room)
    val serverId: Int?,             // ID na serveru (null pokud není sync)
    val projectId: Int,
    val startTime: LocalDateTime,
    val endTime: LocalDateTime?,
    val pauseStart: LocalDateTime?,
    val pauseEnd: LocalDateTime?,
    val note: String?,
    val isSynced: Boolean           // true = synchronizováno se serverem
)
```

### Project

```kotlin
data class Project(
    val id: Int,
    val name: String,
    val userId: Int
)
```

---

## 🔄 API Endpointy

Kompletní dokumentace API je v souboru `API_DOCUMENTATION.md` v hlavním projektu.

Základní endpointy:

- `POST /api/mobile/auth/login` - Přihlášení
- `GET /api/mobile/projects` - Získat projekty
- `GET /api/mobile/logs` - Získat záznamy
- `POST /api/mobile/logs/start` - Začít práci
- `POST /api/mobile/logs/stop` - Ukončit práci
- `GET /api/mobile/sync/status` - Kontrola spojení

---

## 🐛 Testování offline režimu

### V emulátoru

1. Otevřete Extended Controls (tři tečky)
2. Cellular → Data status → Denied

### Na fyzickém zařízení

1. Zapněte režim letadla
2. Vyzkoušejte vytvořit záznam
3. Zkontrolujte, že je viditelný v UI
4. Vypněte režim letadla
5. Aplikace by měla automaticky synchronizovat

---

## 🔮 Budoucí vylepšení (TODO)

- [ ] **WorkManager** pro automatickou synchronizaci na pozadí
- [ ] **Pull-to-refresh** pro manuální synchronizaci
- [ ] **Notifikace** při úspěšné/neúspěšné synchronizaci
- [ ] **Export do PDF** přímo z mobilu
- [ ] **Statistiky** (grafy, odpracované hodiny atd.)
- [ ] **Dark mode**
- [ ] **Widget** na domovskou obrazovku
- [ ] **Biometrické přihlášení**
- [ ] **Geofencing** (automatický start při příchodu do práce)

---

## ❓ Časté problémy

### Aplikace se nespustí

1. Zkontrolujte, že máte JDK 17+
2. `Build` → `Clean Project` a pak `Rebuild Project`
3. Invalidate caches: `File` → `Invalidate Caches / Restart`

### Nefunguje připojení k API

1. Zkontrolujte URL v `build.gradle.kts`
2. Ujistěte se, že backend běží a je dostupný
3. Zkontrolujte v Logcatu chybové hlášky (filtrujte "okhttp")

### Databáze je prázdná po restartu

- To je normální, při každé změně schématu se databáze maže (`fallbackToDestructiveMigration`)
- V produkci byste měli implementovat migrace

---

## 📝 Licence

Tento projekt je vytvořen jako semestrální projekt.

---

## 👨‍💻 Autor

Student - Semestrální projekt

---

## 🙏 Poděkování

- Android Developers dokumentace
- Jetpack Compose samples
- Stack Overflow komunita

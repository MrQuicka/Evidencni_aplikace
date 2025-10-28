# 🚀 Rychlý návod - Jak spustit mobilní aplikaci

Tento dokument obsahuje krok-za-krokem návod, jak celý projekt (Flask backend + Android app) zprovoznit.

---

## 📋 Předpoklady

### Pro Flask Backend:
- Python 3.8+
- MySQL nebo MariaDB databáze
- pip

### Pro Android Aplikaci:
- Android Studio (nejnovější verze)
- JDK 17+
- Android SDK (API 24+)

---

## 🔧 Část 1: Nastavení Flask Backendu

### Krok 1: Instalace dependencies

```bash
cd Evidencni_aplikace
pip install -r requirements.txt
```

### Krok 2: Nastavení databáze

Ujistěte se, že máte běžící MySQL/MariaDB. Pokud používáte Docker:

```bash
docker run -d \
  --name dochazka-db \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=dochazka \
  -e MYSQL_USER=dochazka_user \
  -e MYSQL_PASSWORD=dochazka_pass \
  -p 3306:3306 \
  mysql:8
```

### Krok 3: Inicializace databáze

```bash
python manage.py db init
python manage.py db migrate
python manage.py db upgrade
```

Nebo jednoduše spusťte aplikaci, která databázi vytvoří automaticky:

```bash
python app.py
```

### Krok 4: Test API

Ověřte, že REST API funguje:

```bash
# Test přihlášení
curl -X POST http://localhost:5000/api/mobile/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Mělo by vrátit JWT token
```

---

## 🌐 Část 2: Zpřístupnění přes Cloudflare Tunnel

### Krok 1: Instalace Cloudflared

**Linux/Mac:**
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

**Windows:**
Stáhněte z: https://github.com/cloudflare/cloudflared/releases

### Krok 2: Spuštění tunelu

```bash
cloudflared tunnel --url http://localhost:5000
```

**Výstup bude vypadat takto:**
```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://random-words-1234.trycloudflare.com                                               |
+--------------------------------------------------------------------------------------------+
```

**Tuto URL si poznamenejte** - budete ji potřebovat pro Android aplikaci!

### Krok 3: Test přes tunel

```bash
curl https://vase-random-url.trycloudflare.com/api/mobile/sync/status
```

Poznámka: První request může být pomalejší kvůli inicializaci tunelu.

---

## 📱 Část 3: Android Aplikace

### Krok 1: Otevření projektu

1. Spusťte Android Studio
2. `File` → `Open`
3. Vyberte složku `Evidencni_aplikace/DochazkaMobile`
4. Počkejte na stažení dependencies (může trvat několik minut)

### Krok 2: Konfigurace API URL

Otevřete soubor:
```
DochazkaMobile/app/build.gradle.kts
```

Najděte řádek (cca řádek 23):
```kotlin
buildConfigField("String", "API_BASE_URL", "\"https://your-cloudflare-tunnel.com/api/mobile/\"")
```

**Změňte na vaši Cloudflare URL:**
```kotlin
buildConfigField("String", "API_BASE_URL", "\"https://random-words-1234.trycloudflare.com/api/mobile/\"")
```

⚠️ **Důležité**:
- Nezapomeňte `/api/mobile/` na konci!
- URL musí být v uvozovkách a escapovaná (`\"`)

### Krok 3: Sync Gradle

Po změně v `build.gradle.kts` klikněte na:
```
File → Sync Project with Gradle Files
```

### Krok 4: Spuštění aplikace

**A) Pomocí emulátoru:**
1. `Tools` → `Device Manager`
2. Vytvořte nové virtuální zařízení (např. Pixel 6 s Android 13)
3. Spusťte emulátor
4. Klikněte na zelenou šipku "Run" (Shift+F10)

**B) Pomocí fyzického zařízení:**
1. Zapněte USB debugging na telefonu
2. Připojte telefon k počítači
3. Vyberte zařízení v Android Studio
4. Klikněte na "Run"

### Krok 5: První přihlášení

- **Username**: `admin`
- **Password**: `admin`

(Tyto credentials jsou automaticky vytvořeny při prvním spuštění Flask aplikace)

---

## ✅ Ověření, že vše funguje

### 1. Test přihlášení
- Otevřete aplikaci
- Přihlaste se jako admin/admin
- Měli byste se dostat na hlavní obrazovku

### 2. Test offline režimu
- Zapněte režim letadla
- Zkuste začít práci na projektu
- Mělo by to fungovat (data se uloží lokálně)
- Vypněte režim letadla
- Data by se měla automaticky synchronizovat

### 3. Test synchronizace
- Vytvořte záznam v mobilní aplikaci
- Otevřete webovou verzi na `http://localhost:5000/logs`
- Měli byste vidět stejný záznam

---

## 🐛 Řešení problémů

### Backend nefunguje

**Chyba: `ModuleNotFoundError: No module named 'flask_cors'`**

Řešení:
```bash
pip install Flask-CORS PyJWT
```

**Chyba: `Can't connect to MySQL server`**

Řešení:
1. Zkontrolujte, že MySQL běží: `systemctl status mysql` (Linux) nebo Task Manager (Windows)
2. Zkontrolujte credentials v `app.py` (řádek 41)

### Cloudflare tunel nefunguje

**Chyba: `ERR_CONNECTION_REFUSED`**

Řešení:
1. Ujistěte se, že Flask aplikace běží (`python app.py`)
2. Zkuste tunel restartovat
3. Zkontrolujte, že port 5000 není blokovaný firewallem

### Android aplikace se necompiluje

**Chyba: `Could not resolve com.google.dagger:hilt-android:2.48`**

Řešení:
```bash
File → Invalidate Caches / Restart
```

**Chyba: `Unsupported class file major version 61`**

Řešení:
- Nainstalujte JDK 17+
- V Android Studio: `File` → `Settings` → `Build Tools` → `Gradle JDK` → Vyberte JDK 17

### Aplikace nemůže komunikovat s API

**Chyba v Logcatu: `java.net.UnknownHostException`**

Řešení:
1. Zkontrolujte URL v `build.gradle.kts`
2. Testujte URL v prohlížeči:
   ```
   https://vase-url.trycloudflare.com/api/mobile/sync/status
   ```
3. Ujistěte se, že aplikace má permission `INTERNET` v `AndroidManifest.xml`

**Chyba: `401 Unauthorized`**

Řešení:
- Zkuste se odhlásit a přihlásit znovu
- JWT token možná vypršel (platnost 7 dní)

---

## 📊 Architektura kompletního systému

```
┌─────────────────────┐
│  Android Aplikace   │
│  (Jetpack Compose)  │
└──────────┬──────────┘
           │ HTTPS (JWT)
           ▼
┌─────────────────────┐
│ Cloudflare Tunnel   │
│   (veřejný URL)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Flask Backend     │
│  (Python + REST)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  MySQL Databáze     │
└─────────────────────┘
```

---

## 🔄 Workflow vývoje

### 1. Backend změny

```bash
# Upravte app.py nebo mobile_api.py
# Restartujte server
python app.py
```

### 2. Android změny

```bash
# Upravte Kotlin soubory
# V Android Studio klikněte na "Run" (Shift+F10)
# Aplikace se automaticky přebuiluje a nainstaluje
```

### 3. Testování

```bash
# Backend: curl nebo Postman
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/mobile/logs

# Android: Použijte Logcat v Android Studio
# View → Tool Windows → Logcat
# Filtrujte podle "dochazka" nebo "okhttp"
```

---

## 📚 Další kroky

1. **Implementovat WorkManager** pro automatickou synchronizaci
2. **Přidat unit testy** pro repository vrstvu
3. **Implementovat správu chyb** (retry logic, error messages)
4. **Přidat více UI obrazovek** (nastavení, statistiky, profil)
5. **Optimalizovat synchronizaci** (delta sync místo full sync)

---

## 💡 Tipy a triky

### Pro rychlejší vývoj

1. **Hot Reload**: Použijte Compose Preview v Android Studio
2. **Fake API**: Vytvořte mock repository pro testování UI bez serveru
3. **Database Inspector**: `View` → `Tool Windows` → `App Inspection` → Database Inspector

### Pro debugging

1. **Logcat filtry**:
   ```
   package:com.example.dochazka
   tag:okhttp
   ```

2. **Network profiling**:
   ```
   View → Tool Windows → Profiler → Network
   ```

3. **Room databáze**:
   - Použijte Database Inspector pro vizualizaci dat
   - Nebo exportujte DB soubor z emulátoru

---

Hotovo! 🎉 Teď byste měli mít funkční mobilní aplikaci propojenou s vaším backendem.

Pokud narazíte na problémy, zkontrolujte:
1. Logcat v Android Studio
2. Flask konzoli (server logy)
3. Cloudflare tunnel output

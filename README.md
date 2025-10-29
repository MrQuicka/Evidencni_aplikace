# Evidenční aplikace (Docházka)

Webová aplikace pro evidenci pracovní docházky s mobilní Android aplikací.

## 🚀 Rychlý start

### Production instalace (doporučeno pro servery)

```bash
cd /srv/docker
sudo git clone https://github.com/MrQuicka/Evidencni_aplikace.git
sudo cp Evidencni_aplikace/docker-compose.production.yml docker-compose.yml
sudo docker compose up -d
```

Přístup: http://localhost:5000 (admin/admin)

### Development instalace

```bash
git clone https://github.com/MrQuicka/Evidencni_aplikace.git
cd Evidencni_aplikace
docker compose up -d
```

## 📚 Dokumentace

### Docker Setup
- **[README_DOCKER.md](README_DOCKER.md)** - Porovnání instalačních metod
- **[INSTALL_SRV_DOCKER.md](INSTALL_SRV_DOCKER.md)** - Production instalace do /srv/docker
- **[DOCKER_README.md](DOCKER_README.md)** - Development instalace
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide

### Aplikace
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - REST API dokumentace
- **[MOBILE_APP_SETUP.md](MOBILE_APP_SETUP.md)** - Android aplikace

## 🏗️ Struktura projektu

```
├── app.py                          # Flask backend
├── models.py                       # Databázové modely
├── mobile_api.py                   # REST API pro mobil
├── calendar_bp.py                  # Kalendářový modul
├── templates/                      # Web šablony
├── static/                         # Statické soubory
├── DochazkaMobile/                 # Android aplikace
│   └── app/                       # Kotlin/Compose kód
├── docker-compose.yml             # Development compose
└── docker-compose.production.yml  # Production compose
```

## ✨ Funkce

- ✅ Webová aplikace pro správu docházky
- ✅ Android mobilní aplikace (offline-first)
- ✅ Správa projektů a uživatelů
- ✅ Evidence pracovního času včetně pauz
- ✅ Export do Excel/CSV
- ✅ Kalendářové zobrazení
- ✅ Grafy a reporty
- ✅ REST API pro mobilní aplikaci

## 🔧 Technologie

**Backend:**
- Python + Flask
- MySQL databáze
- Flask-SQLAlchemy ORM
- Docker + Docker Compose

**Frontend:**
- HTML/CSS/JavaScript
- Bootstrap
- Chart.js pro grafy

**Mobile:**
- Kotlin
- Jetpack Compose
- Room Database
- Retrofit pro API
- Hilt pro dependency injection

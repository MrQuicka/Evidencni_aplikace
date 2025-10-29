# Docker Setup - Docházková aplikace

Tento dokument popisuje, jak spustit docházkovou aplikaci pomocí Docker a Docker Compose.

## 📋 Požadavky

- Docker (verze 20.10 nebo vyšší)
- Docker Compose (verze 2.0 nebo vyšší)

## 🚀 Rychlý start

### 1. Spuštění aplikace

```bash
# Spuštění všech služeb (databáze + web aplikace)
docker-compose up -d

# Sledování logů
docker-compose logs -f web
```

### 2. Přístup k aplikaci

- **Webová aplikace**: http://localhost:5000
- **MySQL databáze**: localhost:3306

### 3. Výchozí přihlašovací údaje

- **Username**: admin
- **Password**: admin

## 🛠️ Dostupné příkazy

### Základní operace

```bash
# Spuštění služeb na pozadí
docker-compose up -d

# Zastavení služeb
docker-compose down

# Restart služeb
docker-compose restart

# Sledování logů
docker-compose logs -f

# Pouze logy web aplikace
docker-compose logs -f web

# Pouze logy databáze
docker-compose logs -f db
```

### Build a rebuild

```bash
# Build aplikace bez cache
docker-compose build --no-cache

# Rebuild a restart
docker-compose up -d --build
```

### Databázové operace

```bash
# Přístup k MySQL konzoli
docker-compose exec db mysql -u dochazka_user -pdochazka_pass dochazka

# Záloha databáze
docker-compose exec db mysqldump -u dochazka_user -pdochazka_pass dochazka > backup.sql

# Restore databáze
docker-compose exec -T db mysql -u dochazka_user -pdochazka_pass dochazka < backup.sql

# Přístup k bash v databázovém kontejneru
docker-compose exec db bash
```

### Flask migrace

```bash
# Spuštění migrací
docker-compose exec web flask db upgrade

# Vytvoření nové migrace
docker-compose exec web flask db migrate -m "popis zmeny"

# Přístup k Python shell v kontejneru
docker-compose exec web python
```

### Čištění

```bash
# Zastavení a odstranění kontejnerů, sítí
docker-compose down

# Odstranění včetně volumes (SMAŽE DATA!)
docker-compose down -v

# Kompletní cleanup včetně images
docker-compose down --rmi all -v
```

## 📁 Struktura služeb

### Web aplikace (Flask)
- **Port**: 5000
- **Kontext**: Python 3.11
- **Auto-reload**: Zapnutý (development mode)
- **Volumes**: Zdrojový kód je mountovaný pro live reload

### Databáze (MySQL 8.0)
- **Port**: 3306
- **Username**: dochazka_user
- **Password**: dochazka_pass
- **Database**: dochazka
- **Perzistence**: Volume `mysql_data`

## 🔧 Konfigurace

### Environment proměnné

Upravit můžete v `docker-compose.yml`:

```yaml
environment:
  SQLALCHEMY_DATABASE_URI: mysql+pymysql://user:pass@db:3306/database
  FLASK_ENV: development
  FLASK_DEBUG: 1
```

### Databázové přihlašovací údaje

Pro změnu databázových credentials upravte sekci `db` v `docker-compose.yml`:

```yaml
environment:
  MYSQL_ROOT_PASSWORD: your_root_password
  MYSQL_DATABASE: your_database_name
  MYSQL_USER: your_username
  MYSQL_PASSWORD: your_password
```

**⚠️ DŮLEŽITÉ**: Po změně credentials musíte aktualizovat i proměnnou `SQLALCHEMY_DATABASE_URI` v sekci `web`!

## 🐛 Troubleshooting

### Aplikace se nemůže připojit k databázi

```bash
# Zkontrolujte, zda databáze běží
docker-compose ps

# Zkontrolujte logy databáze
docker-compose logs db

# Restartujte služby
docker-compose restart
```

### Port je již obsazený

Pokud je port 5000 nebo 3306 již obsazený, upravte mapping v `docker-compose.yml`:

```yaml
ports:
  - "8080:5000"  # Pro web aplikaci
  - "3307:3306"  # Pro databázi
```

### Databáze neobsahuje tabulky

```bash
# Spusťte Flask shell a vytvořte tabulky
docker-compose exec web python << EOF
from app import app, db
with app.app_context():
    db.create_all()

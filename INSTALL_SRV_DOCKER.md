# Instalace do /srv/docker struktury

Tento průvodce popisuje, jak nainstalovat aplikaci do standardní `/srv/docker/` struktury, kde `docker-compose.yml` je v hlavním adresáři a aplikace v podadresáři.

## 📁 Struktura adresářů

```
/srv/docker/
├── docker-compose.yml              # Hlavní compose soubor (spouští se odtud)
└── Evidencni_aplikace/             # Aplikace
    ├── app.py
    ├── models.py
    ├── Dockerfile
    ├── requirements.txt
    ├── init.sql
    ├── templates/
    ├── static/
    └── ...
```

## 🚀 Instalace - Krok za krokem

### Krok 1: Příprava adresářů

```bash
# Vytvoření hlavního adresáře
sudo mkdir -p /srv/docker

# Přejdi do adresáře
cd /srv/docker
```

### Krok 2: Stažení aplikace

**Možnost A: Git clone (doporučeno)**

```bash
# Clone repository do /srv/docker/Evidencni_aplikace/
sudo git clone https://github.com/MrQuicka/Evidencni_aplikace.git

# Výsledná struktura:
# /srv/docker/Evidencni_aplikace/...
```

**Možnost B: Kopírování souborů**

```bash
sudo mkdir -p /srv/docker/Evidencni_aplikace
sudo cp -r /cesta/k/aplikaci/* /srv/docker/Evidencni_aplikace/
```

### Krok 3: Zkopírování docker-compose.yml

```bash
# Zkopíruj production docker-compose soubor do /srv/docker/
sudo cp /srv/docker/Evidencni_aplikace/docker-compose.production.yml /srv/docker/docker-compose.yml
```

### Krok 4: Ověření struktury

```bash
cd /srv/docker

# Zkontroluj strukturu
ls -la
# Mělo by vypsat:
# docker-compose.yml
# Evidencni_aplikace/

# Zkontroluj aplikaci
ls -la Evidencni_aplikace/
# Mělo by obsahovat: app.py, Dockerfile, requirements.txt, atd.
```

### Krok 5: Spuštění

```bash
# Spuštění z /srv/docker/
cd /srv/docker
sudo docker compose up -d

# Sledování logů
sudo docker compose logs -f web
```

## ✅ Ověření instalace

```bash
# Zkontroluj běžící kontejnery
sudo docker compose ps

# Mělo by vypsat:
# NAME            STATUS          PORTS
# dochazka_db     Up (healthy)    0.0.0.0:3306->3306/tcp
# dochazka_web    Up              0.0.0.0:5000->5000/tcp

# Test aplikace
curl http://localhost:5000
# Nebo otevři v prohlížeči
```

## 🔄 Správa aplikace

### Základní operace

```bash
# Všechny příkazy se spouští z /srv/docker/
cd /srv/docker

# Spuštění
sudo docker compose up -d

# Zastavení
sudo docker compose down

# Restart
sudo docker compose restart

# Logy
sudo docker compose logs -f
```

### Aktualizace aplikace

```bash
cd /srv/docker

# 1. Zastavení služeb
sudo docker compose down

# 2. Aktualizace kódu
cd Evidencni_aplikace
sudo git pull origin main
cd ..

# 3. Rebuild a spuštění
sudo docker compose up -d --build
```

### Záloha databáze

```bash
cd /srv/docker

# Vytvoření zálohy
sudo docker compose exec db mysqldump -u dochazka_user -pdochazka_pass dochazka > backup_$(date +%Y%m%d).sql

# Restore zálohy
sudo docker compose exec -T db mysql -u dochazka_user -pdochazka_pass dochazka < backup_20250101.sql
```

## 🔧 Konfigurace

### Změna databázových hesel (DŮLEŽITÉ pro production!)

Edituj `/srv/docker/docker-compose.yml`:

```yaml
# Sekce db - změň hesla
environment:
  MYSQL_ROOT_PASSWORD: "TVOJE_SILNE_HESLO_ROOT"
  MYSQL_PASSWORD: "TVOJE_SILNE_HESLO_USER"

# Sekce web - aktualizuj connection string
environment:
  SQLALCHEMY_DATABASE_URI: mysql+pymysql://dochazka_user:TVOJE_SILNE_HESLO_USER@db:3306/dochazka
```

### Změna SECRET_KEY

Edituj `/srv/docker/Evidencni_aplikace/app.py`:

```python
app.config['SECRET_KEY'] = 'vygeneruj-nahodny-tajny-klic-min-32-znaku'
```

Po změnách rebuild:
```bash
cd /srv/docker
sudo docker compose down
sudo docker compose up -d --build
```

## 🔒 Production checklist

Před nasazením do produkce:

- [ ] Změněna výchozí hesla databáze v `docker-compose.yml`
- [ ] Změněn `SECRET_KEY` v `app.py`
- [ ] Vypnut debug mode (již nastaveno v production compose)
- [ ] Nastaven automatický backup (viz níže)
- [ ] Nastaven firewall
- [ ] Zvážit použití NGINX reverse proxy
- [ ] Zvážit SSL certifikát

## 📦 Automatické zálohy

Vytvoř cron job pro automatické zálohy:

```bash
# Editace crontab
sudo crontab -e

# Přidej řádek (záloha každý den ve 2:00)
0 2 * * * cd /srv/docker && docker compose exec -T db mysqldump -u dochazka_user -pdochazka_pass dochazka > /srv/backups/dochazka_$(date +\%Y\%m\%d).sql

# Vytvoř adresář pro zálohy
sudo mkdir -p /srv/backups
```

## 🐛 Troubleshooting

### Aplikace se nespouští

```bash
cd /srv/docker

# Zkontroluj logy
sudo docker compose logs web
sudo docker compose logs db

# Zkontroluj, zda databáze běží
sudo docker compose ps
```

### Změny v kódu se neprojevují

```bash
cd /srv/docker

# Production compose nemá mounted volumes pro live reload
# Musíš provést rebuild
sudo docker compose down
sudo docker compose up -d --build
```

### Port conflict (port již používán)

Edituj `/srv/docker/docker-compose.yml`:

```yaml
# Změň porty
ports:
  - "8080:5000"  # Pro web
  - "3307:3306"  # Pro databázi
```

## 🌐 Firewall

Pokud chceš přístup z venku:

```bash
# Povolit port 5000
sudo ufw allow 5000/tcp

# Nebo jen z konkrétní IP
sudo ufw allow from TVOJE_IP to any port 5000
```

## 📱 Mobilní aplikace

Pro připojení mobilní aplikace:

1. Zjisti IP adresu serveru:
   ```bash
   ip addr show
   ```

2. V Android aplikaci nastav API URL:
   ```
   http://SERVER_IP:5000/api/mobile/
   ```

3. Ujisti se, že firewall povoluje připojení na port 5000

## 🆘 Podpora

Pro více informací viz:
- `DOCKER_README.md` - Obecná Docker dokumentace
- `API_DOCUMENTATION.md` - API dokumentace
- `MOBILE_APP_SETUP.md` - Setup mobilní aplikace

## 📝 Výchozí přihlašovací údaje

Po prvním spuštění:
- **Username**: admin
- **Password**: admin

**⚠️ ZMĚŇ HESLO PO PRVNÍM PŘIHLÁŠENÍ!**

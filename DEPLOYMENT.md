# Deployment Guide - Docházková aplikace

## 🚀 Deployment do /srv/docker struktury

### Krok 1: Příprava struktury adresářů

```bash
# Vytvoření adresáře pro aplikaci
sudo mkdir -p /srv/docker/Evidencni_aplikace

# Nastavení práv (volitelné, podle vašeho setupu)
sudo chown -R $USER:$USER /srv/docker/Evidencni_aplikace
```

### Krok 2: Zkopírování aplikace

**Možnost A: Git clone (doporučeno)**

```bash
cd /srv/docker
sudo git clone https://github.com/MrQuicka/Evidencni_aplikace.git
cd Evidencni_aplikace
```

**Možnost B: Kopírování souborů**

```bash
# Zkopírování všech souborů aplikace
sudo cp -r /cesta/k/Evidencni_aplikace/* /srv/docker/Evidencni_aplikace/

# Nebo použít rsync pro lepší kontrolu
sudo rsync -av --exclude 'DochazkaMobile/' \
                --exclude '__pycache__/' \
                --exclude '*.pyc' \
                /cesta/k/Evidencni_aplikace/ \
                /srv/docker/Evidencni_aplikace/
```

### Krok 3: Přechod do adresáře a spuštění

```bash
# DŮLEŽITÉ: Musíš být v adresáři s docker-compose.yml!
cd /srv/docker/Evidencni_aplikace

# Spuštění služeb
sudo docker compose up -d

# Sledování logů
sudo docker compose logs -f
```

## ❌ Časté chyby

### Chyba: "failed to read dockerfile: open Dockerfile: no such file or directory"

**Příčina**: Spouštíš `docker compose` z nesprávného adresáře.

**Řešení**:
```bash
# Zkontroluj, že jsi ve správném adresáři
pwd
# Mělo by vypsat: /srv/docker/Evidencni_aplikace

# Zkontroluj, že soubory existují
ls -la | grep -E "docker-compose.yml|Dockerfile"

# Pokud soubory neexistují, jsi ve špatném adresáři
cd /srv/docker/Evidencni_aplikace
```

### Chyba: "permission denied"

**Řešení**:
```bash
# Použij sudo pro Docker příkazy
sudo docker compose up -d

# Nebo přidej uživatele do docker skupiny (jednorázově)
sudo usermod -aG docker $USER
# Pak se odhlásit a přihlásit znovu
```

## 🔧 Struktura adresářů

Po správném nastavení by struktura měla vypadat takto:

```
/srv/docker/
└── Evidencni_aplikace/
    ├── docker-compose.yml          # Hlavní konfigurační soubor
    ├── Dockerfile                  # Build instrukce pro Flask app
    ├── .dockerignore              # Soubory ignorované při build
    ├── init.sql                   # Inicializační SQL skript
    ├── app.py                     # Hlavní Flask aplikace
    ├── models.py                  # Databázové modely
    ├── requirements.txt           # Python závislosti
    ├── templates/                 # Flask šablony
    ├── static/                    # Statické soubory
    └── ...                        # Další soubory aplikace
```

## 📝 Ověření instalace

```bash
# 1. Zkontroluj běžící kontejnery
sudo docker compose ps

# Mělo by vypsat něco jako:
# NAME            IMAGE               STATUS          PORTS
# dochazka_db     mysql:8.0          Up (healthy)    0.0.0.0:3306->3306/tcp
# dochazka_web    evidencni-web      Up              0.0.0.0:5000->5000/tcp

# 2. Zkontroluj logy
sudo docker compose logs web | tail -20

# 3. Testuj aplikaci
curl http://localhost:5000
# Nebo otevři v prohlížeči
```

## 🔄 Aktualizace aplikace

```bash
cd /srv/docker/Evidencni_aplikace

# 1. Stáhni nejnovější změny
sudo git pull origin main  # nebo váš branch

# 2. Rebuild a restart
sudo docker compose down
sudo docker compose up -d --build

# Nebo jen restart bez rebuildu (pokud se nezměnil Dockerfile)
sudo docker compose restart
```

## 🛑 Zastavení a odstranění

```bash
cd /srv/docker/Evidencni_aplikace

# Zastavení služeb (data zůstanou)
sudo docker compose down

# Zastavení a smazání dat (POZOR - smaže databázi!)
sudo docker compose down -v

# Úplné vyčištění včetně images
sudo docker compose down --rmi all -v
```

## 🔐 Production doporučení

Pro produkční nasazení v /srv/docker:

### 1. Změň výchozí hesla

Edituj `docker-compose.yml`:

```yaml
environment:
  MYSQL_ROOT_PASSWORD: "SILNE_HESLO_ROOT"
  MYSQL_PASSWORD: "SILNE_HESLO_USER"
```

A také v sekci `web`:

```yaml
environment:
  SQLALCHEMY_DATABASE_URI: mysql+pymysql://dochazka_user:SILNE_HESLO_USER@db:3306/dochazka
```

### 2. Změň SECRET_KEY

V `app.py` změň:
```python
app.config['SECRET_KEY'] = 'tvuj-nahodny-tajny-klic-min-32-znaku'
```

### 3. Vypni debug mode

V `docker-compose.yml`:
```yaml
environment:
  FLASK_ENV: production
  FLASK_DEBUG: 0
```

### 4. Nastavení backupů

```bash
# Vytvoř cron job pro automatické zálohy
sudo crontab -e

# Přidej řádek (záloha každý den ve 2:00)
0 2 * * * cd /srv/docker/Evidencni_aplikace && docker compose exec -T db mysqldump -u dochazka_user -pdochazka_pass dochazka > /srv/backups/dochazka_$(date +\%Y\%m\%d).sql
```

### 5. Nastavení restartování

V `docker-compose.yml` je již nastaveno:
```yaml
restart: unless-stopped
```

To zajistí, že kontejnery se automaticky restartují po restartu serveru.

## 🌐 Přístup z venku

Pokud chceš přístup z internetu:

1. **Nastavení firewallu**:
```bash
# Povolení portu 5000
sudo ufw allow 5000/tcp

# Nebo jen z konkrétní IP
sudo ufw allow from TVOJE_IP to any port 5000
```

2. **Doporučeno: Použít NGINX reverse proxy** místo přímého přístupu

3. **Nastavit SSL certifikát** (Let's Encrypt)

## ✅ Checklist pro deployment

- [ ] Aplikace zkopírována do `/srv/docker/Evidencni_aplikace/`
- [ ] Změněna výchozí hesla v `docker-compose.yml`
- [ ] Změněn `SECRET_KEY` v `app.py`
- [ ] Vypnut debug mode pro production
- [ ] Nastaven automatický backup databáze
- [ ] Otestováno spuštění: `cd /srv/docker/Evidencni_aplikace && sudo docker compose up -d`
- [ ] Ověřen přístup na `http://localhost:5000`
- [ ] Nastaven firewall (pokud je potřeba)
- [ ] Dokumentován admin účet (username: admin, password: změň!)

## 🆘 Pomoc

Pokud máš problémy:

1. Zkontroluj logy: `sudo docker compose logs -f`
2. Zkontroluj běžící kontejnery: `sudo docker compose ps`
3. Zkontroluj, že jsi ve správném adresáři: `pwd`
4. Pro více informací viz `DOCKER_README.md`

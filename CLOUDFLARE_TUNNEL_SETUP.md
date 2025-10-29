# Cloudflare Tunnel Setup - dochazka.dev-nagauc.eu

Tento průvodce popisuje jak nastavit Cloudflare Tunnel pro přístup k aplikaci přes doménu `dochazka.dev-nagauc.eu`.

## 📋 Přehled

- **Doména:** `dochazka.dev-nagauc.eu`
- **Lokální port:** `5000` (Flask aplikace)
- **Cloudflare Tunnel:** Zajistí HTTPS a veřejný přístup
- **Bez potřeby:** Otevírat porty v routeru nebo veřejná IP

## 🔐 Krok 1: Získání Cloudflare Tunnel tokenu

### 1.1 Přihlášení do Cloudflare

1. Jdi na https://dash.cloudflare.com/
2. Vyber svou doménu `dev-nagauc.eu`
3. V levém menu: **Zero Trust** (nebo **Access**)

### 1.2 Vytvoření Tunnelu

1. V Zero Trust dashboard: **Networks → Tunnels**
2. Klikni **Create a tunnel**
3. Vyber **Cloudflared**
4. Pojmenuj tunnel: `dochazka-app`
5. **Save tunnel**

### 1.3 Konfigurace Tunnelu

Po vytvoření tunnelu:

1. **Public Hostname** sekce:
   - **Subdomain:** `dochazka`
   - **Domain:** `dev-nagauc.eu`
   - **Type:** `HTTP`
   - **URL:** `dochazka_web:5000` (nebo `localhost:5000`)

2. Klikni **Save hostname**

### 1.4 Zkopírování tokenu

1. V tunnel detailech najdi **Install connector**
2. Zkopíruj token z příkazu:
   ```bash
   cloudflared service install <TVŮJ_DLOUHÝ_TOKEN>
   ```
3. **Tento token budeš potřebovat v dalším kroku!**

## 🐳 Krok 2: Přidání Cloudflared do Docker Compose

### 2.1 Vytvoř soubor s tokenem

```bash
cd /srv/docker

# Vytvoř soubor s tokenem (NEBUDE V GITU!)
echo "TVŮJ_TOKEN_ZDE" > cloudflare-tunnel-token.txt

# Nastav práva
sudo chmod 600 cloudflare-tunnel-token.txt
```

### 2.2 Použij production compose s cloudflared

Aplikace již obsahuje připravený `docker-compose.production-cloudflare.yml`.

```bash
cd /srv/docker

# Zkopíruj production compose s cloudflare
sudo cp Evidencni_aplikace/docker-compose.production-cloudflare.yml docker-compose.yml

# DŮLEŽITÉ: Edituj docker-compose.yml a vlož svůj token
sudo nano docker-compose.yml
# Najdi řádek s TUNNEL_TOKEN a nahraď <YOUR_CLOUDFLARE_TUNNEL_TOKEN>
```

### 2.3 Spusť aplikaci s Cloudflare Tunnel

```bash
cd /srv/docker

# Zastavit běžící kontejnery
sudo docker compose down

# Spustit s cloudflared
sudo docker compose up -d

# Zkontrolovat logy
sudo docker compose logs cloudflared
sudo docker compose logs web
```

## ✅ Krok 3: Ověření

### 3.1 Zkontroluj Cloudflare Dashboard

1. Jdi zpět do **Tunnels** v Cloudflare
2. Tvůj tunnel by měl být **Healthy** (zelený)
3. Status: **Connected**

### 3.2 Test aplikace

```bash
# Z prohlížeče:
https://dochazka.dev-nagauc.eu

# Mělo by přesměrovat na login stránku
```

## 📱 Krok 4: Aktualizace mobilní aplikace

Mobilní aplikace používá production URL:

```
https://dochazka.dev-nagauc.eu/api/mobile/
```

Toto je již nastaveno v `docker-compose.production-cloudflare.yml` a `build.gradle.kts`.

Pro build aplikace:

```bash
cd /srv/docker/Evidencni_aplikace/DochazkaMobile

# Build release verze
./gradlew assembleRelease

# APK bude v:
# app/build/outputs/apk/release/app-release.apk
```

## 🔒 Krok 5: Zabezpečení (Volitelné)

### 5.1 Změna výchozích hesel

Edituj `/srv/docker/docker-compose.yml`:

```yaml
# Databáze
environment:
  MYSQL_ROOT_PASSWORD: <SILNE_HESLO>
  MYSQL_PASSWORD: <SILNE_HESLO_USER>

# Web
environment:
  SQLALCHEMY_DATABASE_URI: mysql+pymysql://dochazka_user:<SILNE_HESLO_USER>@db:3306/dochazka
```

Po změně:
```bash
sudo docker compose down -v  # POZOR: Smaže data!
sudo docker compose up -d
```

### 5.2 Změna SECRET_KEY v aplikaci

Edituj `Evidencni_aplikace/app.py`:
```python
app.config['SECRET_KEY'] = 'vygeneruj-nahodny-tajny-klic-min-32-znaku'
```

### 5.3 Cloudflare Access (Extra zabezpečení)

V Cloudflare Zero Trust můžeš nastavit:
- **Email ověření** před přístupem
- **IP whitelist**
- **Geo-blocking**

## 🐛 Troubleshooting

### Tunnel se nepřipojuje

```bash
# Zkontroluj logy cloudflared
sudo docker compose logs cloudflared

# Časté problémy:
# - Špatný token
# - Token s mezerami nebo novým řádkem
# - Nesprávná konfigurace v Cloudflare dashboardu
```

### 502 Bad Gateway

```bash
# Zkontroluj že web kontejner běží
sudo docker compose ps

# Zkontroluj logy web kontejneru
sudo docker compose logs web

# Restart web kontejneru
sudo docker compose restart web
```

### CORS chyby v mobilní aplikaci

Aplikace má CORS již nakonfigurovaný pro `*.dev-nagauc.eu`, ale pokud máš problémy:

```python
# V app.py zkontroluj:
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://dochazka.dev-nagauc.eu", "http://localhost:*"]
    }
})
```

## 📊 Monitoring

### Kontrola stavu

```bash
# Všechny kontejnery
sudo docker compose ps

# Logy cloudflared
sudo docker compose logs -f cloudflared

# Logy aplikace
sudo docker compose logs -f web
```

### Cloudflare Analytics

V Cloudflare dashboardu můžeš sledovat:
- **Analytics → Traffic** - návštěvnost
- **Zero Trust → Access → Audit Logs** - přístupové logy
- **Tunnels → [tvůj tunnel]** - tunnel health

## 🔄 Aktualizace aplikace

```bash
cd /srv/docker

# Pull nový kód
cd Evidencni_aplikace
sudo git pull
cd ..

# Rebuild a restart
sudo docker compose down
sudo docker compose up -d --build
```

## 📝 Důležité soubory

```
/srv/docker/
├── docker-compose.yml                    # Production compose s cloudflared
├── cloudflare-tunnel-token.txt          # Token (NE V GITU!)
└── Evidencni_aplikace/
    ├── app.py                           # Flask app s CORS
    └── DochazkaMobile/
        └── app/build.gradle.kts         # Production URL konfigurace
```

## 🆘 Podpora

Pro více informací:
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Zero Trust Dashboard](https://dash.teams.cloudflare.com/)
- Aplikační logy: `sudo docker compose logs -f`

## ⚡ Quick Start Checklist

- [ ] Vytvořen Cloudflare Tunnel v dashboardu
- [ ] Zkopírován tunnel token
- [ ] Token uložen do `cloudflare-tunnel-token.txt`
- [ ] Zkopírován production-cloudflare compose
- [ ] Token vložen do docker-compose.yml
- [ ] Aplikace spuštěna: `sudo docker compose up -d`
- [ ] Tunnel je "Healthy" v Cloudflare
- [ ] Aplikace funguje na https://dochazka.dev-nagauc.eu
- [ ] Změněna výchozí hesla
- [ ] Mobilní aplikace zkompilována s production URL

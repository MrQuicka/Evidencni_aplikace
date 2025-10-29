# Docker Setup - Dva způsoby instalace

Tato aplikace podporuje dva způsoby Docker instalace podle vaší preferované struktury.

## 📌 Metoda 1: Production struktura (DOPORUČENO pro /srv/docker)

**Kde spouštíš docker compose:** `/srv/docker/`
**Kde je aplikace:** `/srv/docker/Evidencni_aplikace/`

### Struktura adresářů

```
/srv/docker/
├── docker-compose.yml              # <- docker compose up zde
└── Evidencni_aplikace/
    ├── app.py
    ├── Dockerfile
    ├── requirements.txt
    └── ...
```

### Instalace

```bash
cd /srv/docker
sudo git clone https://github.com/MrQuicka/Evidencni_aplikace.git
sudo cp Evidencni_aplikace/docker-compose.production.yml docker-compose.yml
sudo docker compose up -d
```

### Použitý soubor
- `docker-compose.production.yml` → zkopírován jako `/srv/docker/docker-compose.yml`

### Správa

```bash
# Všechny příkazy z /srv/docker/
cd /srv/docker

sudo docker compose up -d      # Spuštění
sudo docker compose down       # Zastavení
sudo docker compose logs -f    # Logy
```

📖 **Detailní průvodce:** [INSTALL_SRV_DOCKER.md](INSTALL_SRV_DOCKER.md)

---

## 📌 Metoda 2: Development struktura

**Kde spouštíš docker compose:** V adresáři aplikace
**Kde je aplikace:** `/cesta/k/Evidencni_aplikace/`

### Struktura adresářů

```
/cesta/k/Evidencni_aplikace/
├── docker-compose.yml          # <- docker compose up zde
├── Dockerfile
├── app.py
└── ...
```

### Instalace

```bash
git clone https://github.com/MrQuicka/Evidencni_aplikace.git
cd Evidencni_aplikace
docker compose up -d
```

### Použitý soubor
- `docker-compose.yml` (standardní development verze)

### Správa

```bash
# Všechny příkazy z adresáře aplikace
cd /cesta/k/Evidencni_aplikace

docker compose up -d      # Spuštění
docker compose down       # Zastavení  
docker compose logs -f    # Logy
```

📖 **Detailní průvodce:** [DOCKER_README.md](DOCKER_README.md)

---

## 🔍 Porovnání metod

| Aspekt | Metoda 1 (Production) | Metoda 2 (Development) |
|--------|----------------------|----------------------|
| **Kde spouštět** | `/srv/docker/` | Adresář aplikace |
| **Compose soubor** | `docker-compose.production.yml` | `docker-compose.yml` |
| **Live reload** | ❌ Ne (production) | ✅ Ano |
| **Vhodné pro** | Production server | Development |
| **Debug mode** | ❌ Vypnutý | ✅ Zapnutý |
| **Volumes** | Jen templates/static | Celý kód |

## ❓ Kterou metodu vybrat?

### Použij Metodu 1 pokud:
- ✅ Nasazuješ na production server
- ✅ Chceš standardní `/srv/docker/` strukturu
- ✅ Chceš mít více aplikací v `/srv/docker/`
- ✅ Chceš spouštět docker compose z jednoho místa

### Použij Metodu 2 pokud:
- ✅ Vyvíjíš aplikaci lokálně
- ✅ Potřebuješ live reload při změnách kódu
- ✅ Chceš debug mode zapnutý
- ✅ Experimentuješ s aplikací

## 🚀 Rychlý start

### Pro production (/srv/docker):

```bash
cd /srv/docker
sudo git clone https://github.com/MrQuicka/Evidencni_aplikace.git
sudo cp Evidencni_aplikace/docker-compose.production.yml docker-compose.yml
sudo docker compose up -d
```

### Pro development:

```bash
git clone https://github.com/MrQuicka/Evidencni_aplikace.git
cd Evidencni_aplikace
docker compose up -d
```

## 📱 Přístup k aplikaci

Po spuštění kteroukoliv metodou:

- **Webová aplikace**: http://localhost:5000
- **MySQL databáze**: localhost:3306
- **Login**: admin / admin

## 📚 Kompletní dokumentace

- [INSTALL_SRV_DOCKER.md](INSTALL_SRV_DOCKER.md) - Production instalace
- [DOCKER_README.md](DOCKER_README.md) - Development instalace
- [DEPLOYMENT.md](DEPLOYMENT.md) - Obecný deployment guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API dokumentace

## 🆘 Řešení problémů

### "failed to read dockerfile"

**Příčina:** Špatný adresář pro docker compose

**Řešení:**
```bash
# Metoda 1: Musíš být v /srv/docker/
cd /srv/docker
pwd  # Mělo by vypsat /srv/docker

# Metoda 2: Musíš být v adresáři aplikace
cd /cesta/k/Evidencni_aplikace
pwd  # Mělo by vypsat /cesta/k/Evidencni_aplikace
```

### Změny v kódu se neprojevují

- **Metoda 1:** Musíš provést rebuild: `sudo docker compose down && sudo docker compose up -d --build`
- **Metoda 2:** Změny se projeví automaticky (live reload)

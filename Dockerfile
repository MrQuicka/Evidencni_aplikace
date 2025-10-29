# Dockerfile pro Flask backend aplikaci

FROM python:3.11-slim

# Nastavení pracovního adresáře
WORKDIR /app

# Instalace systémových závislostí pro PyMySQL a další
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Kopírování requirements a instalace Python závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování aplikace
COPY . .

# Nastavení proměnných prostředí
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Exponování portu
EXPOSE 5000

# Spuštění aplikace
# Pro development použijeme Flask development server
# Pro production doporučuji Gunicorn
CMD ["python", "app.py"]

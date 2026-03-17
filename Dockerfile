FROM python:3.9-slim
WORKDIR /app

# Systémové závislosti pro WeasyPrint (PDF generování)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Instaluj závislosti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Zkopíruj aplikaci
COPY . .

# Port
EXPOSE 5000

# Použij gunicorn místo development serveru
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "120", "app:app"]

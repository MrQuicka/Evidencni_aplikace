FROM python:3.9-slim
WORKDIR /app

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

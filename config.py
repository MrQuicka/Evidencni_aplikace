# config.py
import os

class BaseConfig:
    # Bezpečnostní klíč z prostředí (pro session, CSRF apod.)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    # Databáze – zatím klidně SQLite; později přepneme na Postgres/MySQL
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instance/app.db")
    # Flask built-ins
    DEBUG = False
    TESTING = False

class DevConfig(BaseConfig):
    DEBUG = True

class ProdConfig(BaseConfig):
    DEBUG = False

class TestConfig(BaseConfig):
    TESTING = True
    DEBUG = True

# config.py
import os

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instance/app.db")
    # >> DŮLEŽITÉ: SQLAlchemy očekává klíč SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # vypne hlučné signalizace
    DEBUG = False
    TESTING = False

class DevConfig(BaseConfig):
    DEBUG = True

class ProdConfig(BaseConfig):
    DEBUG = False

class TestConfig(BaseConfig):
    TESTING = True
    DEBUG = True

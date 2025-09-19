# app.py
import os
from flask import Flask
from dotenv import load_dotenv
from extensions import db, migrate
from extensions import db as _db
from models import Record as _Record


# Načti .env soubor, pokud existuje
load_dotenv()

def create_app():
    # instance_relative_config=True => Flask použije složku /instance pro soukromá data (např. SQLite)
    app = Flask(__name__, instance_relative_config=True)

    # Výběr konfigurace dle FLASK_CONFIG (dev/prod/test); defaultně dev
    cfg = os.getenv("FLASK_CONFIG", "dev").lower()
    if cfg == "prod":
        from config import ProdConfig as Config
    elif cfg == "test":
        from config import TestConfig as Config
    else:
        from config import DevConfig as Config

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    from models import Record 
    
    # --- Registrace blueprintů ---
    try:
        from calendar_bp import bp as calendar_bp
        app.register_blueprint(calendar_bp, url_prefix="/calendar")
    except Exception as e:
        app.logger.warning(f"calendar_bp nebyl zaregistrován: {e}")

    # --- Základní trasa (ponech jako fallback; klidně si ji uprav) ---
    @app.get("/")
    def index():
        return "Aplikace běží. 🎉  (Uprav /templates a blueprinty podle potřeby.)"

    # Healthcheck pro monitoring/orchestraci
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app




# Umožní spustit: python app.py (kromě 'flask --app app run')
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    create_app().run(host="0.0.0.0", port=port)

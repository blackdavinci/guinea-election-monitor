"""
Configuration générale du système de veille électorale.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins du projet
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
SRC_DIR = BASE_DIR / "src"

# Configuration de la base de données
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "guinea_elections"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "changeme"),
}

# URL de connexion SQLAlchemy
# Gère le cas sans mot de passe (Postgres.app sur macOS)
if DATABASE_CONFIG["password"]:
    DATABASE_URL = (
        f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
        f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
    )
else:
    DATABASE_URL = (
        f"postgresql://{DATABASE_CONFIG['user']}"
        f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
    )

# Configuration du scraping
SCRAPING_CONFIG = {
    "request_timeout": int(os.getenv("REQUEST_TIMEOUT", 30)),
    "request_delay": float(os.getenv("REQUEST_DELAY", 2)),
    "max_retries": int(os.getenv("MAX_RETRIES", 3)),
    "relevance_threshold": float(os.getenv("RELEVANCE_THRESHOLD", 0.3)),
}

# Configuration du logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "scraper.log"

# Configuration des notifications (optionnel)
NOTIFICATION_CONFIG = {
    "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
    "smtp_server": os.getenv("SMTP_SERVER"),
    "smtp_port": int(os.getenv("SMTP_PORT", 587)) if os.getenv("SMTP_PORT") else None,
    "smtp_user": os.getenv("SMTP_USER"),
    "smtp_password": os.getenv("SMTP_PASSWORD"),
    "notification_email": os.getenv("NOTIFICATION_EMAIL"),
}

# User agents pour rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

# DB_URL обязательно для Docker/PostgreSQL,
# но локально fallback на SQLite
DB_URL = os.getenv("DB_URL") or "sqlite:///equipment.db"

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "changeme").strip()
INITIAL_NOTIFIERS = os.getenv("INITIAL_NOTIFIERS", "").strip()

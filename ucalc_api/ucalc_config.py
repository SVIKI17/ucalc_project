import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_URL = os.getenv("UCALC_DB_URL", "sqlite:///./ucalc_local.db")
if DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)

WEB_DIR = BASE_DIR / "ucalc_web"

API_HOST = os.getenv("UCALC_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("UCALC_API_PORT", "8200"))
import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_TELEGRAM_IDS = os.getenv("ADMIN_TELEGRAM_IDS")

if ADMIN_TELEGRAM_IDS:
    ADMIN_TELEGRAM_IDS = [int(x.strip()) for x in ADMIN_TELEGRAM_IDS.split(",")]
else:
    ADMIN_TELEGRAM_IDS = []

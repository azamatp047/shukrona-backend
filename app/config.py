import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432") # Portni string qilib olgan ma'qul yoki defaultni to'g'irlash

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_TELEGRAM_IDS = os.getenv("ADMIN_TELEGRAM_IDS")

# ---------------- Cloudinary config ----------------
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# TUZATILGAN QISM:
if ADMIN_TELEGRAM_IDS:
    # int() ni olib tashladik. Endi ular string bo'lib qoladi: ['12345', '67890']
    ADMIN_TELEGRAM_IDS = [x.strip() for x in ADMIN_TELEGRAM_IDS.split(",")]
else:
    ADMIN_TELEGRAM_IDS = []

# Rasmlar saqlanadigan papka
UPLOAD_DIR = "static/images"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
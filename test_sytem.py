#!/usr/bin/env python3
"""
Tizim sozlamalarini va komponentlarni tekshirish
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import subprocess

def check_file(filename):
    """Fayl mavjudligini tekshirish"""
    if Path(filename).exists():
        print(f"✅ {filename} topildi")
        return True
    else:
        print(f"❌ {filename} topilmadi!")
        return False

def check_env_var(var_name):
    """Environment o'zgaruvchisini tekshirish"""
    value = os.getenv(var_name)
    if value:
        # Parol va tokenlarni yashirish
        if 'PASSWORD' in var_name or 'TOKEN' in var_name or 'SECRET' in var_name:
            display_value = value[:5] + "..." if len(value) > 5 else "***"
        else:
            display_value = value
        print(f"✅ {var_name}: {display_value}")
        return True
    else:
        print(f"❌ {var_name} o'rnatilmagan!")
        return False

def check_python_package(package_name):
    """Python paketini tekshirish"""
    try:
        __import__(package_name)
        print(f"✅ {package_name} o'rnatilgan")
        return True
    except ImportError:
        print(f"❌ {package_name} o'rnatilmagan!")
        return False

def main():
    print("=" * 60)
    print("🔍 SHUKRONA DELIVERY TIZIM TEKSHIRUVI")
    print("=" * 60)
    
    # .env faylini yuklash
    load_dotenv()
    
    all_ok = True
    
    # 1. Muhim fayllarni tekshirish
    print("\n📁 FAYLLAR:")
    print("-" * 60)
    files_to_check = [
        ".env",
        "requirements.txt",
        "app/main.py",
        "app/database.py",
        "app/config.py",
        "bot_user.py",
        "bot_admin.py",
        "bot_courier.py"
    ]
    
    for file in files_to_check:
        if not check_file(file):
            all_ok = False
    
    # 2. Environment o'zgaruvchilarini tekshirish
    print("\n🔧 ENVIRONMENT O'ZGARUVCHILARI:")
    print("-" * 60)
    env_vars = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "ADMIN_TELEGRAM_IDS",
        "ADMIN_PASSWORD",
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
        "ADMIN_BOT_TOKEN",
        "COURIER_BOT_TOKEN",
        "USER_BOT_TOKEN",
        "API_URL"
    ]
    
    for var in env_vars:
        if not check_env_var(var):
            all_ok = False
    
    # 3. Python paketlarini tekshirish
    print("\n📦 PYTHON PAKETLARI:")
    print("-" * 60)
    packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "psycopg2",
        "pydantic",
        "cloudinary",
        "httpx",
        "telegram"
    ]
    
    for package in packages:
        if not check_python_package(package):
            all_ok = False
    
    # 4. PostgreSQL ni tekshirish
    print("\n🗄️ POSTGRESQL:")
    print("-" * 60)
    try:
        result = subprocess.run(
            ["psql", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ PostgreSQL o'rnatilgan: {result.stdout.strip()}")
        else:
            print("❌ PostgreSQL topilmadi!")
            all_ok = False
    except FileNotFoundError:
        print("❌ PostgreSQL topilmadi! O'rnatish kerak.")
        all_ok = False
    except Exception as e:
        print(f"⚠️ PostgreSQL tekshirishda xatolik: {e}")
    
    # 5. Yakuniy xulosa
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ BARCHA TEKSHIRUVLAR MUVAFFAQIYATLI O'TDI!")
        print("\nKeyingi qadamlar:")
        print("1. Backend: uvicorn app.main:app --reload")
        print("2. Botlar: python run_all_bots.py")
    else:
        print("❌ BA'ZI MUAMMOLAR ANIQLANDI!")
        print("\nQuyidagilarni tekshiring:")
        print("- .env fayli to'g'ri to'ldirilganligini")
        print("- requirements.txt dan paketlar o'rnatilganligini: pip install -r requirements.txt")
        print("- PostgreSQL o'rnatilganligini")
    print("=" * 60)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
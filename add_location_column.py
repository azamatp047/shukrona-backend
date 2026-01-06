from sqlalchemy import text
from app.database import engine
import time

def migrate():
    print("Migratsiya boshlanmoqda...")
    try:
        with engine.connect() as conn:
            # Check if column exists first to avoid error
            # PostgreSQL specific check
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='orders' AND column_name='current_location';"))
            if result.fetchone():
                print("Column 'current_location' already exists in 'orders' table. (O'tkazib yuborildi)")
            else:
                conn.execute(text("ALTER TABLE orders ADD COLUMN current_location VARCHAR;"))
                conn.commit()
                print("Muvaffaqiyatli: 'orders' jadvaliga 'current_location' ustuni qo'shildi.")
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    # Bazaga ulanishni kutish (ba'zida productionda baza kechroq yonadi)
    time.sleep(2) 
    migrate()

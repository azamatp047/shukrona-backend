from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.dependencies import require_admin
from app.config import ADMIN_TELEGRAM_IDS, ADMIN_PASSWORD
from app.schemas.admin import AdminCreate

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/login/", summary="Admin tizimiga kirish")
def admin_login(payload: AdminCreate):
    """
    **Admin sifatida autentifikatsiyadan o'tish.**
    
    - **telegram_id**: Telegram ID (Config da bo'lishi kerak).
    - **password**: Maxsus parol.
    """
    telegram_id = payload.telegram_id
    password = payload.password

    if str(password) != str(ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Parol noto'g'ri")

    if str(telegram_id) not in ADMIN_TELEGRAM_IDS:
        raise HTTPException(status_code=403, detail="Siz admin emassiz")
    
    return {"status": "ok", "message": "Kirish muvaffaqiyatli!"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/factory-reset/", summary="Butun bazani tozalash (Admin)")
def factory_reset(db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    """
    **DIQQAT: Bu buyruq barcha ma'lumotlarni o'chirib tashlaydi!**
    
    - Orders, Items, Users, Couriers, Finance, Products hammasi o'chadi.
    - Adminlar o'chmaydi.
    """
    tables = [
        "order_items",
        "order_price_history",
        "salary_payments",
        "expenses",
        "orders",
        "products",
        "users",
        "couriers"
    ]
    
    for table in tables:
        try:
            db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
        except Exception as e:
            print(f"Error truncating {table}: {e}")
            
    db.commit()
    return {"status": "ok", "message": "Ma'lumotlar bazasi muvaffaqiyatli tozalandi!"}
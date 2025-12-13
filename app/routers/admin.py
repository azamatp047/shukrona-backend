from fastapi import APIRouter, HTTPException
from app.config import ADMIN_TELEGRAM_IDS, ADMIN_PASSWORD
from app.schemas.admin import AdminCreate

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/login")
def admin_login(payload: AdminCreate):
    # payload dan ma'lumotlarni olamiz
    telegram_id = payload.telegram_id
    password = payload.password

    # 1. Parol tekshiruvi
    # Configdagi parolni stringga o'tkazib solishtiramiz (har ehtimolga qarshi)
    if str(password) != str(ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Parol noto'g'ri")

    # 2. ID tekshiruvi
    # Kelayotgan ID ni albatta STRING ga aylantirib, keyin ro'yxatdan qidiramiz
    if str(telegram_id) not in ADMIN_TELEGRAM_IDS:
        raise HTTPException(status_code=403, detail="Siz admin emassiz")
    
    return {"status": "ok", "message": "Kirish muvaffaqiyatli!"}
from fastapi import APIRouter, HTTPException
from app.config import ADMIN_TELEGRAM_IDS, ADMIN_PASSWORD

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/login")
def admin_login(telegram_id: int, password: str):
    if telegram_id not in ADMIN_TELEGRAM_IDS:
        raise HTTPException(status_code=403, detail="Siz admin emassiz")
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Parol noto'g'ri")
    return {"status": "ok", "message": "Kirish muvaffaqiyatli!"}

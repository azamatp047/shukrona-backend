from fastapi import Header, HTTPException
from app.config import ADMIN_TELEGRAM_IDS

def require_admin(x_telegram_id: str = Header(..., alias="X-Telegram-ID")):
    # Ikkala tomon ham STRING ekanligiga ishonch hosil qilamiz
    if str(x_telegram_id) not in ADMIN_TELEGRAM_IDS:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan. Faqat adminlar uchun.")
    return x_telegram_id
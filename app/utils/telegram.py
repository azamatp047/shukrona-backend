import os
import httpx
import logging
from dotenv import load_dotenv

# .env faylini qidirish (app/utils/telegram.py dan 2 qavat tepada)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(project_root, ".env")

# Birinchi loyiha ildizidan, keyin joriy papkadan qidiradi
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Logger sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tokenlar - .env dagi nomlarni tekshiring!
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT")
COURIER_USER_BOT_TOKEN = os.getenv("COURIER_USER_BOT")

if not ADMIN_BOT_TOKEN:
    logger.error("!!! ERROR: ADMIN_BOT topilmadi. .env faylini tekshiring !!!")
if not COURIER_USER_BOT_TOKEN:
    logger.error("!!! ERROR: COURIER_USER_BOT topilmadi. .env faylini tekshiring !!!")

BACKEND_URL = os.getenv("BACKEND_URL")

# Admin IDs (ro'yxat sifatida)
try:
    admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
    # Sort qilingan admin IDlar
    ADMIN_IDS = sorted([int(x.strip()) for x in admin_ids_str.split(",") if x.strip()])
except Exception:
    ADMIN_IDS = []

async def send_telegram_request(method: str, token: str, payload: dict):
    """Base Telegram API request helper"""
    if not token:
        logger.warning(f"Telegram Request ignored: No token provided for {method}")
        return None
        
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code != 200:
                logger.error(f"Telegram API Error ({method}): {response.text}")
            return response
        except Exception as e:
            logger.error(f"Telegram connection error in {method}: {e}")
            return None

async def send_telegram_message(token: str, chat_id: str | int, text: str, reply_markup: dict = None):
    """API orqali xabar yuborish"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await send_telegram_request("sendMessage", token, payload)

async def delete_telegram_message(token: str, chat_id: str | int, message_id: int):
    """Xabarni uchirish"""
    payload = {"chat_id": chat_id, "message_id": message_id}
    return await send_telegram_request("deleteMessage", token, payload)

# --- BACKEND INTERACTION HELPERS (bot.py uchun) ---

def get_admin_headers(telegram_id: int = None):
    """Backend uchun headerlarni tayyorlash"""
    # Agar telegram_id berilmasa, .env dagi birinchi admin ishlatiladi
    ti_id = telegram_id or (ADMIN_IDS[0] if ADMIN_IDS else 0)
    return {
        "accept": "application/json",
        "X-Telegram-ID": str(ti_id),
        "Content-Type": "application/json"
    }

async def get_couriers():
    """Kuryerlar ro'yxatini backenddan olish"""
    url = f"{BACKEND_URL}/couriers/"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_admin_headers())
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error fetching couriers: {e}")
            return []

async def assign_order_to_courier(order_id: int, courier_id: int, admin_tg_id: int = None):
    """Buyurtmani kuryerga biriktirish (PATCH)"""
    url = f"{BACKEND_URL}/orders/{order_id}/assign/"
    payload = {"courier_id": courier_id}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(url, json=payload, headers=get_admin_headers(admin_tg_id))
            return response
        except Exception as e:
            logger.error(f"Error assigning courier: {e}")
            return None

# --- NOTIFICATION HELPERS (Backend uchun) ---

async def notify_admins_new_order(order_data: dict):
    """Yangi buyurtma tushganda admin-bot orqali xabar berish"""
    msg = (
        f"🆕 <b>Yangi Buyurtma #{order_data['id']}</b>\n\n"
        f"👤 Mijoz: {order_data.get('user_name', 'Noma\'lum')}\n"
        f"📞 Tel: {order_data.get('user_phone')}\n"
        f"📍 Manzil: {order_data.get('user_address')}\n"
        f"💰 Summa: {order_data.get('total_amount', 0):,} so'm\n"
    )
    
    # Inline tugma: Kuryer biriktirish logic (bot.py da callback_data: list_couriers_{id} handle qilinishi kerak)
    kb = {
        "inline_keyboard": [[
            {"text": "🚚 Kuryer biriktirish", "callback_data": f"list_couriers_{order_data['id']}"}
        ]]
    }

    for admin_id in ADMIN_IDS:
        await send_telegram_message(ADMIN_BOT_TOKEN, admin_id, msg, reply_markup=kb)

async def notify_courier_assigned(courier_telegram_id: str, order_data: dict):
    """Kuryerga xabar berish (courier-user-bot orqali)"""
    msg = (
        f"✅ <b>Sizga yangi buyurtma biriktirildi!</b>\n"
        f"🆔 Order: #{order_data['id']}\n"
        f"📍 Manzil: {order_data.get('user_address')}\n"
        f"📞 Mijoz: {order_data.get('user_phone')}\n"
    )
    
    kb = {
        "inline_keyboard": [[
            {"text": "✅ Qabul qilish", "callback_data": f"accept_{order_data['id']}"}
        ]]
    }
    
    await send_telegram_message(COURIER_USER_BOT_TOKEN, courier_telegram_id, msg, reply_markup=kb)

async def notify_user_courier_assigned(user_telegram_id: str, order_id: int):
    """Mijozga buyurtma kuryerga berilgani haqida (courier-user-bot orqali)"""
    msg = f"ℹ️ <b>Buyurtma #{order_id}</b> admin tomonidan tasdiqlandi va kuryer biriktirildi."
    await send_telegram_message(COURIER_USER_BOT_TOKEN, user_telegram_id, msg)

async def notify_user_courier_accepted(user_telegram_id: str, order_id: int, delivery_time: str, courier_info: str = None):
    """Mijozga kuryer yo'lga chiqqani haqida (courier-user-bot orqali)"""
    c_info = f"\n🛵 Kuryer: {courier_info}" if courier_info else ""
    msg = (
        f"🚀 <b>Buyurtma #{order_id} yo'lga chiqdi!</b>\n"
        f"⏳ Yetkazish vaqti: {delivery_time}{c_info}\n\n"
        f"Bizni tanlaganingiz uchun rahmat!"
    )
    await send_telegram_message(COURIER_USER_BOT_TOKEN, user_telegram_id, msg)

async def notify_user_delivered(user_telegram_id: str, order_id: int):
    """Mijozga buyurtma yetkazilgani haqida"""
    msg = f"✅ <b>Buyurtma #{order_id} yetkazib berildi!</b>\n Katta rahmat! 😋"
    await send_telegram_message(COURIER_USER_BOT_TOKEN, user_telegram_id, msg)

async def notify_admin_delivered(order_id: int, courier_name: str):
    """Adminga buyurtma bitgani haqida (admin-bot orqali)"""
    msg = f"🏁 <b>Order #{order_id} yetkazildi.</b>\n🛵 Kuryer: {courier_name}"
    for admin_id in ADMIN_IDS:
        await send_telegram_message(ADMIN_BOT_TOKEN, admin_id, msg)

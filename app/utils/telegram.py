import os
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()

# Logger sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tokenlar
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin IDs (ro'yxat sifatida)
try:
    admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
except Exception:
    ADMIN_IDS = []

async def send_telegram_message(token: str, chat_id: str | int, text: str, reply_markup: dict = None):
    """
    Telegram API orqali xabar yuborish.
    """
    if not token or not chat_id:
        logger.warning(f"Message not sent: Token={bool(token)}, ChatID={chat_id}")
        return None

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=5.0)
            if response.status_code != 200:
                logger.error(f"Telegram API Error: {response.text}")
            return response
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return None

# --- NOTIFICATION HELPERS ---

async def notify_admins_new_order(order_data: dict):
    """
    Yangi buyurtma tushganda adminlarga xabar berish.
    """
    msg = (
        f"🆕 <b>Yangi Buyurtma #{order_data['id']}</b>\n\n"
        f"👤 Mijoz: {order_data.get('user_name', 'Noma\'lum')}\n"
        f"📞 Tel: {order_data.get('user_phone')}\n"
        f"📍 Manzil: {order_data.get('user_address')}\n"
        f"💰 Summa: {order_data.get('total_amount'):,} so'm\n"
    )
    
    # Inline tugma: Kuryer biriktirish
    kb = {
        "inline_keyboard": [[
            {"text": "🚚 Kuryer biriktirish", "callback_data": f"assign_{order_data['id']}"}
        ]]
    }

    for admin_id in ADMIN_IDS:
        await send_telegram_message(BOT_TOKEN, admin_id, msg, reply_markup=kb)

async def notify_courier_assigned(courier_telegram_id: str, order_data: dict):
    """
    Kuryerga buyurtma biriktirilganda xabar berish.
    """
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
    
    await send_telegram_message(BOT_TOKEN, courier_telegram_id, msg, reply_markup=kb)

async def notify_user_courier_assigned(user_telegram_id: str, order_id: int):
    """
    Mijozga: Buyurtmangiz admin tomonidan ko'rildi va kuryerga berildi (lekin hali kuryer qabul qilmadi).
    """
    msg = f"ℹ️ <b>Buyurtma #{order_id}</b> admin tomonidan tasdiqlandi va kuryer qidirilmoqda."
    await send_telegram_message(BOT_TOKEN, user_telegram_id, msg)

async def notify_user_courier_accepted(user_telegram_id: str, order_id: int, delivery_time: str, courier_info: str = None):
    """
    Mijozga: Kuryer buyurtmani oldi va yo'lga chiqdi.
    """
    c_info = f"\n🛵 Kuryer: {courier_info}" if courier_info else ""
    msg = (
        f"🚀 <b>Buyurtma #{order_id} yo'lga chiqdi!</b>\n"
        f"⏳ Yetkazish vaqti: {delivery_time}{c_info}\n\n"
        f"Bizni tanlaganingiz uchun rahmat!"
    )
    await send_telegram_message(BOT_TOKEN, user_telegram_id, msg)

async def notify_user_delivered(user_telegram_id: str, order_id: int):
    """
    Mijozga buyurtma yetkazilganda.
    """
    msg = f"✅ <b>Buyurtma #{order_id} yetkazib berildi!</b>\n Katta rahmat! 😋"
    await send_telegram_message(BOT_TOKEN, user_telegram_id, msg)

async def notify_admin_delivered(order_id: int, courier_name: str):
    """
    Adminga buyurtma yopilgani haqida.
    """
    msg = f"🏁 <b>Order #{order_id} yetkazildi.</b>\n🛵 Kuryer: {courier_name}"
    for admin_id in ADMIN_IDS:
        await send_telegram_message(BOT_TOKEN, admin_id, msg)

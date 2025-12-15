import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- SOZLAMALAR ---
API_URL = "http://localhost:8000"
# BOTFATHERDAN OLINGAN ADMIN BOT TOKENI
BOT_TOKEN = "8505195609:AAF8rLrqwv2RwwreKls6U0a5GLLoozIYhJc"
ADMIN_IDS = [5111382924, 8324895] # Adminlarning Telegram ID lari

logging.basicConfig(level=logging.INFO)

async def make_request(method, endpoint, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{API_URL}/{endpoint}"
        if method == "GET": return await client.get(url, params=data)
        if method == "PATCH": return await client.patch(url, json=data)
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ Sizga ruxsat yo'q.")
        return

    kb = ReplyKeyboardMarkup([["📦 Yangi buyurtmalar", "🔄 Refresh"]], resize_keyboard=True)
    await update.message.reply_text("Admin Panelga xush kelibsiz!", reply_markup=kb)

async def check_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return

    # Faqat statusi 'created' bo'lgan buyurtmalarni olamiz
    response = await make_request("GET", "orders/", data={"status": "created"})
    if response and response.status_code == 200:
        orders = response.json()
        if not orders:
            await update.message.reply_text("Yangi buyurtmalar yo'q.")
            return

        for order in orders:
            msg = (f"🆕 <b>Order #{order['id']}</b>\n"
                   f"👤 {order['user']['name']}\n"
                   f"📦 {order['product']['name']}\n"
                   f"📍 {order['user']['address']}")
            
            kb = [[InlineKeyboardButton("🚚 Kuryer biriktirish", callback_data=f"assign_{order['id']}")]]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await update.message.reply_text("Baza bilan aloqa yo'q.")

async def assign_courier_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("_")[1]
    
    # Kuryerlar ro'yxatini olish
    response = await make_request("GET", "couriers/")
    if response and response.status_code == 200:
        couriers = response.json()
        if not couriers:
            await query.message.edit_text("Kuryerlar topilmadi.")
            return
            
        kb = []
        for c in couriers:
            kb.append([InlineKeyboardButton(f"🛵 {c['name']}", callback_data=f"setcourier_{order_id}_{c['id']}")])
        
        await query.message.edit_text(f"Order #{order_id} uchun kuryer tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def set_courier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, order_id, courier_id = query.data.split("_")
    
    resp = await make_request("PATCH", f"orders/{order_id}/assign", data={"courier_id": int(courier_id)})
    
    if resp and resp.status_code == 200:
        await query.message.edit_text(f"✅ Order #{order_id} kuryerga biriktirildi.")
    else:
        await query.message.edit_text("Xatolik yuz berdi.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^(📦 Yangi buyurtmalar|🔄 Refresh)$"), check_orders))
    app.add_handler(CallbackQueryHandler(assign_courier_menu, pattern="^assign_"))
    app.add_handler(CallbackQueryHandler(set_courier, pattern="^setcourier_"))
    
    print("Admin Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
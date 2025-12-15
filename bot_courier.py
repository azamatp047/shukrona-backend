import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- SOZLAMALAR ---
API_URL = "http://localhost:8000"
# BOTFATHERDAN OLINGAN COURIER BOT TOKENI
BOT_TOKEN = "8528222994:AAFxLPtNGVzZNanSL1l8TaYzRgOrGLmNclQ"

logging.basicConfig(level=logging.INFO)

# Vaqtincha xotira (vaqt kiritish uchun)
courier_states = {} 

async def make_request(method, endpoint, data=None):
    async with httpx.AsyncClient() as client:
        url = f"{API_URL}/{endpoint}"
        if method == "GET": return await client.get(url, params=data)
        if method == "PATCH": return await client.patch(url, json=data)
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Kuryer bazada bormi tekshiramiz
    response = await make_request("GET", "couriers/")
    is_courier = False
    if response and response.status_code == 200:
        for c in response.json():
            if str(c.get("telegram_id")) == user_id:
                is_courier = True
                break
    
    if is_courier:
        kb = ReplyKeyboardMarkup([["📋 Mening buyurtmalarim"]], resize_keyboard=True)
        await update.message.reply_text("Ishga kirishamizmi?", reply_markup=kb)
    else:
        await update.message.reply_text("❌ Siz kuryer emassiz.")

async def check_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kuryerning o'z ID sini topish
    all_couriers = (await make_request("GET", "couriers/")).json()
    my_courier_id = next((c['id'] for c in all_couriers if str(c['telegram_id']) == str(update.effective_user.id)), None)
    
    if not my_courier_id: return

    # Faqat menga biriktirilgan (assigned) buyurtmalar
    response = await make_request("GET", "orders/") # Bu yerda filtrlash logikasi backendda bo'lishi kerak aslida
    if response:
        orders = response.json()
        my_orders = [o for o in orders if o.get('courier_id') == my_courier_id and o['status'] == 'assigned']
        
        if not my_orders:
            await update.message.reply_text("Aktiv buyurtmalar yo'q.")
            return

        for order in my_orders:
            kb = [[InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{order['id']}")]]
            await update.message.reply_text(
                f"📦 <b>Order #{order['id']}</b>\n📍 {order['user']['address']}",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
            )

async def accept_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[1])
    
    courier_states[update.effective_user.id] = {"order_id": order_id, "state": "WAITING_TIME"}
    await query.message.reply_text(f"Order #{order_id} qabul qilindi.\nQancha vaqtda yetkazasiz? (yozing):")

async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in courier_states and courier_states[user_id]["state"] == "WAITING_TIME":
        time_text = update.message.text
        order_id = courier_states[user_id]["order_id"]
        
        await make_request("PATCH", f"orders/{order_id}/accept", data={"delivery_time": time_text})
        
        del courier_states[user_id] # State tozalash
        
        kb = [[InlineKeyboardButton("🏁 Yetkazib berildi", callback_data=f"finish_{order_id}")]]
        await update.message.reply_text(f"Vaqt: {time_text} belgilandi. Yetkazgach tugmani bosing:", reply_markup=InlineKeyboardMarkup(kb))

async def finish_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("_")[1]
    
    await make_request("PATCH", f"orders/{order_id}/deliver")
    await query.message.edit_text(f"✅ Order #{order_id} yetkazildi. Rahmat!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📋 Mening buyurtmalarim$"), check_my_orders))
    app.add_handler(CallbackQueryHandler(accept_order, pattern="^accept_"))
    app.add_handler(CallbackQueryHandler(finish_order, pattern="^finish_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, time_handler))
    
    print("Courier Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
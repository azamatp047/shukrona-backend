import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# --- SOZLAMALAR ---
API_URL = "http://localhost:8000"
# BOTFATHERDAN OLINGAN USER BOT TOKENI
BOT_TOKEN = "8371889300:AAGk4mlR4CQ4GsHkXH-e-KhhMVy7qEycEiE" 

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Holatlar
NAME, PHONE, ADDRESS = range(3)

# --- REQUEST FUNKSIYASI ---
async def make_request(method, endpoint, data=None, params=None):
    async with httpx.AsyncClient() as client:
        try:
            url = f"{API_URL}/{endpoint}"
            if method == "GET":
                response = await client.get(url, params=params, timeout=10.0)
            elif method == "POST":
                response = await client.post(url, json=data, timeout=10.0)
            return response
        except Exception as e:
            logger.error(f"API Error: {e}")
            return None

# --- START & REGISTRATION ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Bazadan tekshirish
    response = await make_request("GET", "users/")
    existing_user = None
    if response and response.status_code == 200:
        users = response.json()
        existing_user = next((u for u in users if str(u.get("telegram_id")) == telegram_id), None)
    
    if existing_user:
        await update.message.reply_text(
            f"Xush kelibsiz, {existing_user['name']}!",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Assalomu alaykum! Ismingizni kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME

def get_main_menu():
    return ReplyKeyboardMarkup([
        ["🛍 Buyurtma berish", "👤 Profil"],
        ["📞 Biz bilan aloqa"]
    ], resize_keyboard=True)

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        context.user_data['phone'] = update.message.contact.phone_number
    else:
        context.user_data['phone'] = update.message.text
    
    await update.message.reply_text("Manzilingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    
    user_data = {
        "name": context.user_data['name'],
        "phone": context.user_data['phone'],
        "address": context.user_data['address'],
        "telegram_id": str(update.effective_user.id)
    }
    
    response = await make_request("POST", "users/", data=user_data)
    if response and response.status_code in [200, 201]:
        await update.message.reply_text("✅ Ro'yxatdan o'tdingiz!", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("⚠️ Xatolik. /start ni bosing.")
    return ConversationHandler.END

# --- BUYURTMA QISMI ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)

    if text == "🛍 Buyurtma berish":
        response = await make_request("GET", "products/")
        if response and response.status_code == 200:
            products = response.json()
            if not products:
                await update.message.reply_text("Mahsulotlar yo'q.")
                return
            
            keyboard = [[InlineKeyboardButton(f"{p['name']} - {p['price']} so'm", callback_data=f"prod_{p['id']}")] for p in products]
            await update.message.reply_text("Mahsulotni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("Xatolik yuz berdi.")

    elif text == "👤 Profil":
        # User ma'lumotlarini olish logikasi shu yerda bo'ladi
        await update.message.reply_text(f"Sizning ID: {user_id}")

    elif text == "📞 Biz bilan aloqa":
        await update.message.reply_text("Admin: +998901234567")

async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("prod_"):
        prod_id = query.data.split("_")[1]
        kb = [
            [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_{prod_id}")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")]
        ]
        await query.message.edit_text("Buyurtmani tasdiqlaysizmi?", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("confirm_"):
        prod_id = int(query.data.split("_")[1])
        # User ID ni bazadan olish kerak (telegram_id orqali)
        # Soddalashtirish uchun bu yerda avval user listdan qidiramiz
        all_users = (await make_request("GET", "users/")).json()
        user_db = next((u for u in all_users if str(u['telegram_id']) == str(update.effective_user.id)), None)
        
        if user_db:
            order_data = {"user_id": user_db['id'], "product_id": prod_id}
            resp = await make_request("POST", "orders/", data=order_data)
            if resp and resp.status_code == 201:
                order_id = resp.json()['id']
                await query.message.edit_text(f"✅ Buyurtma qabul qilindi! ID: #{order_id}\nTez orada aloqaga chiqamiz.")
            else:
                await query.message.edit_text("Xatolik yuz berdi.")
        else:
            await query.message.edit_text("Foydalanuvchi topilmadi. /start bosing.")

    elif query.data == "cancel":
        await query.message.delete()
        await query.message.reply_text("Buyurtma bekor qilindi.", reply_markup=get_main_menu())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT, get_name)],
            PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, get_phone)],
            ADDRESS: [MessageHandler(filters.TEXT, get_address)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(product_callback))
    
    print("User Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
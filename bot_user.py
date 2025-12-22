import os
import httpx
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
USER_BOT_TOKEN = os.getenv("USER_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ========== KEYBOARD HELPERS ==========
def main_menu_keyboard():
    """Asosiy menyu klaviaturasi"""
    keyboard = [
        [KeyboardButton("🛒 Buyurtma berish")],
        [KeyboardButton("📦 Mening buyurtmalarim"), KeyboardButton("👤 Profil")],
        [KeyboardButton("📞 Bog'lanish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_keyboard():
    """Bekor qilish klaviaturasi"""
    keyboard = [[KeyboardButton("❌ Bekor qilish")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== START COMMAND ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot /start buyrug'i - Foydalanuvchini ro'yxatdan o'tkazish"""
    user = update.effective_user
    
    # Foydalanuvchini API ga yuborish
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_URL}/users/", json={
                "telegram_id": str(user.id),
                "name": user.full_name or "Foydalanuvchi",
                "phone": "Kiritilmagan",
                "address": "Kiritilmagan"
            }, timeout=10.0)
            
            if response.status_code in [200, 201]:
                await update.message.reply_text(
                    f"👋 Assalomu alaykum, {user.first_name}!\n\n"
                    "🍽 Shukrona Delivery botiga xush kelibsiz!\n\n"
                    "Buyurtma berish uchun quyidagi menyudan foydalaning.",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring: /start"
                )
        except Exception as e:
            logger.error(f"Start error: {e}")
            await update.message.reply_text(
                "❌ Serverga ulanishda xatolik. Iltimos qaytadan urinib ko'ring."
            )

# ========== PROFIL ==========
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi profilini ko'rsatish"""
    user = update.effective_user
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/users/me/{user.id}", timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                
                profile_text = (
                    f"👤 <b>Profil ma'lumotlari</b>\n\n"
                    f"📛 Ism: {data['name']}\n"
                    f"📞 Telefon: {data['phone']}\n"
                    f"📍 Manzil: {data['address']}\n"
                    f"🆔 Telegram ID: {data['telegram_id']}\n"
                    f"📊 Status: {data['status']}"
                )
                
                keyboard = [[InlineKeyboardButton("✏️ Profilni yangilash", callback_data="update_profile")]]
                
                await update.message.reply_text(
                    profile_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ Profilni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Profile error: {e}")
            await update.message.reply_text("❌ Serverga ulanishda xatolik.")

# ========== PROFIL YANGILASH ==========
async def update_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profilni yangilash jarayonini boshlash"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['updating_profile'] = True
    context.user_data['profile_step'] = 'name'
    
    await query.edit_message_text(
        "✏️ <b>Profilni yangilash</b>\n\n"
        "Iltimos, yangi ismingizni kiriting:",
        parse_mode="HTML"
    )

async def handle_profile_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profil yangilash ma'lumotlarini qabul qilish"""
    if not context.user_data.get('updating_profile'):
        return
    
    text = update.message.text
    step = context.user_data.get('profile_step')
    
    if step == 'name':
        context.user_data['new_name'] = text
        context.user_data['profile_step'] = 'phone'
        await update.message.reply_text("📞 Telefon raqamingizni kiriting (Format: +998901234567):")
    
    elif step == 'phone':
        context.user_data['new_phone'] = text
        context.user_data['profile_step'] = 'address'
        await update.message.reply_text("📍 Manzilingizni kiriting (masalan: Chilonzor, 12-kvartal):")
    
    elif step == 'address':
        context.user_data['new_address'] = text
        
        # API ga yangilash so'rovi
        user = update.effective_user
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    f"{API_URL}/users/me/{user.id}",
                    json={
                        "name": context.user_data['new_name'],
                        "phone": context.user_data['new_phone'],
                        "address": context.user_data['new_address']
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    await update.message.reply_text(
                        "✅ Profil muvaffaqiyatli yangilandi!",
                        reply_markup=main_menu_keyboard()
                    )
                else:
                    await update.message.reply_text("❌ Yangilashda xatolik yuz berdi.")
            except Exception as e:
                logger.error(f"Update profile error: {e}")
                await update.message.reply_text("❌ Serverga ulanishda xatolik.")
        
        # Tozalash
        context.user_data.clear()

# ========== BUYURTMA BERISH ==========
async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtma berish jarayonini boshlash"""
    user = update.effective_user
    
    # Mahsulotlarni olish
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/products/", timeout=10.0)
            
            if response.status_code == 200:
                products = response.json()
                
                if not products:
                    await update.message.reply_text("❌ Hozirda mavjud mahsulotlar yo'q.")
                    return
                
                context.user_data['products'] = products
                context.user_data['cart'] = []
                context.user_data['ordering'] = True
                
                # Mahsulotlarni ko'rsatish
                keyboard = []
                for p in products:
                    keyboard.append([InlineKeyboardButton(
                        f"{p['name']} - {p['stock']} ta mavjud",
                        callback_data=f"select_product_{p['id']}"
                    )])
                keyboard.append([InlineKeyboardButton("✅ Savatni tasdiqlash", callback_data="confirm_cart")])
                keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_order")])
                
                await update.message.reply_text(
                    "🛒 <b>Buyurtma berish</b>\n\n"
                    "Mahsulotlarni tanlang:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ Mahsulotlarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Start order error: {e}")
            await update.message.reply_text("❌ Serverga ulanishda xatolik.")

async def select_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mahsulot tanlash"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split("_")[2])
    products = context.user_data.get('products', [])
    
    product = next((p for p in products if p['id'] == product_id), None)
    
    if not product:
        await query.edit_message_text("❌ Mahsulot topilmadi.")
        return
    
    context.user_data['selected_product'] = product
    context.user_data['awaiting_quantity'] = True
    
    await query.edit_message_text(
        f"📦 <b>{product['name']}</b>\n\n"
        f"Mavjud: {product['stock']} ta\n\n"
        f"Nechta olmoqchisiz? (Sonni kiriting)",
        parse_mode="HTML"
    )

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mahsulot sonini qabul qilish"""
    if not context.user_data.get('awaiting_quantity'):
        return
    
    try:
        quantity = int(update.message.text)
        
        if quantity <= 0:
            await update.message.reply_text("❌ Son 0 dan katta bo'lishi kerak.")
            return
        
        product = context.user_data['selected_product']
        
        if quantity > product['stock']:
            await update.message.reply_text(f"❌ Omborda faqat {product['stock']} ta mavjud.")
            return
        
        # Savatga qo'shish
        cart = context.user_data.get('cart', [])
        
        # Agar mahsulot allaqachon savatda bo'lsa, sonini yangilash
        existing = next((item for item in cart if item['product_id'] == product['id']), None)
        if existing:
            existing['quantity'] += quantity
        else:
            cart.append({
                'product_id': product['id'],
                'quantity': quantity,
                'name': product['name']
            })
        
        context.user_data['cart'] = cart
        context.user_data['awaiting_quantity'] = False
        
        await update.message.reply_text(
            f"✅ {product['name']} ({quantity} ta) savatga qo'shildi!\n\n"
            "Yana mahsulot qo'shish uchun: /order\n"
            "Buyurtmani tasdiqlash uchun: /confirm"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Iltimos, to'g'ri son kiriting.")

async def confirm_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Savatni tasdiqlash"""
    query = update.callback_query
    await query.answer()
    
    cart = context.user_data.get('cart', [])
    
    if not cart:
        await query.edit_message_text("❌ Savat bo'sh. Avval mahsulot tanlang.")
        return
    
    # Savat ro'yxatini ko'rsatish
    cart_text = "🛒 <b>Sizning savatingiz:</b>\n\n"
    for item in cart:
        cart_text += f"• {item['name']} - {item['quantity']} ta\n"
    
    keyboard = [
        [InlineKeyboardButton("✅ Buyurtmani tasdiqlash", callback_data="finalize_order")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_order")]
    ]
    
    await query.edit_message_text(
        cart_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def finalize_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtmani yakunlash va API ga yuborish"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    cart = context.user_data.get('cart', [])
    
    if not cart:
        await query.edit_message_text("❌ Savat bo'sh.")
        return
    
    # API ga buyurtma yuborish
    items = [{"product_id": item['product_id'], "quantity": item['quantity']} for item in cart]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/orders/",
                json={"telegram_id": str(user.id), "items": items},
                timeout=10.0
            )
            
            if response.status_code == 201:
                order_data = response.json()
                
                await query.edit_message_text(
                    f"✅ <b>Buyurtma muvaffaqiyatli qabul qilindi!</b>\n\n"
                    f"🆔 Buyurtma raqami: #{order_data['id']}\n"
                    f"💰 Jami summa: {order_data['total_amount']:,} so'm\n\n"
                    f"📞 Tez orada operator siz bilan bog'lanadi.",
                    parse_mode="HTML"
                )
                
                # Savatni tozalash
                context.user_data.clear()
            else:
                error_detail = response.json().get('detail', 'Noma\'lum xatolik')
                await query.edit_message_text(f"❌ Buyurtma berishda xatolik: {error_detail}")
        except Exception as e:
            logger.error(f"Finalize order error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

async def cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtmani bekor qilish"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    await query.edit_message_text("❌ Buyurtma bekor qilindi.", reply_markup=main_menu_keyboard())

# ========== BUYURTMALARNI KO'RISH ==========
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi buyurtmalarini ko'rsatish"""
    user = update.effective_user
    
    async with httpx.AsyncClient() as client:
        try:
            # Foydalanuvchi ID sini olish
            user_response = await client.get(f"{API_URL}/users/me/{user.id}", timeout=10.0)
            
            if user_response.status_code != 200:
                await update.message.reply_text("❌ Foydalanuvchi ma'lumotlari topilmadi.")
                return
            
            user_data = user_response.json()
            user_id = user_data['id']
            
            # Buyurtmalarni olish
            orders_response = await client.get(
                f"{API_URL}/orders/?user_id={user_id}",
                timeout=10.0
            )
            
            if orders_response.status_code == 200:
                orders = orders_response.json()
                
                if not orders:
                    await update.message.reply_text("📭 Sizda hali buyurtmalar yo'q.")
                    return
                
                for order in orders[:5]:  # Oxirgi 5 ta
                    status_emoji = {
                        'kutilmoqda': '⏳',
                        'kuryerda': '🚚',
                        'yetkazildi': '✅'
                    }
                    
                    order_text = (
                        f"{status_emoji.get(order['status'], '📦')} <b>Buyurtma #{order['id']}</b>\n\n"
                        f"Status: {order['status']}\n"
                        f"💰 Summa: {order['total_amount']:,} so'm\n"
                    )
                    
                    if order['delivery_time']:
                        order_text += f"⏰ Yetkazish vaqti: {order['delivery_time']}\n"
                    
                    if order['courier_name']:
                        order_text += f"🛵 Kuryer: {order['courier_name']}\n"
                    
                    await update.message.reply_text(order_text, parse_mode="HTML")
            else:
                await update.message.reply_text("❌ Buyurtmalarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"My orders error: {e}")
            await update.message.reply_text("❌ Serverga ulanishda xatolik.")

# ========== KONTAKT ==========
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kontakt ma'lumotlari"""
    contact_text = (
        "📞 <b>Biz bilan bog'lanish:</b>\n\n"
        "☎️ Telefon: +998 90 123 45 67\n"
        "📧 Email: info@shukrona.uz\n"
        "🌐 Veb-sayt: www.shukrona.uz\n\n"
        "🕐 Ish vaqti: 09:00 - 22:00"
    )
    await update.message.reply_text(contact_text, parse_mode="HTML")

# ========== TEXT HANDLER ==========
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn xabarlarini boshqarish"""
    text = update.message.text
    
    # Profil yangilash jarayonida
    if context.user_data.get('updating_profile'):
        await handle_profile_update(update, context)
        return
    
    # Mahsulot soni kiritish jarayonida
    if context.user_data.get('awaiting_quantity'):
        await handle_quantity(update, context)
        return
    
    # Menyu tugmalari
    if text == "🛒 Buyurtma berish":
        await start_order(update, context)
    elif text == "📦 Mening buyurtmalarim":
        await my_orders(update, context)
    elif text == "👤 Profil":
        await profile(update, context)
    elif text == "📞 Bog'lanish":
        await contact(update, context)
    elif text == "❌ Bekor qilish":
        context.user_data.clear()
        await update.message.reply_text("❌ Jarayon bekor qilindi.", reply_markup=main_menu_keyboard())

# ========== CALLBACK HANDLER ==========
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query larni boshqarish"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("select_product_"):
        await select_product_callback(update, context)
    elif data == "confirm_cart":
        await confirm_cart_callback(update, context)
    elif data == "finalize_order":
        await finalize_order_callback(update, context)
    elif data == "cancel_order":
        await cancel_order_callback(update, context)
    elif data == "update_profile":
        await update_profile_callback(update, context)

# ========== MAIN ==========
def main():
    """Botni ishga tushirish"""
    application = Application.builder().token(USER_BOT_TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("order", start_order))
    application.add_handler(CommandHandler("confirm", confirm_cart_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("User bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
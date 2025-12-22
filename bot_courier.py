import os
import httpx
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
COURIER_BOT_TOKEN = os.getenv("COURIER_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ========== KEYBOARD HELPERS ==========
def main_menu_keyboard():
    """Asosiy menyu klaviaturasi"""
    keyboard = [
        [KeyboardButton("📋 Mening buyurtmalarim")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("👤 Profil")],
        [KeyboardButton("📞 Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuryer /start buyrug'i"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"👋 Assalomu alaykum, {user.first_name}!\n\n"
        "🚚 Shukrona Delivery kuryer botiga xush kelibsiz!\n\n"
        "📋 Sizga biriktirilgan buyurtmalarni ko'rish va boshqarish uchun quyidagi menyudan foydalaning.",
        reply_markup=main_menu_keyboard()
    )

# ========== MENING BUYURTMALARIM ==========
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuryerga biriktirilgan buyurtmalar"""
    user = update.effective_user
    
    # Kuryer ma'lumotlarini olish
    async with httpx.AsyncClient() as client:
        try:
            # Kuryerni topish
            couriers_response = await client.get(f"{API_URL}/couriers/", timeout=10.0)
            
            if couriers_response.status_code != 200:
                await update.message.reply_text("❌ Kuryer ma'lumotlarini yuklashda xatolik.")
                return
            
            couriers = couriers_response.json()
            courier = next((c for c in couriers if c['telegram_id'] == str(user.id)), None)
            
            if not courier:
                await update.message.reply_text(
                    "❌ Siz tizimda ro'yxatdan o'tmagansiz.\n"
                    "Admin bilan bog'laning."
                )
                return
            
            # Kuryerning buyurtmalarini olish
            orders_response = await client.get(
                f"{API_URL}/orders/?courier_id={courier['id']}",
                timeout=10.0
            )
            
            if orders_response.status_code == 200:
                orders = orders_response.json()
                
                # Statusga qarab ajratish
                pending_orders = [o for o in orders if o['status'] == 'kutilmoqda']
                active_orders = [o for o in orders if o['status'] == 'kuryerda']
                delivered_orders = [o for o in orders if o['status'] == 'yetkazildi']
                
                if not orders:
                    await update.message.reply_text("📭 Sizga hali buyurtmalar biriktirilmagan.")
                    return
                
                # Faol buyurtmalar
                if active_orders:
                    await update.message.reply_text("🚚 <b>Sizda kuryerdagi buyurtmalar:</b>", parse_mode="HTML")
                    for order in active_orders:
                        await send_order_details(update, order, show_deliver_button=True)
                
                # Kutilayotgan buyurtmalar (Admin biriktirgan, lekin kuryer hali qabul qilmagan)
                if pending_orders:
                    await update.message.reply_text("⏳ <b>Qabul qilishingizni kutayotgan buyurtmalar:</b>", parse_mode="HTML")
                    for order in pending_orders:
                        await send_order_details(update, order, show_accept_button=True)
                
                # Yetkazilgan buyurtmalar (oxirgi 3 ta)
                if delivered_orders:
                    await update.message.reply_text("✅ <b>Oxirgi yetkazilgan buyurtmalar:</b>", parse_mode="HTML")
                    for order in delivered_orders[:3]:
                        await send_order_details(update, order)
            
            else:
                await update.message.reply_text("❌ Buyurtmalarni yuklashda xatolik.")
        
        except Exception as e:
            logger.error(f"My orders error: {e}")
            await update.message.reply_text("❌ Serverga ulanishda xatolik.")

async def send_order_details(update: Update, order: dict, show_accept_button: bool = False, show_deliver_button: bool = False):
    """Buyurtma tafsilotlarini yuborish"""
    status_emoji = {
        'kutilmoqda': '⏳',
        'kuryerda': '🚚',
        'yetkazildi': '✅'
    }
    
    order_text = (
        f"{status_emoji.get(order['status'], '📦')} <b>Buyurtma #{order['id']}</b>\n\n"
        f"👤 Mijoz: {order['user_name']}\n"
        f"📞 Telefon: {order['user_phone']}\n"
        f"📍 Manzil: {order['user_address']}\n"
        f"💰 Summa: {order['total_amount']:,} so'm\n"
    )
    
    if order.get('delivery_time'):
        order_text += f"⏰ Yetkazish vaqti: {order['delivery_time']}\n"
    
    # Mahsulotlar
    order_text += "\n<b>Mahsulotlar:</b>\n"
    for item in order['items']:
        order_text += f"  • {item['product_name']} x{item['quantity']}\n"
    
    # Tugmalar
    keyboard = []
    
    if show_accept_button:
        keyboard.append([InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{order['id']}")])
    
    if show_deliver_button:
        keyboard.append([InlineKeyboardButton("🏁 Yetkazildi", callback_data=f"deliver_{order['id']}")])
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            order_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )
    else:
        await update.message.reply_text(
            order_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )

# ========== BUYURTMANI QABUL QILISH ==========
async def accept_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtmani qabul qilish"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split("_")[1])
    
    # Yetkazish vaqtini so'rash
    context.user_data['accepting_order'] = order_id
    
    await query.edit_message_text(
        f"⏰ <b>Buyurtma #{order_id}</b> uchun yetkazish vaqtini kiriting\n\n"
        "Masalan: 30 daqiqa, 1 soat, 45 minut",
        parse_mode="HTML"
    )

async def handle_delivery_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yetkazish vaqtini qabul qilish"""
    if 'accepting_order' not in context.user_data:
        return
    
    order_id = context.user_data['accepting_order']
    delivery_time = update.message.text
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{API_URL}/orders/{order_id}/accept",
                json={"delivery_time": delivery_time},
                timeout=10.0
            )
            
            if response.status_code == 200:
                order_data = response.json()
                
                await update.message.reply_text(
                    f"✅ <b>Buyurtma #{order_id}</b> qabul qilindi!\n\n"
                    f"⏰ Yetkazish vaqti: {delivery_time}\n"
                    f"📍 Manzil: {order_data['user_address']}\n"
                    f"📞 Mijoz: {order_data['user_phone']}\n\n"
                    f"Mijozga xabar yuborildi. Omad!",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard()
                )
                
                # Tozalash
                del context.user_data['accepting_order']
            else:
                error_detail = response.json().get('detail', 'Noma\'lum xatolik')
                await update.message.reply_text(f"❌ Xatolik: {error_detail}")
        except Exception as e:
            logger.error(f"Accept order error: {e}")
            await update.message.reply_text("❌ Serverga ulanishda xatolik.")

# ========== BUYURTMA YETKAZILDI ==========
async def deliver_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtma yetkazildi deb belgilash"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split("_")[1])
    
    # Tasdiqlash
    keyboard = [
        [InlineKeyboardButton("✅ Ha, yetkazildi", callback_data=f"confirm_deliver_{order_id}")],
        [InlineKeyboardButton("❌ Yo'q, ortga", callback_data="cancel_deliver")]
    ]
    
    await query.edit_message_text(
        f"❓ <b>Buyurtma #{order_id}</b> yetkazib berilganini tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_deliver_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yetkazilganini tasdiqlash"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split("_")[2])
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{API_URL}/orders/{order_id}/deliver",
                timeout=10.0
            )
            
            if response.status_code == 200:
                await query.edit_message_text(
                    f"✅ <b>Buyurtma #{order_id}</b> yetkazildi!\n\n"
                    "Ajoyib ish! Mijoz va admin xabardor qilindi.",
                    parse_mode="HTML"
                )
            else:
                error_detail = response.json().get('detail', 'Noma\'lum xatolik')
                await query.edit_message_text(f"❌ Xatolik: {error_detail}")
        except Exception as e:
            logger.error(f"Deliver order error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

async def cancel_deliver_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yetkazishni bekor qilish"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ Bekor qilindi.")

# ========== STATISTIKA ==========
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuryer statistikasini ko'rsatish"""
    user = update.effective_user
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_URL}/couriers/me/history?telegram_id={user.id}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                stats_text = (
                    f"📊 <b>Sizning statistikangiz</b>\n\n"
                    f"👤 Kuryer: {stats['courier_name']}\n"
                    f"✅ Yetkazilgan buyurtmalar: {stats['total_delivered_orders']} ta\n"
                    f"💰 Jami yig'ilgan pul: {stats['total_money_collected']:,} so'm\n\n"
                )
                
                if stats['history']:
                    stats_text += "<b>Oxirgi 5 ta buyurtma:</b>\n"
                    for h in stats['history'][:5]:
                        stats_text += (
                            f"\n  • Order #{h['order_id']}\n"
                            f"    💰 {h['total_amount']:,} so'm\n"
                            f"    📍 {h['user_address']}\n"
                        )
                
                await update.message.reply_text(stats_text, parse_mode="HTML")
            
            else:
                await update.message.reply_text("❌ Statistikani yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Statistics error: {e}")
            await update.message.reply_text("❌ Serverga ulanishda xatolik.")

# ========== PROFIL ==========
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuryer profili"""
    user = update.effective_user
    
    async with httpx.AsyncClient() as client:
        try:
            couriers_response = await client.get(f"{API_URL}/couriers/", timeout=10.0)
            
            if couriers_response.status_code == 200:
                couriers = couriers_response.json()
                courier = next((c for c in couriers if c['telegram_id'] == str(user.id)), None)
                
                if not courier:
                    await update.message.reply_text("❌ Profil topilmadi.")
                    return
                
                profile_text = (
                    f"👤 <b>Profil</b>\n\n"
                    f"📛 Ism: {courier['name']}\n"
                    f"📞 Telefon: {courier.get('phone', 'Kiritilmagan')}\n"
                    f"🆔 Telegram: @{courier.get('tg_username', 'N/A')}\n"
                    f"📊 Status: {courier['status']}\n"
                )
                
                await update.message.reply_text(profile_text, parse_mode="HTML")
            else:
                await update.message.reply_text("❌ Profilni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Profile error: {e}")
            await update.message.reply_text("❌ Serverga ulanishda xatolik.")

# ========== YORDAM ==========
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam ma'lumotlari"""
    help_text = (
        "📚 <b>Yordam</b>\n\n"
        "🚚 <b>Bot qanday ishlaydi?</b>\n"
        "1. Admin sizga buyurtma biriktirganda xabar keladi\n"
        "2. Buyurtmani qabul qiling va yetkazish vaqtini belgilang\n"
        "3. Yetkazib bergandan keyin \"Yetkazildi\" tugmasini bosing\n\n"
        "📋 <b>Buyg'ruqlar:</b>\n"
        "/start - Botni boshlash\n"
        "/orders - Mening buyurtmalarim\n"
        "/stats - Statistika\n"
        "/profile - Profil\n"
        "/help - Yordam\n\n"
        "❓ Savol bo'lsa admin bilan bog'laning:\n"
        "📞 +998 90 123 45 67"
    )
    
    await update.message.reply_text(help_text, parse_mode="HTML")

# ========== TEXT HANDLER ==========
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn xabarlarini boshqarish"""
    text = update.message.text
    
    # Yetkazish vaqtini kiritish jarayonida
    if context.user_data.get('accepting_order'):
        await handle_delivery_time(update, context)
        return
    
    # Menyu tugmalari
    if text == "📋 Mening buyurtmalarim":
        await my_orders(update, context)
    elif text == "📊 Statistika":
        await show_statistics(update, context)
    elif text == "👤 Profil":
        await show_profile(update, context)
    elif text == "📞 Yordam":
        await help_command(update, context)

# ========== CALLBACK HANDLER ==========
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query larni boshqarish"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("accept_"):
        await accept_order_callback(update, context)
    elif data.startswith("deliver_"):
        await deliver_order_callback(update, context)
    elif data.startswith("confirm_deliver_"):
        await confirm_deliver_callback(update, context)
    elif data == "cancel_deliver":
        await cancel_deliver_callback(update, context)

# ========== MAIN ==========
def main():
    """Botni ishga tushirish"""
    application = Application.builder().token(COURIER_BOT_TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("orders", my_orders))
    application.add_handler(CommandHandler("stats", show_statistics))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Courier bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
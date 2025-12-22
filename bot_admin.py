import os
import httpx
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_TELEGRAM_IDS = os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ========== ADMIN TEKSHIRUVI ==========
def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    return str(user_id) in ADMIN_TELEGRAM_IDS

async def require_admin(update: Update) -> bool:
    """Admin bo'lishni talab qilish"""
    user = update.effective_user
    if not is_admin(user.id):
        if update.callback_query:
            await update.callback_query.answer("❌ Ruxsat yo'q!", show_alert=True)
        else:
            await update.message.reply_text("❌ Siz admin emassiz!")
        return False
    return True

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin bot /start buyrug'i"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Siz admin emassiz. Kirish taqiqlanadi.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Kutilayotgan buyurtmalar", callback_data="orders_pending")],
        [InlineKeyboardButton("🚚 Kuryerdagi buyurtmalar", callback_data="orders_courier")],
        [InlineKeyboardButton("✅ Yetkazilganlar", callback_data="orders_delivered")],
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_list")],
        [InlineKeyboardButton("🛵 Kuryerlar", callback_data="couriers_list")],
        [InlineKeyboardButton("📦 Mahsulotlar", callback_data="products_list")],
        [InlineKeyboardButton("💰 Moliyaviy hisobotlar", callback_data="finance_stats")]
    ]
    
    await update.message.reply_text(
        f"👋 Assalomu alaykum, Admin {user.first_name}!\n\n"
        "🎛 <b>Admin Panel</b>\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== BUYURTMALARNI KO'RISH ==========
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str = None):
    """Buyurtmalarni status bo'yicha ko'rsatish"""
    query = update.callback_query
    await query.answer()
    
    if not await require_admin(update):
        return
    
    async with httpx.AsyncClient() as client:
        try:
            url = f"{API_URL}/orders/"
            if status:
                url += f"?status={status}"
            
            headers = {"X-Telegram-ID": str(update.effective_user.id)}
            response = await client.get(url, headers=headers, timeout=15.0)
            
            if response.status_code == 200:
                orders = response.json()
                
                if not orders:
                    await query.edit_message_text(
                        f"📭 {status or 'Hech qanday'} buyurtmalar topilmadi.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")]])
                    )
                    return
                
                # Har bir buyurtma uchun alohida xabar
                for order in orders[:10]:  # Oxirgi 10 ta
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
                        f"📊 Status: {order['status']}\n"
                    )
                    
                    if order.get('courier_name'):
                        order_text += f"🛵 Kuryer: {order['courier_name']}\n"
                    
                    if order.get('delivery_time'):
                        order_text += f"⏰ Yetkazish: {order['delivery_time']}\n"
                    
                    # Mahsulotlar ro'yxati
                    order_text += "\n<b>Mahsulotlar:</b>\n"
                    for item in order['items']:
                        order_text += f"  • {item['product_name']} x{item['quantity']}\n"
                    
                    # Tugmalar
                    keyboard = []
                    
                    if order['status'] == 'kutilmoqda':
                        keyboard.append([InlineKeyboardButton("🚚 Kuryerga biriktirish", callback_data=f"assign_{order['id']}")])
                    
                    await query.message.reply_text(order_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)
                
                # Orqaga tugmasi
                await query.message.reply_text(
                    "Yuqoridagi buyurtmalar ro'yxati.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Bosh menyu", callback_data="back_to_menu")]])
                )
            
            else:
                await query.edit_message_text("❌ Buyurtmalarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Show orders error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

# ========== KURYERGA BIRIKTIRISH ==========
async def assign_courier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtmani kuryerga biriktirish"""
    query = update.callback_query
    await query.answer()
    
    if not await require_admin(update):
        return
    
    order_id = int(query.data.split("_")[1])
    
    # Kuryerlar ro'yxatini olish
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-Telegram-ID": str(update.effective_user.id)}
            response = await client.get(f"{API_URL}/couriers/", headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                couriers = response.json()
                
                if not couriers:
                    await query.edit_message_text("❌ Kuryerlar topilmadi.")
                    return
                
                # Kuryer tanlash tugmalari
                keyboard = []
                for courier in couriers:
                    if courier['status'] == 'active':
                        keyboard.append([InlineKeyboardButton(
                            f"🛵 {courier['name']} - {courier.get('phone', 'Telefon yo\'q')}",
                            callback_data=f"do_assign_{order_id}_{courier['id']}"
                        )])
                
                keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="back_to_menu")])
                
                await query.edit_message_text(
                    f"🚚 <b>Buyurtma #{order_id}</b> uchun kuryer tanlang:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Kuryerlarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Assign courier error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

async def do_assign_courier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuryerni tayinlash amalini bajarish"""
    query = update.callback_query
    await query.answer()
    
    if not await require_admin(update):
        return
    
    parts = query.data.split("_")
    order_id = int(parts[2])
    courier_id = int(parts[3])
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-Telegram-ID": str(update.effective_user.id)}
            response = await client.patch(
                f"{API_URL}/orders/{order_id}/assign",
                json={"courier_id": courier_id},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                order_data = response.json()
                await query.edit_message_text(
                    f"✅ <b>Buyurtma #{order_id}</b> kuryerga biriktirildi!\n\n"
                    f"🛵 Kuryer: {order_data.get('courier_name')}\n"
                    f"📞 Telefon: {order_data.get('courier_phone', 'Yo\'q')}\n\n"
                    f"Kuryer va mijozga xabar yuborildi.",
                    parse_mode="HTML"
                )
            else:
                error_detail = response.json().get('detail', 'Noma\'lum xatolik')
                await query.edit_message_text(f"❌ Xatolik: {error_detail}")
        except Exception as e:
            logger.error(f"Do assign error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

# ========== FOYDALANUVCHILAR ==========
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchilar ro'yxati"""
    query = update.callback_query
    await query.answer()
    
    if not await require_admin(update):
        return
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-Telegram-ID": str(update.effective_user.id)}
            response = await client.get(f"{API_URL}/users/", headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                users = response.json()
                
                if not users:
                    await query.edit_message_text("📭 Foydalanuvchilar topilmadi.")
                    return
                
                users_text = "👥 <b>Foydalanuvchilar ro'yxati:</b>\n\n"
                
                for user in users[:20]:
                    status_emoji = "✅" if user['status'] == 'active' else "🚫"
                    users_text += (
                        f"{status_emoji} <b>{user['name']}</b>\n"
                        f"   📞 {user['phone']}\n"
                        f"   📍 {user['address']}\n"
                        f"   🆔 {user['telegram_id']}\n\n"
                    )
                
                keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="back_to_menu")]]
                
                await query.edit_message_text(
                    users_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Foydalanuvchilarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Show users error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

# ========== KURYERLAR ==========
async def show_couriers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuryerlar ro'yxati"""
    query = update.callback_query
    await query.answer()
    
    if not await require_admin(update):
        return
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-Telegram-ID": str(update.effective_user.id)}
            response = await client.get(f"{API_URL}/couriers/", headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                couriers = response.json()
                
                if not couriers:
                    await query.edit_message_text("📭 Kuryerlar topilmadi.")
                    return
                
                couriers_text = "🛵 <b>Kuryerlar ro'yxati:</b>\n\n"
                
                for courier in couriers:
                    status_emoji = "✅" if courier['status'] == 'active' else "🚫"
                    phone = courier.get('phone', 'Telefon yo\'q')
                    couriers_text += (
                        f"{status_emoji} <b>{courier['name']}</b>\n"
                        f"   📞 {phone}\n"
                        f"   🆔 @{courier.get('tg_username', 'N/A')}\n"
                        f"   ID: {courier['telegram_id']}\n\n"
                    )
                
                keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="back_to_menu")]]
                
                await query.edit_message_text(
                    couriers_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Kuryerlarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Show couriers error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

# ========== MAHSULOTLAR ==========
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mahsulotlar ro'yxati"""
    query = update.callback_query
    await query.answer()
    
    if not await require_admin(update):
        return
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/products/", timeout=10.0)
            
            if response.status_code == 200:
                products = response.json()
                
                if not products:
                    await query.edit_message_text("📭 Mahsulotlar topilmadi.")
                    return
                
                products_text = "📦 <b>Mahsulotlar ro'yxati:</b>\n\n"
                
                for product in products:
                    products_text += (
                        f"• <b>{product['name']}</b>\n"
                        f"  Ombor: {product['stock']} ta\n\n"
                    )
                
                keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="back_to_menu")]]
                
                await query.edit_message_text(
                    products_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Mahsulotlarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Show products error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

# ========== MOLIYAVIY HISOBOT ==========
async def show_finance_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Moliyaviy hisobotlarni ko'rsatish"""
    query = update.callback_query
    await query.answer()
    
    if not await require_admin(update):
        return
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-Telegram-ID": str(update.effective_user.id)}
            response = await client.get(f"{API_URL}/finance/stats", headers=headers, timeout=15.0)
            
            if response.status_code == 200:
                stats = response.json()
                
                stats_text = (
                    f"💰 <b>Moliyaviy hisobot</b>\n\n"
                    f"📊 Jami savdo: {stats['total_revenue']:,} so'm\n"
                    f"📉 Tannarx: {stats['total_cogs']:,} so'm\n"
                    f"💵 Yalpi foyda: {stats['gross_profit']:,} so'm\n\n"
                    f"👨‍💼 Oyliklar: {stats['total_salaries']:,} so'm\n"
                    f"💸 Boshqa chiqimlar: {stats['total_expenses']:,} so'm\n\n"
                    f"✅ <b>Sof foyda: {stats['net_profit']:,} so'm</b>\n\n"
                    f"📦 Sotilgan mahsulotlar: {stats['sold_items_count']} ta"
                )
                
                # Mahsulotlar kesimida
                if stats.get('products_breakdown'):
                    stats_text += "\n\n<b>Mahsulotlar bo'yicha:</b>\n"
                    for pb in stats['products_breakdown'][:5]:
                        stats_text += (
                            f"\n• {pb['product_name']}\n"
                            f"  Sotildi: {pb['sold_quantity']} ta\n"
                            f"  Savdo: {pb['total_revenue']:,} so'm\n"
                            f"  Foyda: {pb['gross_profit']:,} so'm ({pb['margin_percent']}%)\n"
                        )
                
                keyboard = [[InlineKeyboardButton("🔙 Bosh menyu", callback_data="back_to_menu")]]
                
                await query.edit_message_text(
                    stats_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ Hisobotlarni yuklashda xatolik.")
        except Exception as e:
            logger.error(f"Finance stats error: {e}")
            await query.edit_message_text("❌ Serverga ulanishda xatolik.")

# ========== ORQAGA QAYTISH ==========
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bosh menyuga qaytish"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📋 Kutilayotgan buyurtmalar", callback_data="orders_pending")],
        [InlineKeyboardButton("🚚 Kuryerdagi buyurtmalar", callback_data="orders_courier")],
        [InlineKeyboardButton("✅ Yetkazilganlar", callback_data="orders_delivered")],
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_list")],
        [InlineKeyboardButton("🛵 Kuryerlar", callback_data="couriers_list")],
        [InlineKeyboardButton("📦 Mahsulotlar", callback_data="products_list")],
        [InlineKeyboardButton("💰 Moliyaviy hisobotlar", callback_data="finance_stats")]
    ]
    
    await query.edit_message_text(
        "🎛 <b>Admin Panel</b>\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== CALLBACK HANDLER ==========
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query larni boshqarish"""
    query = update.callback_query
    data = query.data
    
    if data == "orders_pending":
        await show_orders(update, context, "kutilmoqda")
    elif data == "orders_courier":
        await show_orders(update, context, "kuryerda")
    elif data == "orders_delivered":
        await show_orders(update, context, "yetkazildi")
    elif data.startswith("assign_"):
        await assign_courier(update, context)
    elif data.startswith("do_assign_"):
        await do_assign_courier(update, context)
    elif data == "users_list":
        await show_users(update, context)
    elif data == "couriers_list":
        await show_couriers(update, context)
    elif data == "products_list":
        await show_products(update, context)
    elif data == "finance_stats":
        await show_finance_stats(update, context)
    elif data == "back_to_menu":
        await back_to_menu(update, context)

# ========== MAIN ==========
def main():
    """Botni ishga tushirish"""
    application = Application.builder().token(ADMIN_BOT_TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Admin bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
# 🍽 Shukrona Delivery ERP Tizimi

To'liq funksional yetkazib berish boshqaruv tizimi FastAPI backend va 3 ta Telegram bot bilan.

## 📋 Tizim Tarkibi

### Backend (FastAPI)
- **FastAPI** asosida qurilgan RESTful API
- **PostgreSQL** ma'lumotlar bazasi
- **Cloudinary** rasm saqlash
- Real-time xabarnomalar Telegram bot orqali

### Telegram Botlar
1. **bot_user.py** - Foydalanuvchilar uchun (buyurtma berish)
2. **bot_admin.py** - Adminlar uchun (buyurtmalarni boshqarish)
3. **bot_courier.py** - Kuryerlar uchun (yetkazish)

## 🚀 O'rnatish va Ishga Tushirish

### 1. Talablar
```bash
Python 3.8+
PostgreSQL
```

### 2. Repository ni klonlash
```bash
git clone <repository-url>
cd shukrona-delivery
```

### 3. Virtual muhit yaratish
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

### 4. Paketlarni o'rnatish
```bash
pip install -r requirements.txt
```

### 5. .env faylini sozlash
`.env` fayl yarating va quyidagi ma'lumotlarni kiriting:

```env
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sizning_parolingiz
POSTGRES_DB=shukrona
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Admin
ADMIN_TELEGRAM_IDS=123456789,987654321  # Vergul bilan ajratilgan
ADMIN_PASSWORD=Admin123

# Cloudinary
CLOUDINARY_CLOUD_NAME=sizning_cloud_name
CLOUDINARY_API_KEY=sizning_api_key
CLOUDINARY_API_SECRET=sizning_api_secret

# Bot Tokenlar
BOT_TOKEN=user_bot_token
ADMIN_BOT_TOKEN=admin_bot_token
COURIER_BOT_TOKEN=courier_bot_token
USER_BOT_TOKEN=user_bot_token

# API URL
API_URL=http://localhost:8000
```

### 6. Ma'lumotlar bazasini yaratish
```bash
# PostgreSQL ga kiring
psql -U postgres

# Database yaratish
CREATE DATABASE shukrona;
\q
```

### 7. Backend ni ishga tushirish
```bash
uvicorn app.main:app --reload --port 8000
```

Backend `http://localhost:8000` da ishga tushadi.

### 8. Botlarni ishga tushirish

#### Usul 1: Har bir botni alohida
```bash
# Terminal 1
python bot_user.py

# Terminal 2
python bot_admin.py

# Terminal 3
python bot_courier.py
```

#### Usul 2: Barcha botlarni bir vaqtda
```bash
python run_all_bots.py
```

## 📱 Bot Ishlash Jarayoni

### Foydalanuvchi Bot (bot_user.py)
1. `/start` - Ro'yxatdan o'tish
2. 🛒 Buyurtma berish
3. 📦 Buyurtmalarni kuzatish
4. 👤 Profil boshqarish

### Admin Bot (bot_admin.py)
1. Yangi buyurtmalar haqida real-time xabar olish
2. Buyurtmalarni kuryerlarga biriktirish
3. Foydalanuvchilar va kuryerlarni boshqarish
4. Moliyaviy hisobotlar

### Kuryer Bot (bot_courier.py)
1. Buyurtma biriktirilganda xabar olish
2. Buyurtmani qabul qilish va yetkazish vaqtini belgilash
3. Yetkazilganini tasdiqlash
4. Statistika ko'rish

## 🔄 Real-time Xabarnomalar

### 1. Yangi buyurtma
```
User → bot_user.py → API → notify_admins_new_order() → Admin bot
```

### 2. Kuryer biriktirish
```
Admin → bot_admin.py → API → notify_courier_assigned() → Courier bot
Admin → bot_admin.py → API → notify_user_courier_assigned() → User bot
```

### 3. Kuryer qabul qildi
```
Courier → bot_courier.py → API → notify_user_courier_accepted() → User bot
```

### 4. Yetkazildi
```
Courier → bot_courier.py → API → notify_user_delivered() → User bot
Courier → bot_courier.py → API → notify_admin_delivered() → Admin bot
```

## 📊 API Endpoints

### Users
- `POST /users/` - Foydalanuvchi yaratish
- `GET /users/me/{telegram_id}` - Profil olish
- `PUT /users/me/{telegram_id}` - Profilni yangilash
- `GET /users/` - Barcha foydalanuvchilar (Admin)

### Couriers
- `POST /couriers/` - Kuryer yaratish (Admin)
- `GET /couriers/` - Kuryerlar ro'yxati (Admin)
- `GET /couriers/me/history` - Kuryer statistikasi

### Products
- `POST /products/` - Mahsulot qo'shish (Admin)
- `GET /products/` - Mahsulotlar ro'yxati
- `PUT /products/{id}` - Mahsulotni yangilash (Admin)
- `DELETE /products/{id}` - Mahsulotni o'chirish (Admin)

### Orders
- `POST /orders/` - Buyurtma yaratish
- `GET /orders/` - Buyurtmalar ro'yxati
- `PATCH /orders/{id}/assign` - Kuryerga biriktirish (Admin)
- `PATCH /orders/{id}/accept` - Qabul qilish (Kuryer)
- `PATCH /orders/{id}/deliver` - Yetkazildi (Kuryer)

### Finance
- `GET /finance/stats` - Moliyaviy hisobotlar (Admin)
- `POST /finance/pay-salary` - Oylik to'lash (Admin)
- `POST /finance/expenses` - Chiqim qo'shish (Admin)
- `GET /finance/expenses` - Chiqimlar ro'yxati (Admin)

## 🔧 Muammolarni Hal Qilish

### Backend ishlamayapti
```bash
# Loglarni tekshiring
uvicorn app.main:app --log-level debug

# PostgreSQL ishlayotganini tekshiring
psql -U postgres -c "SELECT 1"
```

### Bot xabar yubormayapti
1. Bot tokenlarini `.env` faylda tekshiring
2. `ADMIN_TELEGRAM_IDS` to'g'ri kiritilganini tekshiring
3. Bot ishga tushganini tekshiring

### Ma'lumotlar bazasi xatosi
```bash
# Bazani qayta yaratish (DIQQAT: Ma'lumotlar o'chadi!)
python
>>> from app.database import engine, Base
>>> Base.metadata.drop_all(bind=engine)
>>> Base.metadata.create_all(bind=engine)
```

## 📝 Development

### Yangi endpoint qo'shish
1. `app/models.py` - Model yaratish
2. `app/schemas/` - Schema yaratish
3. `app/routers/` - Router yaratish
4. `app/main.py` - Router qo'shish

### Yangi bot funksiyasi qo'shish
1. Handler funksiyasini yozing
2. `application.add_handler()` qo'shing
3. Test qiling

## 🔐 Xavfsizlik

- Admin parolini o'zgartiring
- `.env` faylini git ga qo'shmang
- Database parolini murakkab qiling
- Production da HTTPS ishlatiladi

## 📞 Support

Muammo yuzaga kelsa:
- Issues bo'limida xabar qoldiring
- Telegram: @your_support_username
- Email: support@shukrona.uz

## 📄 License

MIT License - Erkin foydalaning!

---

**Shukrona Delivery** - Made with ❤️ in Uzbekistan
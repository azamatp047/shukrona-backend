from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text # <--- Muhim import
import os

from app.database import engine, Base
from app.routers import admin, users, products, couriers, orders, finance

# Papkani yaratish
if not os.path.exists("static/images"):
    os.makedirs("static/images")

# =================================================================
# BAZANI TOZALASH (RESET) QISMI
# =================================================================
# Eski usul ishlamadi, chunki eski 'transactions' jadvali xalaqit beryapti.
# Biz SQL buyrug'i bilan hammasini majburan (CASCADE) o'chiramiz.

with engine.begin() as conn:
    # Eski jadvallarni o'chirish tartibi
    conn.execute(text("DROP TABLE IF EXISTS transactions CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS salary_payments CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS expenses CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS couriers CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS admins CASCADE"))
    # Agar alembic ishlatgan bo'lsangiz uni ham o'chiramiz
    conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

# Yangi jadvallarni yaratish
Base.metadata.create_all(bind=engine)
# =================================================================

# Taglar uchun tavsiflar (Swagger UI da ko'rinadi)
tags_metadata = [
    {
        "name": "Admin",
        "description": "Adminlar uchun maxsus funksiyalar (Login, Statistika, Boshqaruv).",
    },
    {
        "name": "Users",
        "description": "Mijozlar (Foydalanuvchilar) bilan ishlash. Ro'yxatdan o'tish va ma'lumotlarni o'zgartirish.",
    },
    {
        "name": "Products",
        "description": "Mahsulotlar katalogi. Qo'shish, o'zgartirish, o'chirish va rasmlar yuklash.",
    },
    {
        "name": "Couriers",
        "description": "Kuryerlar boshqaruvi. Yangi kuryer qo'shish, tarix va reytinglarni ko'rish.",
    },
    {
        "name": "Orders",
        "description": "Buyurtmalar tizimi. Yaratish, biriktirish, yetkazish, baholash va bonus qo'shish.",
    },
    {
        "name": "Finance & Analytics",
        "description": "Moliyaviy hisobotlar, foyda-zarar analizi va kuryerlarga oylik to'lash.",
    },
]

app = FastAPI(
    title="Shukrona Delivery ERP",
    description="""
    **Shukrona Delivery** - yetkazib berish xizmatini avtomatlashtirish tizimi.
    
    Bu API orqali siz quyidagilarni amalga oshirishingiz mumkin:
    *   **Buyurtmalar**: Qabul qilish, kuryerlarga biriktirish va yetkazish.
    *   **Kuryerlar**: Ish faoliyatini kuzatish, reyting va oylik hisoblash.
    *   **Ombor**: Mahsulotlar qoldig'ini real vaqtda nazorat qilish.
    *   **Moliya**: Kirim-chiqim va sof foydani aniq hisoblash.
    
    Tizim 3 ta asosiy rol uchun mo'ljallangan: **Admin**, **Kuryer**, **Mijoz**.
    """,
    version="2.1.0",
    openapi_tags=tags_metadata
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://shukrona-admin-panel.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(couriers.router)
app.include_router(orders.router)
app.include_router(finance.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
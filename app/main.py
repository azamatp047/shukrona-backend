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

app = FastAPI(
    title="Shukrona Delivery ERP",
    description="Mukammallashgan yetkazib berish tizimi",
    version="2.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
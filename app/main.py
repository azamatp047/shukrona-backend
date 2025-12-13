from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # <-- Import
import os

from app.database import engine, Base
from app.routers import admin, users, products, couriers, orders, transactions

# Papkani yaratish
if not os.path.exists("static/images"):
    os.makedirs("static/images")

# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Shukrona Delivery Backend",
    description="Telegram bot uchun yetkazib berish tizimi API",
    version="1.1.0"
)

# Static fayllarni mount qilish (brauzerda /static/images/nomi.jpg deb ochish uchun)
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
app.include_router(transactions.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import admin, users, products, couriers, orders
from app.routers import transactions

Base.metadata.drop_all(bind=engine)
# =================================================================

# Jadvallarni yangidan yaratish (endi created_at ustuni bilan yaratiladi)
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Shukrona Delivery Backend",
    description="Telegram bot uchun yetkazib berish tizimi API",
    version="1.0.0"
)

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(couriers.router)
app.include_router(orders.router)
app.include_router(transactions.router)

@app.get("/")
def read_root():
    return {
        "message": "Shukrona Delivery Backend API",
        "status": "ishlayapti",
        "endpoints": {
            "admin": "/admin",
            "users": "/users",
            "products": "/products",
            "couriers": "/couriers",
            "orders": "/orders",
            "transactions": "/transactions",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}
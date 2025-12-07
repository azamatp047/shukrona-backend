from fastapi import FastAPI
from app.database import engine, Base
from app.routers import admin, users, products, couriers, orders

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shukrona Backend")

app.include_router(admin.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(couriers.router)
app.include_router(orders.router)

@app.get("/")
def read_root():
    return {"message": "Backend ishlayapti!"}

from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Courier, Order, User
from app.schemas.courier import CourierCreate, CourierRead, CourierStats, CourierOrderSummary
from app.dependencies import require_admin

router = APIRouter(prefix="/couriers", tags=["Couriers"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Kuryer yaratish (Admin)
@router.post("/", response_model=CourierRead, status_code=201)
def create_courier(
    courier: CourierCreate, 
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    db_courier = Courier(**courier.model_dump())
    db.add(db_courier)
    db.commit()
    db.refresh(db_courier)
    return db_courier

# 2. Barcha kuryerlar ro'yxati (Admin)
@router.get("/", response_model=List[CourierRead])
def get_couriers(
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    return db.query(Courier).all()

# --- YANGI: KURYER TARIXI VA STATISTIKASI ---

def get_courier_statistics(db: Session, courier: Courier, start_date: date = None, end_date: date = None):
    # Faqat yetkazilgan buyurtmalarni olamiz
    query = db.query(Order).filter(
        Order.courier_id == courier.id,
        Order.status == "yetkazildi"
    )
    
    if start_date:
        query = query.filter(func.date(Order.delivered_at) >= start_date)
    if end_date:
        query = query.filter(func.date(Order.delivered_at) <= end_date)
    
    orders = query.order_by(Order.delivered_at.desc()).all()
    
    total_count = len(orders)
    total_money = sum(o.total_amount for o in orders)
    
    history_list = []
    for o in orders:
        history_list.append(CourierOrderSummary(
            order_id=o.id,
            total_amount=o.total_amount,
            delivered_at=o.delivered_at,
            user_address=o.user.address if o.user else "Noma'lum"
        ))
        
    return CourierStats(
        courier_id=courier.id,
        courier_name=courier.name,
        total_delivered_orders=total_count,
        total_money_collected=total_money,
        history=history_list
    )

# 3. Kuryer o'z tarixini ko'rishi (Telegram ID orqali)
@router.get("/me/history", response_model=CourierStats)
def get_my_history(
    telegram_id: str, 
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db)
):
    courier = db.query(Courier).filter(Courier.telegram_id == telegram_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
    
    return get_courier_statistics(db, courier, start_date, end_date)

# 4. Admin birorta kuryerni tarixini ko'rishi
@router.get("/{courier_id}/history", response_model=CourierStats)
def get_courier_history_admin(
    courier_id: int,
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    courier = db.query(Courier).filter(Courier.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
        
    return get_courier_statistics(db, courier, start_date, end_date)
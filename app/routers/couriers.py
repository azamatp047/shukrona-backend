from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Courier, Order, User
from app.schemas.courier import CourierCreate, CourierRead, CourierStats, CourierOrderSummary, CourierUpdate
from app.dependencies import require_admin

router = APIRouter(prefix="/couriers", tags=["Couriers"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Kuryer yaratish (Admin)
@router.post("/", response_model=CourierRead, status_code=201, summary="Yangi kuryer qo'shish")
def create_courier(
    courier: CourierCreate, 
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Tizimga yangi kuryer qo'shish (faqat Admin uchun).**
    """
    db_courier = Courier(**courier.model_dump())
    db.add(db_courier)
    db.commit()
    db.refresh(db_courier)
    return db_courier

# 2. Barcha kuryerlar ro'yxati (Admin)
@router.get("/", response_model=List[CourierRead], summary="Barcha kuryerlarni ko'rish")
def get_couriers(
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Tizimdagi barcha kuryerlar ro'yxati.**
    """
    return db.query(Courier).all()

# 2.5. Kuryer ma'lumotlarini o'zgartirish (Admin)
@router.patch("/{courier_id}/", response_model=CourierRead, summary="Kuryer ma'lumotlarini o'zgartirish (Admin)")
def update_courier(
    courier_id: int,
    data: CourierUpdate,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Kuryer ma'lumotlarini tahrirlash (Admin).**
    
    - Faqat yuborilgan maydonlar o'zgaradi.
    """
    db_courier = db.query(Courier).filter(Courier.id == courier_id).first()
    if not db_courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_courier, key, value)
    
    db.commit()
    db.refresh(db_courier)
    return db_courier

# ... (Helper methods remain same)

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
    total_money = sum(o.final_total_amount for o in orders)
    
    # Rating hisoblash
    rated_orders = [o.rating for o in orders if o.rating is not None]
    avg_rating = sum(rated_orders) / len(rated_orders) if rated_orders else 0.0
    
    return CourierStats(
        courier_id=courier.id,
        courier_name=courier.name,
        total_delivered_orders=total_count,
        total_money_collected=total_money,
        average_rating=round(avg_rating, 1)
    )

# 3. Kuryer o'z tarixini ko'rishi (Telegram ID orqali)
@router.get("/me/history/", response_model=CourierStats, summary="Kuryer o'z statistikasini ko'rishi")
def get_my_history(
    telegram_id: str, 
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db)
):
    """
    **Kuryerning shaxsiy statistikasi va tarixi.**
    
    - **average_rating**: O'rtacha reyting.
    - **history**: Bajarilgan buyurtmalar ro'yxati.
    """
    courier = db.query(Courier).filter(Courier.telegram_id == telegram_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
    
    return get_courier_statistics(db, courier, start_date, end_date)

# 4. Admin birorta kuryerni tarixini ko'rishi
@router.get("/{courier_id}/history/", response_model=CourierStats, summary="Kuryer statistikasi (Admin)")
def get_courier_history_admin(
    courier_id: int,
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Admin istalgan kuryerning statistikasini ko'rishi mumkin.**
    """
    courier = db.query(Courier).filter(Courier.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
        
    return get_courier_statistics(db, courier, start_date, end_date)

# 5. Kuryer borligini tekshirish (Bot start uchun)
@router.get("/check-messenger/{telegram_id}/", summary="Kuryer bazada borligini tekshirish")
def check_courier_exists(telegram_id: str, db: Session = Depends(get_db)):
    """
    **Kuryer bazada ro'yxatdan o'tganligini tekshirish (Bot orqali).**
    
    - Bazada bo'lsa: 200 OK qaytadi.
    - Bazada bo'lmasa: 404 Not Found qaytadi.
    """
    courier = db.query(Courier).filter(Courier.telegram_id == telegram_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi. Iltimos, adminga murojaat qiling.")
    
    return {"status": 200, "message": "Kuryer topildi", "courier_name": courier.name}

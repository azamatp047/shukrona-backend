from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Order, User, Product, Courier, Transaction
from app.schemas.order import (
    OrderCreate, 
    OrderRead, 
    OrderAssign, 
    OrderAccept, 
    OrderStatusUpdate,
    OrderWithDetails
)

router = APIRouter(prefix="/orders", tags=["Orders"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=OrderRead, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Foydalanuvchi order yaratadi"""
    # User va Product mavjudligini tekshirish
    user = db.query(User).filter(User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    product = db.query(Product).filter(Product.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    
    # Order yaratish
    db_order = Order(**order.model_dump(), status="created")
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    return db_order

@router.get("/", response_model=List[OrderWithDetails])
def get_orders(
    status: str = None, 
    courier_id: int = None,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """Barcha orderlarni olish (filter bilan)"""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    if courier_id:
        query = query.filter(Order.courier_id == courier_id)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    
    orders = query.all()
    
    # To'liq ma'lumot bilan qaytarish
    result = []
    for order in orders:
        order_dict = {
            "id": order.id,
            "status": order.status,
            "delivery_time": order.delivery_time,
            "created_at": order.created_at,
            "user": {
                "id": order.user.id,
                "name": order.user.name,
                "phone": order.user.phone,
                "address": order.user.address
            },
            "product": {
                "id": order.product.id,
                "name": order.product.name,
                "price": order.product.price
            },
            "courier": {
                "id": order.courier.id,
                "name": order.courier.name
            } if order.courier else None
        }
        result.append(order_dict)
    
    return result

@router.get("/{order_id}", response_model=OrderWithDetails)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Bitta orderni olish"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order topilmadi")
    
    return {
        "id": order.id,
        "status": order.status,
        "delivery_time": order.delivery_time,
        "created_at": order.created_at,
        "user": {
            "id": order.user.id,
            "name": order.user.name,
            "phone": order.user.phone,
            "address": order.user.address
        },
        "product": {
            "id": order.product.id,
            "name": order.product.name,
            "price": order.product.price
        },
        "courier": {
            "id": order.courier.id,
            "name": order.courier.name
        } if order.courier else None
    }

@router.patch("/{order_id}/assign", response_model=OrderRead)
def assign_courier(order_id: int, data: OrderAssign, db: Session = Depends(get_db)):
    """Admin kuryer biriktiradi"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order topilmadi")
    
    # Kuryer mavjudligini tekshirish
    courier = db.query(Courier).filter(Courier.id == data.courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
    
    # Order statusini yangilash
    order.courier_id = data.courier_id
    order.status = "assigned"
    order.assigned_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    return order

@router.patch("/{order_id}/accept", response_model=OrderRead)
def accept_order(order_id: int, data: OrderAccept, db: Session = Depends(get_db)):
    """Kuryer orderni qabul qiladi va yetkazish vaqtini yozadi"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order topilmadi")
    
    if order.status != "assigned":
        raise HTTPException(status_code=400, detail="Order hali tayinlanmagan")
    
    # Statusni yangilash
    order.status = "accepted"
    order.delivery_time = data.delivery_time
    order.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    return order

@router.patch("/{order_id}/deliver", response_model=OrderRead)
def deliver_order(order_id: int, db: Session = Depends(get_db)):
    """Kuryer orderni yetkazdi (delivered tugmasi)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order topilmadi")
    
    if order.status not in ["accepted", "delivering"]:
        raise HTTPException(status_code=400, detail="Order hali qabul qilinmagan")
    
    # Statusni yangilash
    order.status = "delivered"
    order.delivered_at = datetime.utcnow()
    
    # Transaction yaratish (kirim)
    transaction = Transaction(
        order_id=order.id,
        amount=order.product.price,
        type="income",
        description=f"Order #{order.id} uchun to'lov"
    )
    db.add(transaction)
    
    db.commit()
    db.refresh(order)
    
    return order

@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int, 
    data: OrderStatusUpdate, 
    db: Session = Depends(get_db)
):
    """Order statusini yangilash (universal)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order topilmadi")
    
    order.status = data.status
    db.commit()
    db.refresh(order)
    
    return order
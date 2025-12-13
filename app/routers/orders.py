from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Order, User, Product, Courier, Transaction, OrderItem
from app.schemas.order import (
    OrderCreate, 
    OrderRead, 
    OrderAssign, 
    OrderAccept,
    OrderItemRead
)

router = APIRouter(prefix="/orders", tags=["Orders"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------
# YORDAMCHI FUNKSIYA: Javobni chiroyli formatlash uchun
# -------------------------------------------------------------------
def format_order_response(order: Order) -> OrderRead:
    # 1. Order ichidagi mahsulotlarni formatlash
    items_data = []
    for item in order.items:
        product_name = item.product.name if item.product else "O'chirilgan mahsulot"
        items_data.append(OrderItemRead(
            product_id=item.product_id,
            product_name=product_name,
            quantity=item.quantity,
            price=item.price,
            total=item.price * item.quantity
        ))
        
    # 2. Kuryer telefonini xavfsiz olish
    c_phone = None
    if order.courier and hasattr(order.courier, 'phone'):
        c_phone = order.courier.phone

    # 3. Asosiy javobni qaytarish
    return OrderRead(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        delivery_time=order.delivery_time,
        created_at=order.created_at,
        
        # User ma'lumotlari
        user_id=order.user_id,
        user_name=order.user.name,
        user_phone=order.user.phone,
        user_address=order.user.address,
        user_telegram_id=order.user.telegram_id,
        
        # Courier ma'lumotlari
        courier_id=order.courier_id,
        courier_name=order.courier.name if order.courier else None,
        courier_phone=c_phone,
        
        items=items_data
    )

# -------------------------------------------------------------------
# ENDPOINTS
# -------------------------------------------------------------------

@router.post("/", response_model=OrderRead, status_code=201)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    Foydalanuvchi telegram_id orqali buyurtma beradi.
    """
    # 1. Userni telegram_id orqali topish
    user = db.query(User).filter(User.telegram_id == order_in.telegram_id).first()
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="Foydalanuvchi topilmadi. Iltimos, avval botdan /start bosing."
        )
    
    # 2. Bo'sh order yaratish (User ID bilan)
    db_order = Order(
        user_id=user.id,
        status="created",
        total_amount=0.0
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    total_price = 0.0
    
    # 3. Mahsulotlarni orderga qo'shish
    for item in order_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            continue # Mahsulot topilmasa tashlab ketamiz
        
        # OrderItem jadvaliga yozish
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.price
        )
        db.add(db_item)
        total_price += (product.price * item.quantity)
    
    # 4. Umumiy narxni yangilash
    db_order.total_amount = total_price
    db.commit()
    db.refresh(db_order)
    
    # 5. To'liq ma'lumotni qaytarish
    return format_order_response(db_order)


@router.get("/", response_model=List[OrderRead])
def get_orders(
    status: str = None, 
    courier_id: int = None,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Admin barcha buyurtmalarni ko'rishi uchun.
    """
    query = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.user),
        joinedload(Order.courier)
    )
    
    if status:
        query = query.filter(Order.status == status)
    if courier_id:
        query = query.filter(Order.courier_id == courier_id)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    return [format_order_response(o) for o in orders]


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Bitta buyurtmani ID orqali olish"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    return format_order_response(order)


@router.patch("/{order_id}/assign", response_model=OrderRead)
def assign_courier(order_id: int, data: OrderAssign, db: Session = Depends(get_db)):
    """Admin kuryer biriktiradi"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    courier = db.query(Courier).filter(Courier.id == data.courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
    
    order.courier_id = data.courier_id
    order.status = "assigned"
    order.assigned_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    return format_order_response(order)


@router.patch("/{order_id}/accept", response_model=OrderRead)
def accept_order(order_id: int, data: OrderAccept, db: Session = Depends(get_db)):
    """Kuryer buyurtmani qabul qiladi va vaqt belgilaydi"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    if order.status != "assigned":
        raise HTTPException(status_code=400, detail="Buyurtma hali kuryerga biriktirilmagan")
    
    order.status = "accepted"
    order.delivery_time = data.delivery_time
    order.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    return format_order_response(order)


@router.patch("/{order_id}/deliver", response_model=OrderRead)
def deliver_order(order_id: int, db: Session = Depends(get_db)):
    """Kuryer buyurtmani yetkazib berdi"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    if order.status not in ["accepted", "delivering"]:
        raise HTTPException(status_code=400, detail="Buyurtma hali qabul qilinmagan")
    
    order.status = "delivered"
    order.delivered_at = datetime.utcnow()
    
    # Kirim tranzaksiyasini yaratish
    transaction = Transaction(
        order_id=order.id,
        amount=order.total_amount,
        type="income",
        description=f"Order #{order.id} muvaffaqiyatli yetkazildi"
    )
    db.add(transaction)
    
    db.commit()
    db.refresh(order)
    return format_order_response(order)
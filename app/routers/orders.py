from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Order, User, Product, Courier, OrderItem
from app.schemas.order import (
    OrderCreate, OrderRead, OrderAssign, OrderAccept, OrderItemRead
)
from app.dependencies import require_admin

router = APIRouter(prefix="/orders", tags=["Orders"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function
def format_order_response(order: Order) -> OrderRead:
    items_data = []
    for item in order.items:
        p_name = item.product.name if item.product else "Noma'lum"
        items_data.append(OrderItemRead(
            product_id=item.product_id,
            product_name=p_name,
            quantity=item.quantity,
            price=item.sell_price, # Sotilgan narxni ko'rsatamiz
            total=item.sell_price * item.quantity
        ))
    
    c_phone = order.courier.phone if (order.courier and order.courier.phone) else None

    return OrderRead(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        delivery_time=order.delivery_time,
        created_at=order.created_at,
        user_id=order.user_id,
        user_name=order.user.name,
        user_phone=order.user.phone,
        user_address=order.user.address,
        user_telegram_id=order.user.telegram_id,
        courier_id=order.courier_id,
        courier_name=order.courier.name if order.courier else None,
        courier_phone=c_phone,
        items=items_data
    )

from app.utils.telegram import (
    notify_admins_new_order, 
    notify_courier_assigned, 
    notify_user_courier_assigned,
    notify_user_courier_accepted,
    notify_user_delivered,
    notify_admin_delivered
)

# ... (Imports qoladi)

# 1. CREATE ORDER (Ombor logikasi bilan)
@router.post("/", response_model=OrderRead, status_code=201)
async def create_order(order_in: OrderCreate, db: Session = Depends(get_db)): # ASYNC bo'lishi kerak
    user = db.query(User).filter(User.telegram_id == order_in.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Order yaratamiz
    db_order = Order(
        user_id=user.id,
        status="kutilmoqda", 
        total_amount=0.0
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    total_price = 0.0
    
    for item in order_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            continue
        
        # OMBOR TEKSHIRUVI (soddalashtirilgan)
        if product.stock < item.quantity:
            pass 

        product.stock -= item.quantity
        
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=product.id,
            quantity=item.quantity,
            buy_price=product.buy_price,   
            sell_price=product.sell_price  
        )
        db.add(db_item)
        total_price += (product.sell_price * item.quantity)
    
    db_order.total_amount = total_price
    db.commit()
    db.refresh(db_order)
    
    # --- NOTIFICATION START ---
    try:
        order_data = {
            "id": db_order.id,
            "user_name": user.name,
            "user_phone": user.phone,
            "user_address": user.address,
            "total_amount": total_price
        }
        await notify_admins_new_order(order_data)
    except Exception as e:
        print(f"Notification Error: {e}")
    # --- NOTIFICATION END ---

    return format_order_response(db_order)

# 2. Assign Courier
@router.patch("/{order_id}/assign", response_model=OrderRead)
async def assign_courier(order_id: int, data: OrderAssign, db: Session = Depends(get_db)): # ASYNC
    order = db.query(Order).options(joinedload(Order.user)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Topilmadi")
    
    courier = db.query(Courier).filter(Courier.id == data.courier_id).first()
    if not courier: raise HTTPException(status_code=404, detail="Kuryer yo'q")
    
    order.courier_id = data.courier_id
    order.assigned_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    
    # --- NOTIFICATION START ---
    try:
        # Kuryerga xabar
        order_data = {
            "id": order.id,
            "user_address": order.user.address,
            "user_phone": order.user.phone
        }
        if courier.telegram_id:
            await notify_courier_assigned(courier.telegram_id, order_data)
        
        # Userga xabar (Admin ko'rdi)
        if order.user.telegram_id:
            await notify_user_courier_assigned(order.user.telegram_id, order.id)
            
    except Exception as e:
        print(f"Notification Error: {e}")
    # --- NOTIFICATION END ---
    
    return format_order_response(order)

# 3. Accept (Kuryerda)
@router.patch("/{order_id}/accept", response_model=OrderRead)
async def accept_order(order_id: int, data: OrderAccept, db: Session = Depends(get_db)): # ASYNC
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Topilmadi")
    
    order.status = "kuryerda" 
    order.delivery_time = data.delivery_time
    order.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    # --- NOTIFICATION START ---
    try:
        if order.user.telegram_id:
            c_name = order.courier.name if order.courier else "Kuryer"
            await notify_user_courier_accepted(
                order.user.telegram_id, 
                order.id, 
                data.delivery_time, 
                c_name
            )
    except Exception as e:
        print(f"Notification Error: {e}")
    # --- NOTIFICATION END ---

    return format_order_response(order)

# 4. Deliver (Yetkazildi)
@router.patch("/{order_id}/deliver", response_model=OrderRead)
async def deliver_order(order_id: int, db: Session = Depends(get_db)): # ASYNC
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Topilmadi")
    
    order.status = "yetkazildi" 
    order.delivered_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)

    # --- NOTIFICATION START ---
    try:
        if order.user.telegram_id:
            await notify_user_delivered(order.user.telegram_id, order.id)
        
        c_name = order.courier.name if order.courier else "Kuryer"
        await notify_admin_delivered(order.id, c_name)

    except Exception as e:
        print(f"Notification Error: {e}")
    # --- NOTIFICATION END ---
    
    return format_order_response(order)

# Admin uchun GET
@router.get("/", response_model=List[OrderRead])
def get_orders(
    status: str = None, 
    courier_id: int = None,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.user),
        joinedload(Order.courier)
    )
    if status: query = query.filter(Order.status == status)
    if courier_id: query = query.filter(Order.courier_id == courier_id)
    if user_id: query = query.filter(Order.user_id == user_id)
    
    return [format_order_response(o) for o in query.order_by(Order.created_at.desc()).all()]
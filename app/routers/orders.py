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

# 1. CREATE ORDER (Ombor logikasi bilan)
@router.post("/", response_model=OrderRead, status_code=201)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == order_in.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Order yaratamiz
    db_order = Order(
        user_id=user.id,
        status="kutilmoqda", # <--- Default status O'zbekcha
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
        
        # OMBOR TEKSHIRUVI
        if product.stock < item.quantity:
            # Talab bo'yicha "xatolik bermasligi kerak", lekin manfiy ombor bo'lmasligi uchun
            # biz borini beramiz yoki xato qaytaramiz.
            # Agar 120 ta bo'lsa va 40 ta so'rasa -> beramiz.
            # Agar 10 ta bo'lsa va 40 ta so'rasa -> 400 Xato qaytarish mantiqan to'g'ri.
            # Lekin siz "xato bermasin" dedingiz, demak ehtimol "Buyurtma qabul qilinaversin, ombor minusga kirsin" degan ma'noda?
            # ERP qoidasi: Minusga kirish yomon, lekin "Pre-order" sifatida minusga kiritamiz.
            pass 

        # Ombordan ayiramiz
        product.stock -= item.quantity
        
        # OrderItem ga Olish va Sotish narxini muhrlaymiz
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=product.id,
            quantity=item.quantity,
            buy_price=product.buy_price,   # <-- Tannarx
            sell_price=product.sell_price  # <-- Sotuv narx
        )
        db.add(db_item)
        total_price += (product.sell_price * item.quantity)
    
    db_order.total_amount = total_price
    db.commit()
    db.refresh(db_order)
    
    return format_order_response(db_order)

# 2. Assign Courier
@router.patch("/{order_id}/assign", response_model=OrderRead)
def assign_courier(order_id: int, data: OrderAssign, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Topilmadi")
    
    courier = db.query(Courier).filter(Courier.id == data.courier_id).first()
    if not courier: raise HTTPException(status_code=404, detail="Kuryer yo'q")
    
    order.courier_id = data.courier_id
    # Status o'zgarmaydi (hali ham kutilmoqda) yoki "assigned" qilmasdan to'g'ridan to'g'ri kuryer qabul qilganda o'zgartiramiz
    # Talabda 3 ta status bor: kutilmoqda, kuryerda, yetkazildi.
    # Admin biriktirganda hali "kuryerda" emas, kuryer "Qabul qildim" deganda o'zgaradi.
    
    order.assigned_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return format_order_response(order)

# 3. Accept (Kuryerda)
@router.patch("/{order_id}/accept", response_model=OrderRead)
def accept_order(order_id: int, data: OrderAccept, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Topilmadi")
    
    order.status = "kuryerda" # <--- Status o'zgardi
    order.delivery_time = data.delivery_time
    order.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    return format_order_response(order)

# 4. Deliver (Yetkazildi)
@router.patch("/{order_id}/deliver", response_model=OrderRead)
def deliver_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Topilmadi")
    
    order.status = "yetkazildi" # <--- Status yakunlandi
    order.delivered_at = datetime.utcnow()
    
    # Eslatma: Transaction jadvali endi shart emas, chunki Order uzi hamma info ni saqlaydi
    # lekin xohlasangiz qoldirishingiz mumkin. Men soddalik uchun OrderItemlardan hisoblashni afzal ko'raman.
    
    db.commit()
    db.refresh(order)
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
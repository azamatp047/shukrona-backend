from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Order, User, Product, Courier, OrderItem
from app.schemas.order import (
    OrderCreate, OrderRead, OrderAssign, OrderAccept, OrderItemRead, OrderRate, BonusItemCreate
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
            total=item.sell_price * item.quantity,
            is_bonus=item.is_bonus
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
        rating=order.rating,
        rating_comment=order.rating_comment,
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
@router.post("/", response_model=OrderRead, status_code=201, summary="Yangi buyurtma yaratish")
async def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """
    **Foydalanuvchi tomonidan yangi buyurtma yaratish.**
    
    - **telegram_id**: Buyurtmachi (User) ning Telegram ID si.
    - **items**: Mahsulotlar ro'yxati (ID va soni).
    
    Tizim avtomatik ravishda:
    1. Foydalanuvchini topadi.
    2. Mahsulotlar omborda yetarli ekanligini tekshiradi (hozircha pass).
    3. Ombor qoldig'ini kamaytiradi.
    4. Umumiy summani hisoblaydi.
    5. Adminga xabar yuboradi.
    """
    user = db.query(User).filter(User.telegram_id == order_in.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Order yaratamiz
    db_order = Order(
        user_id=user.id,
        status="kutilmoqda", 
        total_amount=0.0,
        delivery_time=order_in.delivery_time
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
@router.patch("/{order_id}/assign/", response_model=OrderRead, summary="Kuryer biriktirish (Admin)")
async def assign_courier(order_id: int, data: OrderAssign, db: Session = Depends(get_db)):
    """
    **Buyurtmani kuryerga biriktirish.**
    
    - Faqat **Admin** foydalanishi kerak (Frontendda tekshiriladi).
    - Kuryerga va Mijozga Telegram orqali xabar boradi.
    """
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
@router.patch("/{order_id}/accept/", response_model=OrderRead, summary="Buyurtmani qabul qilish (Kuryer)")
async def accept_order(order_id: int, data: OrderAccept, db: Session = Depends(get_db)):
    """
    **Kuryer buyurtmani qabul qilishi.**
    
    - **delivery_time**: Yetkazib berish vaqti matn ko'rinishida (masalan: "30 daqiqa").
    - Status **kuryerda** ga o'zgaraadi.
    - Mijozga xabar yuboriladi.
    """
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
@router.patch("/{order_id}/deliver/", response_model=OrderRead, summary="Buyurtmani yetkazildi deb belgilash")
async def deliver_order(order_id: int, db: Session = Depends(get_db)):
    """
    **Buyurtma yetkazib berilganda ishlatiladi.**
    
    - Status **yetkazildi** ga o'zgaradi.
    - **delivered_at** vaqti belgilanadi.
    - Admin va Mijozga xabar boradi.
    """
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

    
    return format_order_response(order)

# 4.5. Rate Order (Baho berish)
@router.post("/{order_id}/rate/", response_model=OrderRead, summary="Buyurtmani baholash")
async def rate_order(order_id: int, data: OrderRate, db: Session = Depends(get_db)):
    """
    **Mijoz tomonidan kuryer xizmatini baholash.**
    
    - **rating**: 1 dan 5 gacha bo'lgan baho.
    - **comment**: Ixtiyoriy izoh.
    - Faqat **yetkazildi** statusidagi buyurtmalar uchun ishlaydi.
    """
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    if order.status != "yetkazildi":
        raise HTTPException(status_code=400, detail="Faqat yetkazilgan buyurtmalarni baholash mumkin")
        
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Baho 1 va 5 oralig'ida bo'lishi kerak")
        
    order.rating = data.rating
    order.rating_comment = data.comment
    
    db.commit()
    db.refresh(order)
    
    return format_order_response(order)

    return format_order_response(order)

# 4.6 Get One Order
@router.get("/{order_id}/", response_model=OrderRead, summary="Bitta buyurtma haqida ma'lumot")
def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    """
    **ID orqali buyurtma tafsilotlarini olish.**
    
    Agar buyurtma topilmasa 404 xatolik qaytaradi.
    """
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.user),
        joinedload(Order.courier)
    ).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
        
    return format_order_response(order)

# 4.7 Add Bonus Items
@router.post("/{order_id}/bonus/", response_model=OrderRead, summary="Bonus (tekin) mahsulot qo'shish")
async def add_bonus_items(order_id: int, items: List[BonusItemCreate], db: Session = Depends(get_db)):
    """
    **Kuryer tomonidan buyurtmaga bonus qo'shish.**
    
    - Faqat **kuryerda** statusida ishlaydi.
    - Mahsulot **narxi 0** deb hisoblanadi (tekin).
    - Ombor qoldig'i kamayadi, lekin umumiy savdo summasi o'zgarmaydi.
    """
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    if order.status != "kuryerda":
        raise HTTPException(status_code=400, detail="Faqat kuryerdagi buyurtmalarga bonus qo'shish mumkin")
    
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            continue
            
        if product.stock < item.quantity:
             raise HTTPException(status_code=400, detail=f"{product.name} yetarli emas (Mavjud: {product.stock})")
        
        product.stock -= item.quantity
        
        db_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            buy_price=0.0,  # Bonus = 0
            sell_price=0.0, # Bonus = 0
            is_bonus=True   # Flag
        )
        db.add(db_item)
    
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
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Order, User, Product, Courier, OrderItem, OrderPriceHistory
from app.schemas.order import (
    OrderCreate, OrderRead, OrderList, OrderAssign, OrderAccept, OrderItemRead, OrderRate, BonusItemCreate, OrderPriceUpdate,
    OrderDeliver, OrderBonus, OrderLock
)
from app.dependencies import require_admin
from app.config import MAX_USER_PENDING_ORDERS

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
    bonus_data = []
    for item in order.items:
        p_name = item.product.name if item.product else "Noma'lum"
        item_read = OrderItemRead(
            product_id=item.product_id,
            product_name=p_name,
            quantity=item.quantity,
            price=item.sell_price, # Sotilgan narxni ko'rsatamiz
            total=item.sell_price * item.quantity,
            is_bonus=item.is_bonus
        )
        if item.is_bonus:
            bonus_data.append(item_read)
        else:
            items_data.append(item_read)
    
    c_phone = order.courier.phone if (order.courier and order.courier.phone) else None

    return OrderRead(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        base_total_amount=order.base_total_amount,
        final_total_amount=order.final_total_amount,
        is_price_locked=order.is_price_locked,
        delivery_time=order.delivery_time,
        created_at=order.created_at,
        assigned_at=order.assigned_at,
        accepted_at=order.accepted_at,
        delivered_at=order.delivered_at,
        user_id=order.user_id,
        user_name=order.user.name,
        user_phone=order.user.phone,
        user_address=order.user.address,
        user_telegram_id=order.user.telegram_id,
        user_type=order.user.user_type,
        courier_id=order.courier_id,
        courier_name=order.courier.name if order.courier else None,
        courier_phone=c_phone,
        rating=order.rating,
        rating_comment=order.rating_comment,
        items=items_data,
        bonus_items=bonus_data
    )

def format_order_list_response(order: Order) -> OrderList:
    bonus_list = []
    has_bonus = False
    for item in order.items:
        if item.is_bonus:
            has_bonus = True
            p_name = item.product.name if item.product else "Noma'lum"
            bonus_list.append(f"{p_name} ({item.quantity})")
    
    bonus_desc = ", ".join(bonus_list) if bonus_list else None

    return OrderList(
        id=order.id,
        user_id=order.user_id,
        courier_id=order.courier_id,
        user_name=order.user.name,
        user_phone=order.user.phone,
        courier_name=order.courier.name if order.courier else None,
        status=order.status,
        rating=order.rating,
        rating_comment=order.rating_comment,
        total_amount=order.total_amount,
        base_total_amount=order.base_total_amount,
        final_total_amount=order.final_total_amount,
        is_price_locked=order.is_price_locked,
        has_bonus=has_bonus,
        bonus_description=bonus_desc
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
    
    # LIMIT TEKSHIRUVI: Foydalanuvchining faol buyurtmalari sonini tekshiramiz
    active_orders_count = db.query(Order).filter(
        Order.user_id == user.id,
        Order.status.in_(["kutilmoqda", "kuryerda"])
    ).count()
    
    if active_orders_count >= MAX_USER_PENDING_ORDERS:
        raise HTTPException(
            status_code=400, 
            detail=f"Sizda {active_orders_count} ta faol buyurtma bor. Yangi buyurtma berish uchun avvalgi buyurtmalaringiz yetkazilishini kuting."
        )
    
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
    db_order.base_total_amount = total_price
    db_order.final_total_amount = total_price
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

# Admin uchun GET
@router.get("/admin/", response_model=List[OrderList], summary="Barcha buyurtmalarni olish (Admin)")
def get_orders_admin(
    status: str = None, 
    limit: int = 5, 
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Admin uchun barcha buyurtmalar ro'yxatini olish.**
    
    - Faqat qisqacha ma'lumot (OrderList) qaytaradi.
    - Status bo'yicha filtrlash mumkin.
    """
    query = db.query(Order).options(
        joinedload(Order.user),
        joinedload(Order.courier)
    )
    
    # Status mapping
    if status:
        status_map = {
            "pending": "kutilmoqda",
            "in_courier": "kuryerda",
            "in the courier": "kuryerda",
            "delivered": "yetkazildi"
        }
        db_status = status_map.get(status.lower().strip(), status)
        query = query.filter(Order.status == db_status)
    
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    return [format_order_list_response(o) for o in orders]

# Kuryer uchun GET
@router.get("/courier/", response_model=List[OrderRead], summary="Kuryerning o'z buyurtmalarini olish")
def get_orders_courier(
    telegram_id: str,
    status: str = None,
    limit: int = 5,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    **Kuryerning o'ziga biriktirilgan buyurtmalarni olish.**
    
    - **telegram_id**: Kuryerning Telegram ID si (Majburiy).
    - To'liq ma'lumot (OrderRead) qaytaradi.
    """
    courier = db.query(Courier).filter(Courier.telegram_id == telegram_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
    
    query = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.user),
        joinedload(Order.courier)
    ).filter(Order.courier_id == courier.id)
    
    if status:
        status_map = {
            "pending": "kutilmoqda",
            "in_courier": "kuryerda",
            "delivered": "yetkazildi"
        }
        db_status = status_map.get(status.lower().strip(), status)
        query = query.filter(Order.status == db_status)
        
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    return [format_order_response(o) for o in orders]

# User uchun GET
@router.get("/user/", response_model=List[OrderRead], summary="Foydalanuvchining o'z buyurtmalarini olish")
def get_orders_user(
    telegram_id: str,
    status: str = None,
    limit: int = 5,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    **Foydalanuvchining (User) o'z buyurtmalarini olish.**
    
    - **telegram_id**: Foydalanuvchining Telegram ID si (Majburiy).
    - To'liq ma'lumot (OrderRead) qaytaradi.
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    query = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.user),
        joinedload(Order.courier)
    ).filter(Order.user_id == user.id)
    
    if status:
        status_map = {
            "pending": "kutilmoqda",
            "in_courier": "kuryerda",
            "delivered": "yetkazildi"
        }
        db_status = status_map.get(status.lower().strip(), status)
        query = query.filter(Order.status == db_status)
        
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    return [format_order_response(o) for o in orders]

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
    
    courier = db.query(Courier).filter(Courier.telegram_id == data.courier_telegram_id).first()
    if not courier or order.courier_id != courier.id:
        raise HTTPException(status_code=403, detail="Faqat biriktirilgan kuryer buyurtmani qabul qila oladi")

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
async def deliver_order(order_id: int, data: OrderDeliver, db: Session = Depends(get_db)):
    """
    **Buyurtma yetkazib berilganda ishlatiladi.**
    
    - Status **yetkazildi** ga o'zgaradi.
    - **delivered_at** vaqti belgilanadi.
    - Admin va Mijozga xabar boradi.
    """
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Topilmadi")
    
    courier = db.query(Courier).filter(Courier.telegram_id == data.courier_telegram_id).first()
    if not courier or order.courier_id != courier.id:
        raise HTTPException(status_code=403, detail="Faqat biriktirilgan kuryer yetkazildi deb belgilay oladi")

    if not order.is_price_locked:
        raise HTTPException(status_code=400, detail="Buyurtmani yetkazildi deb belgilashdan avval narxni bloklash (lock-price) shart")

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
async def add_bonus_items(order_id: int, data: OrderBonus, db: Session = Depends(get_db)):
    """
    **Kuryer tomonidan buyurtmaga bonus qo'shish.**
    
    - Faqat **kuryerda** statusida ishlaydi.
    - Mahsulot **narxi 0** deb hisoblanadi (tekin).
    - Ombor qoldig'i kamayadi, lekin umumiy savdo summasi o'zgarmaydi.
    """
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    courier = db.query(Courier).filter(Courier.telegram_id == data.courier_telegram_id).first()
    if not courier or order.courier_id != courier.id:
        raise HTTPException(status_code=403, detail="Faqat biriktirilgan kuryer bonus qo'shishi mumkin")

    if order.status != "kuryerda":
        raise HTTPException(status_code=400, detail="Faqat kuryerdagi buyurtmalarga bonus qo'shish mumkin")
    
    for item in data.items:
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

@router.patch("/{order_id}/update-price/", response_model=OrderRead, summary="Buyurtma narxini o'zgartirish (Kuryer)")
async def update_order_price(order_id: int, data: OrderPriceUpdate, db: Session = Depends(get_db)):
    """
    **Kuryer tomonidan buyurtma narxini o'zgartirish.**
    
    - Faqat biriktirilgan kuryer o'zgartira oladi.
    - Narx bloklanmagan (locked) bo'lishi kerak.
    - Har bir o'zgarish loglanadi.
    """
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    if order.is_price_locked:
        raise HTTPException(status_code=400, detail="Narx bloklangan, uni o'zgartirib bo'lmaydi")
    
    courier = db.query(Courier).filter(Courier.telegram_id == data.courier_telegram_id).first()
    if not courier or order.courier_id != courier.id:
        raise HTTPException(status_code=403, detail="Faqat biriktirilgan kuryer narxni o'zgartira oladi")
    
    # Log the change
    history = OrderPriceHistory(
        order_id=order.id,
        courier_id=courier.id,
        previous_price=order.final_total_amount,
        new_price=data.new_price
    )
    db.add(history)
    
    order.final_total_amount = data.new_price
    db.commit()
    db.refresh(order)
    
    return format_order_response(order)

@router.patch("/{order_id}/lock-price/", response_model=OrderRead, summary="Buyurtma narxini bloklash (Kuryer)")
async def lock_order_price(order_id: int, data: OrderLock, db: Session = Depends(get_db)):
    """
    **Kuryer tomonidan buyurtma narxini yakuniy deb bloklash.**
    
    - Bloklangandan keyin narxni o'zgartirib bo'lmaydi.
    - Bu narx moliya tizimi uchun asosiy manba hisoblanadi.
    """
    order = db.query(Order).options(joinedload(Order.user), joinedload(Order.courier)).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    
    courier = db.query(Courier).filter(Courier.telegram_id == data.courier_telegram_id).first()
    if not courier or order.courier_id != courier.id:
        raise HTTPException(status_code=403, detail="Faqat biriktirilgan kuryer narxni bloklay oladi")
    
    order.is_price_locked = True
    db.commit()
    db.refresh(order)
    
    return format_order_response(order)


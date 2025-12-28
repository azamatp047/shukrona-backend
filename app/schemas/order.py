from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- KICHIK QISMLAR (Order ichidagi mahsulotlar uchun) ---

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderItemRead(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float
    total: float
    is_bonus: bool = False # Yangi

    class Config:
        from_attributes = True

# --- ASOSIY ORDER SCHEMALARI ---

# 1. Order Yaratish (Frontdan keladigan - telegram_id bilan)
class OrderCreate(BaseModel):
    telegram_id: str 
    items: List[OrderItemCreate]
    delivery_time: Optional[str] = None

# 2. Order ma'lumotlarini o'qish (Javob uchun)
class OrderList(BaseModel):
    id: int
    user_id: int
    courier_id: Optional[int] = None
    user_name: str
    user_phone: str
    courier_name: Optional[str] = None
    status: str
    rating: Optional[int] = None
    rating_comment: Optional[str] = None
    total_amount: float
    base_total_amount: float
    final_total_amount: float
    is_price_locked: bool
    has_bonus: bool = False # Yangi
    bonus_description: Optional[str] = None # Masalan: "Suv (1), Non (2)"

    class Config:
        from_attributes = True

class OrderRead(BaseModel):
    id: int
    status: str
    total_amount: float
    base_total_amount: float
    final_total_amount: float
    is_price_locked: bool
    delivery_time: Optional[str] = None
    created_at: datetime
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # User ma'lumotlari
    user_id: int
    user_name: str
    user_phone: str
    user_address: str
    user_telegram_id: str
    user_type: str # Yangi
    
    # Courier ma'lumotlari
    courier_id: Optional[int] = None
    courier_name: Optional[str] = None
    courier_phone: Optional[str] = None
    
    # Rating
    rating: Optional[int] = None
    rating_comment: Optional[str] = None
    
    # Mahsulotlar ro'yxati
    items: List[OrderItemRead]
    bonus_items: List[OrderItemRead] = [] # Faqat bonuslar uchun alohida ro'yxat

    class Config:
        from_attributes = True

# Kuryer biriktirish uchun
class OrderAssign(BaseModel):
    courier_id: int

# Kuryer qabul qilishi uchun (vaqt bilan)
class OrderAccept(BaseModel):
    delivery_time: str
    courier_telegram_id: str

class OrderDeliver(BaseModel):
    courier_telegram_id: str

# Rating berish uchun
class OrderRate(BaseModel):
    rating: int # 1-5
    comment: Optional[str] = None

class BonusItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderBonus(BaseModel):
    courier_telegram_id: str
    items: List[BonusItemCreate]

class OrderPriceUpdate(BaseModel):
    new_price: float
    courier_telegram_id: str

class OrderLock(BaseModel):
    courier_telegram_id: str
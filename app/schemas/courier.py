from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CourierBase(BaseModel):
    name: str
    phone: Optional[str] = None
    tg_username: Optional[str] = None
    telegram_id: str

class CourierCreate(CourierBase):
    pass

class CourierUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    tg_username: Optional[str] = None
    telegram_id: Optional[str] = None
    status: Optional[str] = None

class CourierRead(CourierBase):
    id: int
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# --- TARIX VA STATISTIKA UCHUN ---

class CourierOrderSummary(BaseModel):
    order_id: int
    total_amount: float
    delivered_at: datetime
    user_name: str # Yangi qoshildi
    user_address: str
    rating: Optional[int] = None
    rating_comment: Optional[str] = None 

    class Config:
        from_attributes = True

class CourierStats(BaseModel):
    courier_id: int
    courier_name: str
    
    total_delivered_orders: int # Nechta buyurtma yetkazdi
    total_money_collected: float # Qancha summa yig'di (savdo)
    average_rating: float = 0.0 # O'rtacha baho
    
    # Tarix ro'yxati
    history: List[CourierOrderSummary]
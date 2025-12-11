from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class OrderBase(BaseModel):
    user_id: int
    product_id: int

class OrderCreate(OrderBase):
    pass

class OrderRead(OrderBase):
    id: int
    courier_id: Optional[int] = None
    status: str
    delivery_time: Optional[str] = None
    created_at: datetime
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

class OrderAssign(BaseModel):
    courier_id: int

class OrderAccept(BaseModel):
    delivery_time: str  # "3 soat", "2 kun"

class OrderStatusUpdate(BaseModel):
    status: str  # created, assigned, accepted, delivering, delivered, completed

class OrderWithDetails(BaseModel):
    id: int
    status: str
    delivery_time: Optional[str] = None
    created_at: datetime
    user: dict  # {id, name, phone, address}
    product: dict  # {id, name, price}
    courier: Optional[dict] = None  # {id, name}

    model_config = {
        "from_attributes": True
    }
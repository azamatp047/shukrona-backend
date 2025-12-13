from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    name: str
    phone: str
    address: str

class UserCreate(UserBase):
    telegram_id: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class UserRead(UserBase):
    id: int
    telegram_id: str
    status: str

    model_config = {
        "from_attributes": True
    }
from pydantic import BaseModel
from typing import Optional, List

class UserBase(BaseModel):
    name: str
    phone: str
    address: str

class UserCreate(UserBase):
    telegram_id: str
    user_type: Optional[str] = "standard"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    user_type: Optional[str] = None

class UserRead(UserBase):
    id: int
    telegram_id: str
    status: str
    user_type: str

    model_config = {
        "from_attributes": True
    }

class UserShort(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class UserStats(BaseModel):
    total_count: int
    active_count: int
    blocked_count: int

class UserListResponse(BaseModel):
    total_count: int
    active_count: int
    blocked_count: int
    limit: int
    users: List[UserRead]
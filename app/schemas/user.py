from pydantic import BaseModel

class UserBase(BaseModel):
    name: str
    phone: str
    address: str

class UserCreate(UserBase):
    telegram_id: str

class UserRead(UserBase):
    id: int
    telegram_id: str
    status: str

    class Config:
        orm_mode = True

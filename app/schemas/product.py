from pydantic import BaseModel
from typing import Optional

class ProductBase(BaseModel):
    name: str
    buy_price: float # Olish narxi
    sell_price: float # Sotish narxi (Userga shu ko'rinadi)
    stock: int # Ombor

class ProductCreate(ProductBase):
    # Rasm alohida keladi
    pass 

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None
    stock: Optional[int] = None
    status: Optional[str] = None

class ProductUserRead(BaseModel):
    id: int
    name: str
    sell_price: float
    image: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class ProductAdminRead(ProductBase):
    id: int
    image: Optional[str] = None
    status: str

    model_config = {
        "from_attributes": True
    }

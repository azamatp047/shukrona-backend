from pydantic import BaseModel
from typing import Optional

# Asosiy baza klass (umumiy maydonlar)
class ProductBase(BaseModel):
    name: str
    price: float

# Yaratish uchun ishlatiladigan klass
class ProductCreate(ProductBase):
    pass 

# Yangilash (Update) uchun klass
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None

# 1. Ro'yxat uchun (GET /products) - Faqat ID va Name
class ProductListRead(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }

# 2. Bittalik mahsulot uchun (GET /products/{id}) - To'liq ma'lumot
class ProductDetailRead(ProductBase):
    id: int
    image: Optional[str] = None
    status: str

    model_config = {
        "from_attributes": True
    }
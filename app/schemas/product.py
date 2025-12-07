from pydantic import BaseModel

class ProductCreate(BaseModel):
    name: str
    price: float
    image: str

class ProductRead(BaseModel):
    id: int
    name: str
    price: float
    image: str

    model_config = {
        "from_attributes": True
    }

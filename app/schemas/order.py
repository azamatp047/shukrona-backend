from pydantic import BaseModel

class OrderBase(BaseModel):
    user_id: int
    product_id: int

class OrderCreate(OrderBase):
    pass

class OrderRead(OrderBase):
    id: int
    courier_id: int | None
    status: str
    delivery_time: str | None

    model_config = {
        "from_attributes": True
    }
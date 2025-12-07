from pydantic import BaseModel

class CourierBase(BaseModel):
    name: str
    tg_username: str
    telegram_id: str

class CourierCreate(CourierBase):
    pass

class CourierRead(CourierBase):
    id: int

    model_config = {
        "from_attributes": True
    }
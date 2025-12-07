from pydantic import BaseModel

class AdminCreate(BaseModel):
    telegram_id: int
    password: str

class AdminResponse(BaseModel):
    id: int
    telegram_id: int

    model_config = {
        "from_attributes": True
    }
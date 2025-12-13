from pydantic import BaseModel

class AdminCreate(BaseModel):
    telegram_id: str  # <--- DIQQAT: int emas, str bo'lishi kerak
    password: str

class AdminResponse(BaseModel):
    id: int
    telegram_id: str # <--- Bu yerda ham str qilsangiz yaxshi

    model_config = {
        "from_attributes": True
    }
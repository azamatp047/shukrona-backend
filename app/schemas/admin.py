from pydantic import BaseModel

class AdminCreate(BaseModel):
    telegram_id: str
    username: str
    password: str

class AdminResponse(BaseModel):
    id: int
    telegram_id: str
    username: str

    class Config:
        from_attributes = True

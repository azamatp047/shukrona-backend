from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Courier
from app.schemas.courier import CourierCreate, CourierRead
from app.dependencies import require_admin # Admin check

router = APIRouter(prefix="/couriers", tags=["Couriers"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=CourierRead, status_code=201)
def create_courier(
    courier: CourierCreate, 
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin) # <-- Faqat admin
):
    db_courier = Courier(**courier.model_dump())
    db.add(db_courier)
    db.commit()
    db.refresh(db_courier)
    return db_courier

@router.get("/", response_model=List[CourierRead])
def get_couriers(
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin) # <-- Ro'yxatni ham faqat admin ko'rsin
):
    return db.query(Courier).all()
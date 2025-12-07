from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Courier
from app.schemas.courier import CourierCreate, CourierRead

router = APIRouter(prefix="/couriers", tags=["Couriers"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=CourierRead, status_code=201)
def create_courier(courier: CourierCreate, db: Session = Depends(get_db)):
    # optional validation
    if not courier.name:
        raise HTTPException(status_code=400, detail="Courier name is required")

    db_courier = Courier(**courier.model_dump())
    db.add(db_courier)
    db.commit()
    db.refresh(db_courier)
    return db_courier


@router.get("/", response_model=List[CourierRead])
def get_couriers(db: Session = Depends(get_db)):
    return db.query(Courier).all()
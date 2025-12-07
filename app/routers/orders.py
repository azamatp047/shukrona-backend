from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Order
from app.schemas.order import OrderCreate, OrderRead

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=OrderRead, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # optional: validate that user_id/product_id exist, etc.
    db_order = Order(**order.model_dump())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@router.get("/", response_model=List[OrderRead])
def get_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Product
from app.schemas.product import ProductCreate, ProductRead

router = APIRouter(prefix="/products", tags=["Products"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=ProductRead, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    # simple validation example (optional)
    if not product.name:
        raise HTTPException(status_code=400, detail="Product name is required")

    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/", response_model=List[ProductRead])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()
import shutil
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Product
from app.schemas.product import ProductCreate, ProductListRead, ProductDetailRead
from app.config import UPLOAD_DIR
from app.dependencies import require_admin

router = APIRouter(prefix="/products", tags=["Products"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_upload_file(upload_file: UploadFile) -> str:
    extension = os.path.splitext(upload_file.filename)[1]
    new_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return f"/static/images/{new_filename}"

# CREATE
@router.post("/", response_model=ProductDetailRead)
def create_product(
    name: str = Form(...),
    buy_price: float = Form(...),  # <-- Yangi
    sell_price: float = Form(...), # <-- Yangi
    stock: int = Form(...),        # <-- Yangi
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    image_url = save_upload_file(image)
    # price degan ustunni sell_price ga o'zgartirdik modelda
    db_product = Product(
        name=name, 
        buy_price=buy_price, 
        sell_price=sell_price, 
        stock=stock, 
        image=image_url
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# UPDATE
@router.put("/{product_id}", response_model=ProductDetailRead)
def update_product(
    product_id: int,
    name: Optional[str] = Form(None),
    buy_price: Optional[float] = Form(None),
    sell_price: Optional[float] = Form(None),
    stock: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

    if name: product.name = name
    if buy_price is not None: product.buy_price = buy_price
    if sell_price is not None: product.sell_price = sell_price
    if stock is not None: product.stock = stock
    if status: product.status = status
    
    if image:
        product.image = save_upload_file(image)

    db.commit()
    db.refresh(product)
    return product

# GET (List)
@router.get("/", response_model=List[ProductListRead])
def get_products(db: Session = Depends(get_db)):
    # Userga faqat aktiv va omborda bor mahsulotlarni ko'rsatsa maqsadga muvofiq
    # Lekin "stock=0" bo'lsa ham ko'rsatish kerak bo'lsa filter qilmang
    return db.query(Product).filter(Product.status == "active").all()

# GET (Detail)
@router.get("/{product_id}", response_model=ProductDetailRead)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    return product

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Topilmadi")
    product.status = "deleted"
    db.commit()
    return {"message": "O'chirildi"}
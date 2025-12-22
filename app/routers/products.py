from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from cloudinary.uploader import upload as cloud_upload, destroy as cloud_destroy
import cloudinary

from app.database import SessionLocal
from app.models import Product
from app.schemas.product import ProductListRead, ProductDetailRead
from app.dependencies import require_admin
from app.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

# Cloudinary config
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

router = APIRouter(prefix="/products", tags=["Products"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cloudinary helper functions
def upload_to_cloudinary(file) -> dict:
    result = cloud_upload(file, folder="products", overwrite=True)
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"]
    }

def delete_from_cloudinary(public_id: Optional[str]):
    if public_id:
        cloud_destroy(public_id)

# CREATE
@router.post("/", response_model=ProductDetailRead, summary="Yangi mahsulot qo'shish")
def create_product(
    name: str = Form(...),
    buy_price: float = Form(...),
    sell_price: float = Form(...),
    stock: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Omborga yangi mahsulot qo'shish (Admin).**
    
    - **name**: Mahsulot nomi.
    - **buy_price**: Sotib olingan narxi (tannarx).
    - **sell_price**: Sotuv narxi.
    - **stock**: Ombor qoldig'i (dona).
    - **image**: Rasm fayli (Cloudinary ga yuklanadi).
    """
    upload_result = upload_to_cloudinary(image.file)
    db_product = Product(
        name=name,
        buy_price=buy_price,
        sell_price=sell_price,
        stock=stock,
        image=upload_result["url"]
    )
    # Saqlash uchun public_id DB’da saqlash kerak bo‘lsa, yangi ustun qo‘shish mumkin
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# UPDATE
@router.put("/{product_id}", response_model=ProductDetailRead, summary="Mahsulot ma'lumotlarini tahrirlash")
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
    """
    **Mahsulotni o'zgartirish (Admin).**
    
    - Faqat yuborilgan maydonlar o'zgaradi.
    - Agar yangi **image** yuborilsa, eskisi o'chib yangisi yuklanadi.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

    if name: product.name = name
    if buy_price is not None: product.buy_price = buy_price
    if sell_price is not None: product.sell_price = sell_price
    if stock is not None: product.stock = stock
    if status: product.status = status

    if image:
        # Eski rasmni o'chirish faqat public_id bilan mumkin bo‘ladi
        # agar public_id qo‘shsang, delete_from_cloudinary(product.image_public_id) ishlatiladi
        upload_result = upload_to_cloudinary(image.file)
        product.image = upload_result["url"]

    db.commit()
    db.refresh(product)
    return product

# GET (List)
@router.get("/", response_model=List[ProductListRead], summary="Mahsulotlar ro'yxati (Katalog)")
def get_products(db: Session = Depends(get_db)):
    """
    **Aktiv statusdagi barcha mahsulotlarni olish.**
    
    - Asosan mijozlar ilovasi uchun (rasm va narxlari bilan).
    """
    return db.query(Product).filter(Product.status == "active").all()

# GET (Detail)
@router.get("/{product_id}", response_model=ProductDetailRead, summary="Mahsulot tafsilotlari")
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """
    **ID orqali bitta mahsulotni ko'rish.**
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    return product

# DELETE
@router.delete("/{product_id}", summary="Mahsulotni o'chirish")
def delete_product(product_id: int, db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    """
    **Mahsulotni o'chirish (Soft delete).**
    
    - Bazadan o'chmaydi, faqat statusi **deleted** bo'ladi.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Topilmadi")
    
    # Cloudinary rasmni o'chirish, agar public_id qo‘shilgan bo‘lsa
    # delete_from_cloudinary(product.image_public_id)
    
    # DB status
    product.status = "deleted"
    db.commit()
    return {"message": "O'chirildi"}

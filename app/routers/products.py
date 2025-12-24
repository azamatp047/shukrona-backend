from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
# from app.utils.google_drive import upload_file_to_drive # Endi kerak emas

from app.database import SessionLocal
from app.models import Product
from app.schemas.product import ProductListRead, ProductDetailRead
from app.dependencies import require_admin

router = APIRouter(prefix="/products", tags=["Products"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE
@router.post("/", response_model=ProductDetailRead, summary="Yangi mahsulot qo'shish")
def create_product(
    name: str = Form(...),
    buy_price: float = Form(...),
    sell_price: float = Form(...),
    stock: int = Form(...),
    image: str = Form(...), # Endi shunchaki string (URL) qabul qilamiz
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Omborga yangi mahsulot qo'shish (Admin).**
    
    - **name**: Mahsulot nomi.
    - **buy_price**: Sotib olingan narxi (tannarx).
    - **sell_price**: Sotuv narxi.
    - **stock**: Ombor qoldig'i (dona).
    - **image**: Rasm havolasi (URL).
    """
    try:
        db_product = Product(
            name=name,
            buy_price=buy_price,
            sell_price=sell_price,
            stock=stock,
            image=image # To'g'ridan-to'g'ri URL ni yozamiz
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        print(f"Database Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database xatosi: {str(e)}")

# UPDATE
@router.put("/{product_id}/", response_model=ProductDetailRead, summary="Mahsulot ma'lumotlarini tahrirlash")
def update_product(
    product_id: int,
    name: Optional[str] = Form(None),
    buy_price: Optional[float] = Form(None),
    sell_price: Optional[float] = Form(None),
    stock: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    image: Optional[str] = Form(None), # Bu yerda ham string
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Mahsulotni o'zgartirish (Admin).**
    
    - Faqat yuborilgan maydonlar o'zgaradi.
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
        product.image = image # To'g'ridan-to'g'ri yangilaymiz

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
@router.get("/{product_id}/", response_model=ProductDetailRead, summary="Mahsulot tafsilotlari")
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """
    **ID orqali bitta mahsulotni ko'rish.**
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    return product

# DELETE
@router.delete("/{product_id}/", summary="Mahsulotni o'chirish")
def delete_product(product_id: int, db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    """
    **Mahsulotni o'chirish (Soft delete).**
    
    - Bazadan o'chmaydi, faqat statusi **deleted** bo'ladi.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Topilmadi")
    
    # Cloudinary o'chirish logikasi olib tashlandi
    # Agar Google Drive dan ham o'chirish kerak bo'lsa, alohida file_id saqlash kerak edi
    
    # DB status
    product.status = "deleted"
    db.commit()
    return {"message": "O'chirildi"}

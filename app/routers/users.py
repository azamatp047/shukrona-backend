from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserShort
from app.dependencies import require_admin # Admin tekshiruvi

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. User yaratish (Hamma qila oladi - Bot start bosganda)
@router.post("/", response_model=UserRead, summary="Foydalanuvchini ro'yxatdan o'tkazish")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    **Yangi foydalanuvchi yaratish (Bot /start).**
    
    Agar foydalanuvchi avvaldan bor bo'lsa, eskisini qaytaradi.
    """
    db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if db_user:
        return db_user # Agar bor bo'lsa, o'shani qaytarib beramiz
        
    new_user = User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. Get My Profile (Telegram ID orqali)
@router.get("/me/{telegram_id}/", response_model=UserRead, summary="Mening profilim")
def get_my_profile(telegram_id: str, db: Session = Depends(get_db)):
    """
    **Telegram ID orqali foydalanuvchi ma'lumotlarini olish.**
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Agar user bloklangan bo'lsa xabar berish (ixtiyoriy)
    if user.status == "blocked":
        raise HTTPException(status_code=403, detail="Siz bloklangansiz!")
        
    return user

# 3. Userni update qilish (User o'zi qiladi)
@router.put("/me/{telegram_id}/", response_model=UserRead, summary="Profilni tahrirlash")
def update_my_profile(telegram_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    """
    **Foydalanuvchi o'z ma'lumotlarini o'zgartirishi.**
    
    - Ism, Telefon, Manzil.
    """
    db_user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    if db_user.status == "blocked":
        raise HTTPException(status_code=403, detail="Siz bloklangansiz, o'zgartira olmaysiz.")

    # Kelgan ma'lumotlarni yangilash
    if user_update.name: db_user.name = user_update.name
    if user_update.phone: db_user.phone = user_update.phone
    if user_update.address: db_user.address = user_update.address
    
    db.commit()
    db.refresh(db_user)
    return db_user

# 4. Userni bloklash (Faqat Admin)
@router.post("/{user_id}/block/", summary="Foydalanuvchini bloklash (Admin)")
def block_user(user_id: int, db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    """
    **Foydalanuvchini qora ro'yxatga olish.**
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    user.status = "blocked"
    db.commit()
    return {"message": f"Foydalanuvchi {user.name} bloklandi"}

# 5. Userni blokdan chiqarish (Faqat Admin)
@router.post("/{user_id}/unblock/", summary="Foydalanuvchini blokdan chiqarish (Admin)")
def unblock_user(user_id: int, db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    """
    **Foydalanuvchini faollashtirish.**
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    user.status = "active"
    db.commit()
    return {"message": f"Foydalanuvchi {user.name} faollashtirildi"}

@router.get("/", response_model=list[UserRead], summary="Barcha foydalanuvchilar (Admin)")
def get_all_users(
    status: str = None,
    limit: int = 5,
    offset: int = 0,
    db: Session = Depends(get_db), 
    admin_id: str = Depends(require_admin)
):
    """
    **Tizimdagi barcha mijozlar ro'yxati.**
    
    - **status**: active yoki blocked.
    - **limit**: nechta qaytarish (default 5).
    - **offset**: qanchasini o'tkazib yuborish.
    """
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    
    return query.offset(offset).limit(limit).all()

@router.get("/{user_id}/", response_model=UserRead, summary="Bitta foydalanuvchi ma'lumotlari (Admin)")
def get_one_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    admin_id: str = Depends(require_admin)
):
    """
    **ID orqali bitta foydalanuvchi haqida to'liq ma'lumot olish.**
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return user

@router.get("/search/", response_model=list[UserShort], summary="Foydalanuvchilarni qidirish (Admin)")
def search_users(
    query: str, 
    db: Session = Depends(get_db), 
    admin_id: str = Depends(require_admin)
):
    """
    **Foydalanuvchilarni ismi yoki telefoni orqali qidirish.**
    
    Faqat {id, name} qaytaradi.
    """
    users = db.query(User).filter(
        (User.name.ilike(f"%{query}%")) | (User.phone.ilike(f"%{query}%"))
    ).limit(10).all()
    return users

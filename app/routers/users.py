from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.dependencies import require_admin # Admin tekshiruvi

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. User yaratish (Hamma qila oladi - Bot start bosganda)
@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if db_user:
        return db_user # Agar bor bo'lsa, o'shani qaytarib beramiz
        
    new_user = User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. Get My Profile (Telegram ID orqali)
@router.get("/me/{telegram_id}", response_model=UserRead)
def get_my_profile(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Agar user bloklangan bo'lsa xabar berish (ixtiyoriy)
    if user.status == "blocked":
        raise HTTPException(status_code=403, detail="Siz bloklangansiz!")
        
    return user

# 3. Userni update qilish (User o'zi qiladi)
@router.put("/me/{telegram_id}", response_model=UserRead)
def update_my_profile(telegram_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
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
@router.post("/{user_id}/block")
def block_user(user_id: int, db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    user.status = "blocked"
    db.commit()
    return {"message": f"Foydalanuvchi {user.name} bloklandi"}

# 5. Userni blokdan chiqarish (Faqat Admin)
@router.post("/{user_id}/unblock")
def unblock_user(user_id: int, db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    user.status = "active"
    db.commit()
    return {"message": f"Foydalanuvchi {user.name} faollashtirildi"}

@router.get("/", response_model=list[UserRead])
def get_all_users(db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    return db.query(User).all()
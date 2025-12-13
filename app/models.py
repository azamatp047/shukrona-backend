from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    address = Column(String)
    telegram_id = Column(String, unique=True, index=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="user")

class Courier(Base):
    __tablename__ = "couriers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, nullable=True)
    tg_username = Column(String)
    telegram_id = Column(String, unique=True, index=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="courier")
    salaries = relationship("SalaryPayment", back_populates="courier")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    buy_price = Column(Float, default=0.0)
    sell_price = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    image = Column(String, nullable=True)
    image_public_id = Column(String, nullable=True)  # Cloudinary
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    order_items = relationship("OrderItem", back_populates="product")
    

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=True)
    
    # Statuslar: "kutilmoqda", "kuryerda", "yetkazildi"
    status = Column(String, default="kutilmoqda")
    
    delivery_time = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    total_amount = Column(Float, default=0.0) # Faqat sotish narxi bo'yicha summa
    
    user = relationship("User", back_populates="orders")
    courier = relationship("Courier", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity = Column(Integer, default=1)
    
    # Sotilgan vaqtdagi narxlar (Tarix uchun muhim)
    buy_price = Column(Float, default=0.0)  # O'sha paytdagi tannarx
    sell_price = Column(Float, default=0.0) # O'sha paytdagi sotuv narxi
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

# YANGI: Ishchilarga oylik berish
class SalaryPayment(Base):
    __tablename__ = "salary_payments"
    id = Column(Integer, primary_key=True, index=True)
    courier_id = Column(Integer, ForeignKey("couriers.id"))
    
    amount = Column(Float) # Berilgan summa
    percentage = Column(Float) # Necha foiz hisoblandi (masalan 5%)
    
    start_date = Column(Date) # Qaysi sanadan
    end_date = Column(Date)   # Qaysi sanagacha hisoblandi
    
    paid_at = Column(DateTime, default=datetime.utcnow) # To'langan vaqt
    note = Column(Text, nullable=True)
    
    courier = relationship("Courier", back_populates="salaries")

# YANGI: Boshqa chiqimlar (Arenda, Svet, Gaz va h.k)
class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    note = Column(String) # Nima uchun?
    created_at = Column(DateTime, default=datetime.utcnow)

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
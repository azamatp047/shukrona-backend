from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
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
    tg_username = Column(String)
    telegram_id = Column(String, unique=True, index=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="courier")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    image = Column(String, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=True)
    
    # Status: created -> assigned -> accepted -> delivering -> delivered -> completed
    status = Column(String, default="created")
    
    # Vaqt ma'lumotlari
    delivery_time = Column(String, nullable=True)  # "3 soat", "2 kun"
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)  # Admin kuryer biriktirganda
    accepted_at = Column(DateTime, nullable=True)  # Kuryer qabul qilganda
    delivered_at = Column(DateTime, nullable=True)  # Yetkazilganda
    
    # Relationships
    user = relationship("User", back_populates="orders")
    product = relationship("Product", back_populates="orders")
    courier = relationship("Courier", back_populates="orders")
    transaction = relationship("Transaction", back_populates="order", uselist=False)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    amount = Column(Float)  # Mahsulot narxi
    type = Column(String, default="income")  # income (kirim)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)
    
    order = relationship("Order", back_populates="transaction")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String)
    password_hash = Column(String)  # Hash qilingan parol
    created_at = Column(DateTime, default=datetime.utcnow)
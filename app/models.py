from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    address = Column(String)
    telegram_id = Column(String, unique=True)
    status = Column(String, default="active")

class Courier(Base):
    __tablename__ = "couriers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    tg_username = Column(String)
    telegram_id = Column(String, unique=True)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    image = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=True)
    status = Column(String, default="created")  # created, assigned, delivered
    delivery_time = Column(String, nullable=True)  # "3 soat", "2 kun"

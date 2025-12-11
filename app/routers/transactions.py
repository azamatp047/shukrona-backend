from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Transaction, Order

router = APIRouter(prefix="/transactions", tags=["Transactions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_transactions(
    type: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Barcha transactionlarni olish"""
    query = db.query(Transaction)
    
    if type:
        query = query.filter(Transaction.type == type)
    
    transactions = query.offset(skip).limit(limit).all()
    
    # To'liq ma'lumot bilan qaytarish
    result = []
    for trans in transactions:
        trans_dict = {
            "id": trans.id,
            "order_id": trans.order_id,
            "amount": trans.amount,
            "type": trans.type,
            "description": trans.description,
            "created_at": trans.created_at
        }
        
        # Order ma'lumotlarini qo'shish
        if trans.order:
            trans_dict["order_details"] = {
                "id": trans.order.id,
                "product_name": trans.order.product.name,
                "user_name": trans.order.user.name
            }
        
        result.append(trans_dict)
    
    return result

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Umumiy kirim-chiqim hisoboti"""
    
    # Jami kirim
    total_income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == "income"
    ).scalar() or 0
    
    # Jami chiqim
    total_expense = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == "expense"
    ).scalar() or 0
    
    # Transactionlar soni
    total_count = db.query(Transaction).count()
    
    # Yetkazilgan orderlar soni
    delivered_orders = db.query(Order).filter(Order.status == "delivered").count()
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": total_income - total_expense,
        "total_transactions": total_count,
        "delivered_orders": delivered_orders
    }

@router.get("/daily")
def get_daily_report(
    start_date: str = Query(None, description="YYYY-MM-DD format"),
    end_date: str = Query(None, description="YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Kunlik hisobot"""
    query = db.query(Transaction)
    
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(Transaction.created_at >= start)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.filter(Transaction.created_at <= end)
    
    transactions = query.all()
    
    # Guruhlab hisoblash
    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "income": income,
        "expense": expense,
        "profit": income - expense,
        "count": len(transactions)
    }
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date

from app.database import SessionLocal
from app.models import Order, OrderItem, SalaryPayment, Expense, Courier, Product
from app.schemas.finance import (
    ProfitStats, SalaryCalculateRequest, SalaryCalculationResponse,
    SalaryPaymentCreate, SalaryPaymentRead, 
    ExpenseCreate, ExpenseRead, ProductPerformance
)
from app.dependencies import require_admin

router = APIRouter(prefix="/finance", tags=["Finance & Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/stats/", response_model=ProfitStats, summary="Moliyaviy hisobot va statistika")
def get_analytics(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Kompaniyaning umumiy moliyaviy holati.**
    
    - **start_date**, **end_date**: Filtrlash uchun sanalar.
    - Sof foyda, Yalpi daromad, Xarajatlar va Mahsulotlar kesimida statistika.
    """
    # 1. Yetkazilgan buyurtmalarni olamiz
    query = db.query(Order).filter(Order.status == "yetkazildi")
    
    if start_date:
        query = query.filter(func.date(Order.delivered_at) >= start_date)
    if end_date:
        query = query.filter(func.date(Order.delivered_at) <= end_date)
    
    orders = query.options(joinedload(Order.items).joinedload(OrderItem.product)).all()
    
    # 2. Hisob-kitoblar uchun o'zgaruvchilar
    total_revenue = 0.0
    total_cogs = 0.0
    sold_items_count = 0
    
    # Mahsulotlar bo'yicha guruhlash
    product_stats: Dict[int, dict] = {}
    
    for order in orders:
        total_revenue += order.final_total_amount
        for item in order.items:
            cog = item.buy_price * item.quantity
            total_cogs += cog
            sold_items_count += item.quantity
            
            # Mahsulot kesimida hisob
            p_id = item.product_id
            if p_id not in product_stats:
                p_name = item.product.name if item.product else "O'chirilgan"
                product_stats[p_id] = {
                    "name": p_name,
                    "qty": 0,
                    "revenue": 0.0,
                    "cogs": 0.0
                }
            
            product_stats[p_id]["qty"] += item.quantity
            product_stats[p_id]["revenue"] += (item.sell_price * item.quantity)
            product_stats[p_id]["cogs"] += cog

    # 3. ProductPerformance ro'yxatini shakllantirish
    breakdown_list = []
    for pid, data in product_stats.items():
        gross = data["revenue"] - data["cogs"]
        margin = (gross / data["revenue"] * 100) if data["revenue"] > 0 else 0.0
        
        breakdown_list.append(ProductPerformance(
            product_id=pid,
            product_name=data["name"],
            sold_quantity=data["qty"],
            total_revenue=data["revenue"],
            total_cogs=data["cogs"],
            gross_profit=gross,
            margin_percent=round(margin, 2)
        ))
    
    # 4. Chiqimlar (Oylik va Boshqa xarajatlar)
    salary_query = db.query(func.sum(SalaryPayment.amount))
    expense_query = db.query(func.sum(Expense.amount))
    
    if start_date:
        salary_query = salary_query.filter(func.date(SalaryPayment.paid_at) >= start_date)
        expense_query = expense_query.filter(func.date(Expense.created_at) >= start_date)
    if end_date:
        salary_query = salary_query.filter(func.date(SalaryPayment.paid_at) <= end_date)
        expense_query = expense_query.filter(func.date(Expense.created_at) <= end_date)

    total_salaries = salary_query.scalar() or 0.0
    total_expenses = expense_query.scalar() or 0.0
    
    gross_profit = total_revenue - total_cogs
    net_profit = gross_profit - total_salaries - total_expenses
    
    return ProfitStats(
        total_revenue=total_revenue,
        total_cogs=total_cogs,
        gross_profit=gross_profit,
        total_salaries=total_salaries,
        total_expenses=total_expenses,
        net_profit=net_profit,
        sold_items_count=sold_items_count,
        products_breakdown=breakdown_list
    )

@router.get("/calculate-salary/", response_model=SalaryCalculationResponse, summary="Kuryer oyligini hisoblash (Saqlamasdan)")
def calculate_salary(
    courier_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Kuryerning ish haqqini hisoblab beradi.**
    
    Bu endpoint bazaga saqlamaydi, faqat hisoblab javob qaytaradi.
    """
    courier = db.query(Courier).filter(Courier.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
        
    orders = db.query(Order).filter(
        Order.courier_id == courier_id,
        Order.status == "yetkazildi",
        func.date(Order.delivered_at) >= start_date,
        func.date(Order.delivered_at) <= end_date
    ).options(joinedload(Order.items)).all()
    
    total_sales = sum(order.final_total_amount for order in orders)
    items_count = sum(sum(item.quantity for item in order.items) for order in orders)
    
    return SalaryCalculationResponse(
        courier_id=courier_id,
        courier_name=courier.name,
        total_sales=total_sales,
        orders_count=len(orders),
        items_count=items_count,
        start_date=start_date,
        end_date=end_date
    )

@router.post("/pay-salary/", response_model=SalaryPaymentRead, summary="Oylik to'lovini saqlash")
def pay_courier_salary(
    data: SalaryPaymentCreate,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Kuryerga oylik to'langanligi haqida ma'lumotni saqlash.**
    
    Bu endpoint hisob-kitob qilmaydi, faqat yuborilgan ma'lumotlarni bazaga yozadi.
    """
    courier = db.query(Courier).filter(Courier.id == data.courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Kuryer topilmadi")
        
    payment = SalaryPayment(
        courier_id=data.courier_id,
        amount=data.amount,
        percentage=0.0, # Removed feature
        start_date=data.start_date,
        end_date=data.end_date
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    payment.courier_name = courier.name 
    return payment

@router.get("/salaries/", response_model=List[SalaryPaymentRead], summary="Barcha oylik to'lovlari ro'yxati (Admin)")
def get_salary_payments(
    courier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Tizimda saqlangan barcha oylik to'lovlarini ko'rish.**
    """
    query = db.query(SalaryPayment).options(joinedload(SalaryPayment.courier))
    
    if courier_id:
        query = query.filter(SalaryPayment.courier_id == courier_id)
        
    payments = query.order_by(SalaryPayment.paid_at.desc()).all()
    
    # Kuryer ismlarini Schema uchun tayyorlaymiz
    for p in payments:
        p.courier_name = p.courier.name if p.courier else "O'chirilgan kuryer"
        
    return payments

@router.delete("/salaries/{payment_id}/", summary="Oylik to'lovini o'chirish (Admin)")
def delete_salary_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Berilgan oylik to'lovini tizimdan o'chirish.**
    
    Xatolik yuz berganda to'lovni bekor qilish uchun ishlatiladi.
    """
    payment = db.query(SalaryPayment).filter(SalaryPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="To'lov topilmadi")
    
    db.delete(payment)
    db.commit()
    return {"status": "ok", "message": "Oylik to'lovi muvaffaqiyatli o'chirildi"}

@router.post("/expenses/", response_model=ExpenseRead, summary="Yangi xarajat qo'shish")
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Qo'shimcha xarajatlarni kiritish.**
    
    - Masalan: Arenda, Kommunal, Internet va boshqalar.
    """
    expense = Expense(**data.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

@router.get("/expenses/", response_model=List[ExpenseRead], summary="Barcha xarajatlar ro'yxati")
def get_expenses(db: Session = Depends(get_db), admin_id: str = Depends(require_admin)):
    """
    **Tizimga kiritilgan barcha xarajatlar.**
    """
    return db.query(Expense).all()

@router.delete("/expenses/{expense_id}/", summary="Xarajatni o'chirish (Admin)")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    admin_id: str = Depends(require_admin)
):
    """
    **Kiritilgan xarajatni tizimdan o'chirish.**
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Xarajat topilmadi")
    
    db.delete(expense)
    db.commit()
    return {"status": "ok", "message": "Xarajat muvaffaqiyatli o'chirildi"}
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

# --- OYLIK BERISH ---
class SalaryCalculateRequest(BaseModel):
    courier_id: int
    start_date: date
    end_date: date
    percentage: float 

class SalaryCalculationResponse(BaseModel):
    courier_id: int
    courier_name: str
    total_sales: float
    salary_amount: float
    orders_count: int
    start_date: date
    end_date: date
    percentage: float

class SalaryPaymentCreate(BaseModel):
    courier_id: int
    amount: float
    percentage: float
    start_date: date
    end_date: date

class SalaryPaymentRead(BaseModel):
    id: int
    courier_name: str
    amount: float
    percentage: float
    start_date: date
    end_date: date
    paid_at: datetime

    class Config:
        from_attributes = True

# --- CHIQIMLAR ---
class ExpenseCreate(BaseModel):
    amount: float
    note: str

class ExpenseRead(ExpenseCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- ANALITIKA (YANGILANGAN) ---

# Har bir mahsulot bo'yicha hisobot
class ProductPerformance(BaseModel):
    product_id: int
    product_name: str
    sold_quantity: int      # Nechta sotildi
    total_revenue: float    # Jami savdo (Sotish narxi * soni)
    total_cogs: float       # Jami tannarx (Olish narxi * soni)
    gross_profit: float     # Foyda (Revenue - COGS)
    margin_percent: float   # Foyda foizi

class ProfitStats(BaseModel):
    # Umumiy pul oqimi
    total_revenue: float 
    total_cogs: float    
    gross_profit: float  
    
    # Chiqimlar
    total_salaries: float 
    total_expenses: float 
    
    # Yakuniy natija
    net_profit: float    
    sold_items_count: int
    
    # Mahsulotlar kesimida
    products_breakdown: List[ProductPerformance]
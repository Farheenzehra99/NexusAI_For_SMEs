from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.business import (
    Business,
    Expense,
    DailySale,
    Product,
    Customer,
    MarketingCampaign,
    SupportTicket,
    AgentActivity,
)
from ..schemas.dashboard import (
    ExpenseSummary,
    ExpenseItem,
    DailySalesResponse,
    DailySaleItem,
    CustomerListResponse,
    CustomerItem,
    CampaignListResponse,
    CampaignItem,
    AgentActivityResponse,
    AgentActivityItem,
)

from .dependencies import get_current_business

router = APIRouter()


# ── Expenses ────────────────────────────────────────────────────────────────

@router.get("/expenses", response_model=ExpenseSummary)
async def get_expenses(
    month: Optional[str] = Query(None, description="Filter by month (e.g. 'Aug')"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    query = db.query(Expense).filter(Expense.business_id == business.id)
    if month:
        query = query.filter(Expense.month == month)

    expenses = query.all()
    total = sum(e.amount for e in expenses)

    return ExpenseSummary(
        total_monthly=total,
        categories=[
            ExpenseItem(
                category=e.category,
                description=e.description,
                amount=e.amount,
                year=e.year,
                month=e.month,
                is_recurring=bool(e.is_recurring),
            )
            for e in expenses
        ],
    )


# ── Daily Sales ─────────────────────────────────────────────────────────────

@router.get("/daily-sales", response_model=DailySalesResponse)
async def get_daily_sales(
    product_sku: Optional[str] = Query(None, description="Filter by product SKU"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    query = (
        db.query(DailySale, Product)
        .join(Product, DailySale.product_id == Product.id)
        .filter(DailySale.business_id == business.id)
    )
    if product_sku:
        query = query.filter(Product.sku == product_sku)

    rows = query.order_by(DailySale.date.desc()).all()

    items = []
    total_revenue = 0.0
    total_units = 0
    for ds, prod in rows:
        items.append(DailySaleItem(
            date=ds.date,
            product_name=prod.name,
            sku=prod.sku,
            qty_sold=ds.qty_sold,
            revenue=ds.revenue,
        ))
        total_revenue += ds.revenue
        total_units += ds.qty_sold

    return DailySalesResponse(
        days=items, total_revenue=total_revenue, total_units=total_units,
    )


# ── Customers ───────────────────────────────────────────────────────────────

@router.get("/customers", response_model=CustomerListResponse)
async def get_customers(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    customers = (
        db.query(Customer)
        .filter(Customer.business_id == business.id)
        .order_by(Customer.total_spent.desc())
        .all()
    )

    return CustomerListResponse(
        customers=[
            CustomerItem(
                name=c.name, phone=c.phone, email=c.email, city=c.city,
                total_orders=c.total_orders, total_spent=c.total_spent,
                last_order_date=c.last_order_date,
            )
            for c in customers
        ],
        total=len(customers),
    )


# ── Campaigns ───────────────────────────────────────────────────────────────

@router.get("/campaigns", response_model=CampaignListResponse)
async def get_campaigns(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    campaigns = (
        db.query(MarketingCampaign)
        .filter(MarketingCampaign.business_id == business.id)
        .all()
    )

    items = []
    total_spend = 0.0
    total_revenue = 0.0
    for c in campaigns:
        conv_rate = (c.conversions / c.clicks * 100) if c.clicks else 0
        cost_per = (c.spend / c.conversions) if c.conversions else 0
        roi = ((c.revenue_generated - c.spend) / c.spend * 100) if c.spend else 0
        items.append(CampaignItem(
            name=c.name, channel=c.channel,
            spend=c.spend, impressions=c.impressions,
            clicks=c.clicks, conversions=c.conversions,
            revenue_generated=c.revenue_generated, status=c.status,
            conversion_rate=round(conv_rate, 2),
            cost_per_conversion=round(cost_per, 2),
            roi_percent=round(roi, 1),
            start_date=c.start_date, end_date=c.end_date,
        ))
        total_spend += c.spend
        total_revenue += c.revenue_generated

    return CampaignListResponse(
        campaigns=items, total_spend=total_spend, total_revenue=total_revenue,
    )


# ── Support Tickets ─────────────────────────────────────────────────────────

@router.get("/support-tickets")
async def get_support_tickets(
    status: Optional[str] = Query(None),
    ticket_type: Optional[str] = Query(None),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    query = db.query(SupportTicket).filter(SupportTicket.business_id == business.id)
    if status:
        query = query.filter(SupportTicket.status == status)
    if ticket_type:
        query = query.filter(SupportTicket.ticket_type == ticket_type)

    tickets = query.order_by(SupportTicket.created_at.desc()).all()

    return {
        "tickets": [
            {
                "id": t.id,
                "customer_name": t.customer_name,
                "ticket_type": t.ticket_type,
                "status": t.status,
                "sentiment": t.sentiment,
                "description": t.description,
                "channel": t.channel,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
            }
            for t in tickets
        ],
        "total": len(tickets),
        "open_count": sum(1 for t in tickets if t.status == "open"),
        "complaint_count": sum(1 for t in tickets if t.ticket_type == "complaint"),
    }


# ── Agent Activities ────────────────────────────────────────────────────────

@router.get("/agent-activities", response_model=AgentActivityResponse)
async def get_agent_activities(
    agent_name: Optional[str] = Query(None),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    query = db.query(AgentActivity).filter(AgentActivity.business_id == business.id)
    if agent_name:
        query = query.filter(AgentActivity.agent_name == agent_name)

    activities = query.order_by(AgentActivity.created_at.desc()).all()

    return AgentActivityResponse(
        activities=[
            AgentActivityItem(
                agent_name=a.agent_name, action=a.action,
                finding=a.finding, data_points=a.data_points,
                created_at=a.created_at,
            )
            for a in activities
        ],
        total=len(activities),
    )

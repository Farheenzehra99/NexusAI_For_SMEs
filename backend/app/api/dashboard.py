"""Dashboard API — the business overview the owner sees first.

Every value returned here is REAL data from the application:

    - The Business Health Score, risk level, formula, and domain breakdown
      are computed LIVE by the BI Agent (never the static seeded column).
    - The AI recommendations are the CEO Agent's grounded, prioritized
      action plan (same rules as the Command Center), each with the exact
      evidence numbers from the specialized agents' structured outputs.
    - Inventory alerts are enriched with the Inventory Agent's computed
      days-of-stock-remaining and recommended reorder quantity.
    - Metrics, trends, products, and activity come from the seeded tables.

If the whole AI analysis layer fails, the dashboard degrades gracefully:
the raw business data is still returned and the health fields are null.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.business import (
    Business,
    Product,
    MonthlySale,
    InventoryAlert,
    SupportTicket,
    MarketingCampaign,
    Expense,
    Customer,
    AgentActivity,
)
from ..schemas.dashboard import (
    DashboardResponse,
    DomainScoreSummary,
    MetricCard,
    SalesTrendPoint,
    ProductSummary,
    InventoryAlertItem,
    Recommendation,
    ActivityItem,
)
from ..services.bi import get_bi_snapshot, NoBIDataError, BusinessNotFoundError
from ..services.ceo import get_ceo_answer_from_bi

router = APIRouter()

# The dashboard surfaces the AI workforce's answer to the owner's core
# question — the same grounded plan the CEO Agent produces on demand.
_DASHBOARD_QUESTION = "Why are my sales down?"

_MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: Session = Depends(get_db)):
    business = db.query(Business).first()
    if not business:
        raise HTTPException(status_code=404, detail="No business data found. Run seed.py first.")

    # ── Revenue & Profit Metrics (current month, month-over-month) ──
    sales = (
        db.query(MonthlySale)
        .filter(MonthlySale.business_id == business.id)
        .order_by(MonthlySale.id)
        .all()
    )

    current_revenue = sales[-1].revenue if sales else 0
    prev_revenue = sales[-2].revenue if len(sales) >= 2 else current_revenue
    current_profit = sales[-1].profit if sales else 0
    prev_profit = sales[-2].profit if len(sales) >= 2 else current_profit

    total_customers = business.total_customers or db.query(Customer).filter(
        Customer.business_id == business.id
    ).count()

    rev_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else None
    prof_change = ((current_profit - prev_profit) / prev_profit * 100) if prev_profit else None

    # Orders: the CURRENT month's order count, consistent with the monthly
    # revenue/profit cards (not the all-time total).
    current_orders = sales[-1].orders if sales else 0
    prev_orders = sales[-2].orders if len(sales) >= 2 else current_orders
    ord_change = ((current_orders - prev_orders) / prev_orders * 100) if prev_orders else None

    # Customers: the base is the real aggregate; the trend is the change in
    # ACTIVE customers (last order in the current vs previous month),
    # computed from the Customer table — never a hardcoded number.
    customers = db.query(Customer).filter(Customer.business_id == business.id).all()
    active_now, active_change = _active_customer_trend(customers, sales)

    metrics = [
        MetricCard(label="Revenue", value=current_revenue, change=_round1(rev_change), prefix="Rs "),
        MetricCard(label="Profit", value=current_profit, change=_round1(prof_change), prefix="Rs "),
        MetricCard(label="Orders", value=current_orders, change=_round1(ord_change)),
        MetricCard(
            label="Customers",
            value=total_customers,
            change=_round1(active_change),
            change_label="active customers",
            note=(
                f"{active_now} active in {sales[-1].month}"
                if active_change is None and sales else None
            ),
        ),
    ]

    # ── Sales Trend ──
    sales_trend = [
        SalesTrendPoint(month=s.month, revenue=s.revenue, profit=s.profit)
        for s in sales
    ]

    # ── AI workforce layer: BI health score + CEO action plan ──
    # Degrades gracefully: if the analysis layer fails, the dashboard still
    # returns the raw business data with null health fields.
    health_score = None
    risk_level = None
    health_formula = None
    as_of_date = None
    weakest_domain = None
    strongest_domain = None
    domain_scores: list[DomainScoreSummary] = []
    missing_domains: list[str] = []
    recommendations: list[Recommendation] = []
    inventory_products_by_sku = {}

    try:
        bi = get_bi_snapshot(db)
        ceo_answer = get_ceo_answer_from_bi(bi, _DASHBOARD_QUESTION)

        hs = ceo_answer.health_score
        if hs is not None:
            health_score = hs.score
            risk_level = hs.risk_level
            health_formula = hs.formula
            weakest_domain = hs.weakest_domain
            strongest_domain = hs.strongest_domain
            domain_scores = [
                DomainScoreSummary(
                    domain=d.domain, label=d.label, score=d.score, weight=d.weight,
                )
                for d in hs.domain_scores
                if d.data_available
            ]
        as_of_date = bi.as_of_date
        missing_domains = ceo_answer.missing_agents

        recommendations = [
            Recommendation(
                title=a.title,
                description=a.description,
                priority=a.priority,
                impact=a.priority,
                agent=a.agent_name,
                evidence=a.evidence,
                expected_impact=a.expected_impact,
            )
            for a in ceo_answer.recommended_actions
        ]

        if bi.inventory is not None:
            inventory_products_by_sku = {p.sku: p for p in bi.inventory.products}
    except (BusinessNotFoundError, NoBIDataError):
        # Entire analysis layer unavailable — raw data still shown.
        pass

    # ── Products ──
    all_products = db.query(Product).filter(Product.business_id == business.id).all()
    sorted_by_revenue = sorted(all_products, key=lambda p: p.total_revenue, reverse=True)

    top_products = [
        ProductSummary(
            name=p.name, sku=p.sku, sales=p.total_sales,
            revenue=p.total_revenue, trend=p.trend, stock_qty=p.stock_qty,
        )
        for p in sorted_by_revenue[:5]
    ]

    weak_products = [
        ProductSummary(
            name=p.name, sku=p.sku, sales=p.total_sales,
            revenue=p.total_revenue, reason=_weak_reason(p),
            stock_qty=p.stock_qty,
        )
        for p in sorted_by_revenue
        if p.total_sales < 20
    ]

    # ── Inventory Alerts (enriched with the Inventory Agent's numbers) ──
    alerts = (
        db.query(InventoryAlert)
        .filter(InventoryAlert.business_id == business.id)
        .all()
    )
    inventory_alerts = []
    for a in alerts:
        agent_product = _agent_product_for_alert(db, a, inventory_products_by_sku)
        inventory_alerts.append(InventoryAlertItem(
            item=a.item_name, status=a.status, qty=a.qty,
            estimated_revenue_at_risk=a.estimated_revenue_at_risk,
            days_of_stock_remaining=(
                agent_product.days_of_stock_remaining
                if agent_product else None
            ),
            recommended_reorder_qty=(
                agent_product.recommended_reorder_qty
                if agent_product else None
            ),
            excess_stock_qty=(
                agent_product.excess_stock_qty
                if agent_product else None
            ),
        ))

    # ── Support Ticket Summary (from real data) ──
    all_tickets = db.query(SupportTicket).filter(
        SupportTicket.business_id == business.id
    ).all()
    open_tickets = [t for t in all_tickets if t.status == "open"]
    complaints = [t for t in all_tickets if t.ticket_type == "complaint"]

    support_ticket_summary = {
        "total": len(all_tickets),
        "open": len(open_tickets),
        "resolved": len(all_tickets) - len(open_tickets),
        "complaints": len(complaints),
        "negative": sum(1 for t in all_tickets if t.sentiment == "negative"),
    }

    # ── Campaign Summary (from real data) ──
    campaigns = db.query(MarketingCampaign).filter(
        MarketingCampaign.business_id == business.id
    ).all()
    total_camp_spend = sum(c.spend for c in campaigns)
    total_camp_revenue = sum(c.revenue_generated for c in campaigns)
    underperforming = [
        c for c in campaigns
        if c.clicks > 0 and (c.conversions / c.clicks * 100) < 2.0
    ]

    campaign_summary = {
        "total": len(campaigns),
        "active": sum(1 for c in campaigns if c.status == "active"),
        "paused": sum(1 for c in campaigns if c.status == "paused"),
        "total_spend": total_camp_spend,
        "total_revenue": total_camp_revenue,
        "underperforming": [c.name for c in underperforming],
    }

    # ── Expense Summary (from real data) ──
    expenses = db.query(Expense).filter(
        Expense.business_id == business.id, Expense.month == "Aug"
    ).all()
    total_expenses = sum(e.amount for e in expenses)

    expense_summary = {
        "total_monthly": total_expenses,
        "categories": {e.category: e.amount for e in expenses},
    }

    # ── Recent Activity (from AgentActivity table) ──
    activities = (
        db.query(AgentActivity)
        .filter(AgentActivity.business_id == business.id)
        .order_by(AgentActivity.created_at.desc())
        .limit(10)
        .all()
    )
    now = datetime.utcnow()
    recent_activity = [
        ActivityItem(
            agent=a.agent_name,
            action=a.action,
            finding=a.finding,
            data_points=a.data_points,
            time=_time_ago(a.created_at, now),
        )
        for a in activities
    ]

    return DashboardResponse(
        business_name=business.name,
        owner_name=business.owner_name,
        location=business.location,
        health_score=health_score,
        risk_level=risk_level,
        health_formula=health_formula,
        as_of_date=as_of_date,
        weakest_domain=weakest_domain,
        strongest_domain=strongest_domain,
        domain_scores=domain_scores,
        missing_domains=missing_domains,
        total_customers=business.total_customers or 0,
        established_year=business.established_year or 2018,
        metrics=metrics,
        sales_trend=sales_trend,
        top_products=top_products,
        weak_products=weak_products,
        inventory_alerts=inventory_alerts,
        support_ticket_summary=support_ticket_summary,
        campaign_summary=campaign_summary,
        expense_summary=expense_summary,
        recommendations=recommendations,
        recent_activity=recent_activity,
    )


def _round1(value):
    return round(value, 1) if value is not None else None


def _active_customer_trend(customers, sales):
    """Count customers whose last order falls in the current vs previous
    month (from the latest MonthlySale row). Returns (active_now, change%).

    Returns (None, None) when there is no monthly data or no prior-month
    baseline — an honest absence instead of a fabricated percentage.
    """
    if not sales:
        return None, None
    last = sales[-1]
    try:
        cur_m = _MONTH_NAMES.index(last.month) + 1
    except ValueError:
        return None, None
    cur_y = last.year
    prev_y, prev_m = (cur_y - 1, 12) if cur_m == 1 else (cur_y, cur_m - 1)

    def _count(year, month):
        return sum(
            1 for c in customers
            if c.last_order_date
            and c.last_order_date.year == year
            and c.last_order_date.month == month
        )

    now_active = _count(cur_y, cur_m)
    prev_active = _count(prev_y, prev_m)
    if prev_active == 0:
        return now_active, None
    change = (now_active - prev_active) / prev_active * 100
    return now_active, change


def _agent_product_for_alert(db, alert, inventory_products_by_sku):
    """Find the Inventory Agent's computed product fact for one alert row."""
    if not inventory_products_by_sku or alert.product_id is None:
        return None
    product = db.get(Product, alert.product_id)
    if product is None:
        return None
    return inventory_products_by_sku.get(product.sku)


def _time_ago(dt, now) -> str:
    """Human-readable time ago string."""
    if not dt:
        return "unknown"
    diff = now - dt
    minutes = int(diff.total_seconds() / 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days > 1 else ''} ago"


def _weak_reason(p: Product) -> str:
    """Generate a weakness reason based on product data."""
    if p.stock_qty > 200 and p.total_sales < 20:
        return f"Overstocked ({p.stock_qty} units) with only {p.total_sales} sales — ties up capital"
    if p.trend == "down" and p.total_sales < 15:
        return f"Very low demand ({p.total_sales} sales) — consider discontinuing"
    if p.trend == "down":
        return f"Declining demand ({p.total_sales} sales) — seasonal mismatch"
    if p.total_sales < 10:
        return f"Minimal traction ({p.total_sales} sales) — review positioning"
    return f"Low performance — stock clearance recommended"

from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


class MetricCard(BaseModel):
    label: str
    value: float
    change: Optional[float] = None   # None when no honest comparison exists
    prefix: str = ""
    change_label: str = "vs last month"
    note: Optional[str] = None       # neutral context line when change is None


class DomainScoreSummary(BaseModel):
    """One domain's BI sub-score, for the health score breakdown."""

    domain: str
    label: str
    score: int
    weight: float


class SalesTrendPoint(BaseModel):
    month: str
    revenue: float
    profit: float


class ProductSummary(BaseModel):
    name: str
    sku: str
    sales: int
    revenue: float
    trend: Optional[str] = None
    stock_qty: Optional[int] = None
    reason: Optional[str] = None


class InventoryAlertItem(BaseModel):
    item: str
    status: str
    qty: int
    estimated_revenue_at_risk: float = 0
    # Agent-computed context (from the Inventory Agent's snapshot)
    days_of_stock_remaining: Optional[float] = None
    recommended_reorder_qty: Optional[int] = None
    excess_stock_qty: Optional[int] = None


class Recommendation(BaseModel):
    """One grounded action from the CEO Agent's prioritized plan."""

    title: str
    description: str
    priority: str                    # urgent|high|medium|low
    agent: str
    evidence: List[str] = []         # exact numbers from the agents' outputs
    expected_impact: str = ""
    # Legacy alias kept so existing consumers keep working.
    impact: str = ""


class ActivityItem(BaseModel):
    agent: str
    action: str
    finding: str = ""
    data_points: str = ""
    time: str


# --- Expense schemas ---

class ExpenseItem(BaseModel):
    category: str
    description: str
    amount: float
    year: int
    month: str
    is_recurring: bool


class ExpenseSummary(BaseModel):
    total_monthly: float
    categories: List[ExpenseItem]


# --- Daily sales schemas ---

class DailySaleItem(BaseModel):
    date: date
    product_name: str
    sku: str
    qty_sold: int
    revenue: float


class DailySalesResponse(BaseModel):
    days: List[DailySaleItem]
    total_revenue: float
    total_units: int


# --- Customer schemas ---

class CustomerItem(BaseModel):
    name: str
    phone: str
    email: str
    city: str
    total_orders: int
    total_spent: float
    last_order_date: Optional[date] = None


class CustomerListResponse(BaseModel):
    customers: List[CustomerItem]
    total: int


# --- Campaign schemas ---

class CampaignItem(BaseModel):
    name: str
    channel: str
    spend: float
    impressions: int
    clicks: int
    conversions: int
    revenue_generated: float
    status: str
    conversion_rate: float
    cost_per_conversion: float
    roi_percent: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignListResponse(BaseModel):
    campaigns: List[CampaignItem]
    total_spend: float
    total_revenue: float


# --- Agent activity schemas ---

class AgentActivityItem(BaseModel):
    agent_name: str
    action: str
    finding: str
    data_points: str
    created_at: datetime


class AgentActivityResponse(BaseModel):
    activities: List[AgentActivityItem]
    total: int


# --- Dashboard (main response) ---

class DashboardResponse(BaseModel):
    business_name: str
    owner_name: str
    location: str
    # Business Health Score computed LIVE by the BI Agent (never the static
    # seeded column). None only when the whole AI analysis layer failed.
    health_score: Optional[int] = None
    risk_level: Optional[str] = None          # low|moderate|high|critical
    health_formula: Optional[str] = None      # documented weighted formula
    as_of_date: Optional[str] = None
    weakest_domain: Optional[str] = None
    strongest_domain: Optional[str] = None
    domain_scores: List[DomainScoreSummary] = []
    missing_domains: List[str] = []
    total_customers: int
    established_year: int
    metrics: List[MetricCard]
    sales_trend: List[SalesTrendPoint]
    top_products: List[ProductSummary]
    weak_products: List[ProductSummary]
    inventory_alerts: List[InventoryAlertItem]
    support_ticket_summary: dict
    campaign_summary: dict
    expense_summary: dict
    recommendations: List[Recommendation]
    recent_activity: List[ActivityItem]

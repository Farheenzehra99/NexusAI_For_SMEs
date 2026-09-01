"""
Finance Agent schemas — structured financial facts.

Design rule: every numeric field here is computed by deterministic code
(app/services/finance.py) from database records. The LLM never produces
these numbers — it only receives them and may explain them in plain
language. This keeps the Finance Agent's facts auditable and testable.
"""

from pydantic import BaseModel
from typing import List, Optional


class MonthlyPoint(BaseModel):
    """One month of financial performance."""
    month: str            # e.g. "Aug"
    year: int
    revenue: float
    profit: float
    expenses: float       # operating expenses tracked in the expenses table
    margin_percent: float


class RevenueFacts(BaseModel):
    current_month: str
    current_revenue: float
    previous_month: Optional[str]
    previous_revenue: float
    change_percent: Optional[float]     # MoM change, None if no prior month
    peak_month: str
    peak_revenue: float
    decline_from_peak_percent: float    # negative when below peak
    series: List[MonthlyPoint]
    trend: str                          # "declining" | "stable" | "growing"


class ExpenseCategoryFact(BaseModel):
    category: str
    amount: float
    share_percent: float                # share of the month's total expenses


class ExpenseFacts(BaseModel):
    month: str
    total: float
    previous_total: float
    change_percent: Optional[float]
    top_category: str
    top_category_amount: float
    categories: List[ExpenseCategoryFact]


class ProfitFacts(BaseModel):
    current_month: str
    current_profit: float
    previous_profit: float
    change_percent: Optional[float]
    current_margin_percent: float
    peak_margin_percent: float
    peak_margin_month: str
    margin_compression_pp: float        # peak margin - current margin (positive = compressed)


class ProductRevenueFact(BaseModel):
    name: str
    sku: str
    revenue: float
    units_sold: int
    revenue_share_percent: float        # share of total product revenue


class WeakProductFact(BaseModel):
    name: str
    sku: str
    revenue: float
    units_sold: int
    stock_qty: int
    reason: str


class UnusualChangeFact(BaseModel):
    """An anomaly detected by deterministic rules (never by the LLM)."""
    type: str               # e.g. "revenue_decline_from_peak"
    severity: str           # "high" | "medium" | "low"
    description: str        # states the exact computed numbers involved
    metrics: dict           # machine-readable facts backing the description


class FinanceFacts(BaseModel):
    """Complete, deterministic financial picture. Suitable for the
    dashboard and for consumption by the CEO Agent."""
    business_name: str
    currency: str
    months_analyzed: int
    revenue: RevenueFacts
    expenses: ExpenseFacts
    profit: ProfitFacts
    top_revenue_products: List[ProductRevenueFact]
    weak_products: List[WeakProductFact]
    unusual_changes: List[UnusualChangeFact]


class FinanceAnalysisResponse(BaseModel):
    """Full Finance Agent response: verified facts + plain-language
    interpretation (LLM or deterministic fallback)."""
    agent: str
    facts: FinanceFacts
    interpretation: str
    interpretation_source: str      # "llm" | "fallback"
    generated_at: str

"""
Inventory Agent schemas — structured stock facts.

Design rule (same as the Finance Agent): every numeric field here is
computed by deterministic code (app/services/inventory.py) from database
records — current stock from the products table, sales velocity from the
daily_sales table. The LLM never produces stock numbers; it only receives
these facts and may explain them in plain language.
"""

from pydantic import BaseModel
from typing import List, Optional


class ProductInventoryFact(BaseModel):
    """Inventory position for one product."""
    name: str
    sku: str
    category: str
    price: float
    cost: float
    current_stock: int
    reorder_threshold: int
    below_reorder_level: bool
    velocity_units_per_day: float
    velocity_units_per_week: float
    days_of_stock_remaining: Optional[float]    # None when velocity is zero
    risk_level: str          # critical|high|medium|adequate|overstock|stagnant|out_of_stock
    recommended_reorder_qty: int                # 0 when no reorder is needed
    excess_stock_qty: int                       # units beyond 180-day supply (overstock only)
    stock_value_retail: float                   # current_stock * price


class InventoryRiskItem(BaseModel):
    """A flagged risk, sorted by severity — suitable for the dashboard
    and for consumption by the CEO Agent."""
    sku: str
    product: str
    risk_level: str
    days_of_stock_remaining: Optional[float] = None
    recommended_reorder_qty: int = 0
    excess_stock_qty: int = 0
    reason: str               # deterministic sentence quoting computed numbers


class InventorySummary(BaseModel):
    total_active_products: int
    at_risk_count: int        # critical + high + medium + out_of_stock
    critical_count: int
    overstock_count: int
    stagnant_count: int
    total_stock_value_retail: float
    recommended_reorder_units: int
    recommended_reorder_cost: float
    excess_stock_value_retail: float


class InventoryFacts(BaseModel):
    """Complete, deterministic inventory picture."""
    business_name: str
    currency: str
    as_of_date: str                       # latest date present in daily_sales
    velocity_window_days: int             # actual window used for velocity
    summary: InventorySummary
    products: List[ProductInventoryFact]  # sorted by risk severity
    risks: List[InventoryRiskItem]        # every non-adequate product


class InventoryAnalysisResponse(BaseModel):
    """Full Inventory Agent response: verified facts + plain-language
    interpretation (LLM or deterministic fallback)."""
    agent: str
    facts: InventoryFacts
    interpretation: str
    interpretation_source: str      # "llm" | "fallback"
    generated_at: str

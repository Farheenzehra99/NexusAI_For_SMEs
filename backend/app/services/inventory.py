"""
Deterministic inventory analysis service.

ARCHITECTURE RULE
-----------------
Every inventory number the Inventory Agent reports is computed HERE, in
plain Python, from database records:
    - current stock          → products.stock_qty
    - sales velocity         → SUM(daily_sales.qty_sold) over the window
    - days of stock remaining → stock_qty / velocity
    - stock-out risk         → rule-based classification on days remaining
    - reorder quantity       → ceil(velocity * TARGET_COVERAGE_DAYS) - stock

The LLM layer is strictly forbidden from calculating or inventing stock
numbers — it only receives the InventoryFacts produced by this module and
may rephrase them in plain language.
"""

import math
from datetime import timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.business import Business, Product, DailySale
from ..schemas.inventory import (
    InventoryFacts,
    InventorySummary,
    ProductInventoryFact,
    InventoryRiskItem,
)

# ── Deterministic thresholds (tunable constants, no LLM involvement) ────────

CRITICAL_DAYS = 7          # stock-out within a week → critical
HIGH_DAYS = 14             # stock-out within two weeks → high
MEDIUM_DAYS = 30           # stock-out within a month → medium
OVERSTOCK_DAYS = 180       # more than ~6 months of supply → overstock
TARGET_COVERAGE_DAYS = 60  # reorder recommendation covers this many days

MIN_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 90

# Sort order for presenting risks (most urgent first)
RISK_ORDER = {
    "out_of_stock": 0,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "overstock": 4,
    "stagnant": 5,
    "adequate": 6,
}

AT_RISK_LEVELS = {"out_of_stock", "critical", "high", "medium"}
RISK_LEVELS = {"out_of_stock", "critical", "high", "medium", "overstock", "stagnant"}


class InventoryDataError(Exception):
    """Raised when the request cannot be served (bad range, missing data)."""


class BusinessNotFoundError(InventoryDataError):
    pass


class InvalidRangeError(InventoryDataError):
    pass


class NoSalesDataError(InventoryDataError):
    pass


def get_inventory_snapshot(db: Session, days: int = 30, business_id: int | None = None) -> InventoryFacts:
    """Build the complete deterministic inventory picture.

    Args:
        db: database session.
        days: requested velocity window (7-90 calendar days).
        business_id: scope to this business (required for multi-tenancy).

    Raises:
        InvalidRangeError: days outside [MIN_WINDOW_DAYS, MAX_WINDOW_DAYS].
        BusinessNotFoundError: no business record in the database.
        NoSalesDataError: no daily sales rows exist to derive velocity.
    """
    if not (MIN_WINDOW_DAYS <= days <= MAX_WINDOW_DAYS):
        raise InvalidRangeError(
            f"days must be between {MIN_WINDOW_DAYS} and {MAX_WINDOW_DAYS}, got {days}"
        )

    if business_id is not None:
        business = db.get(Business, business_id)
    else:
        business = db.query(Business).first()
    if not business:
        raise BusinessNotFoundError("No business found. Run seed.py first.")

    # ── Determine the velocity window from actual data ──
    first_row = (
        db.query(DailySale.date)
        .filter(DailySale.business_id == business.id)
        .order_by(DailySale.date.asc())
        .first()
    )
    last_row = (
        db.query(DailySale.date)
        .filter(DailySale.business_id == business.id)
        .order_by(DailySale.date.desc())
        .first()
    )
    if not first_row or not last_row:
        raise NoSalesDataError(
            "No daily sales data available. Velocity cannot be computed. Run seed.py first."
        )

    as_of = last_row[0]
    data_span = (as_of - first_row[0]).days + 1
    effective_days = min(days, data_span)
    cutoff = as_of - timedelta(days=effective_days - 1)

    # ── Units sold per product within the window (single grouped query) ──
    rows = (
        db.query(
            DailySale.product_id,
            func.sum(DailySale.qty_sold).label("units"),
        )
        .filter(
            DailySale.business_id == business.id,
            DailySale.date >= cutoff,
            DailySale.date <= as_of,
        )
        .group_by(DailySale.product_id)
        .all()
    )
    units_in_window = {product_id: int(units or 0) for product_id, units in rows}

    # ── Per-product facts ──
    products = (
        db.query(Product)
        .filter(Product.business_id == business.id, Product.is_active == 1)
        .all()
    )

    product_facts: list[ProductInventoryFact] = []
    for p in products:
        stock = int(p.stock_qty or 0)
        threshold = int(p.reorder_threshold or 0)
        price = float(p.price or 0)
        cost = float(p.cost or 0)

        sold = units_in_window.get(p.id, 0)
        # Round velocity once and use this single value for every derived
        # metric (days of cover, reorder qty, excess) so all exposed facts
        # are mutually consistent for downstream consumers (CEO Agent).
        velocity = round(sold / effective_days, 4)

        days_remaining: Optional[float] = None
        if velocity > 0:
            days_remaining = round(stock / velocity, 2)

        risk, reorder_qty, excess_qty = _classify(
            stock=stock, velocity=velocity, days_remaining=days_remaining
        )

        product_facts.append(ProductInventoryFact(
            name=p.name,
            sku=p.sku,
            category=p.category or "",
            price=price,
            cost=cost,
            current_stock=stock,
            reorder_threshold=threshold,
            below_reorder_level=stock <= threshold,
            velocity_units_per_day=velocity,
            velocity_units_per_week=round(velocity * 7, 2),
            days_of_stock_remaining=days_remaining,
            risk_level=risk,
            recommended_reorder_qty=reorder_qty,
            excess_stock_qty=excess_qty,
            stock_value_retail=round(stock * price, 2),
        ))

    # Most urgent risks first; ties broken by fewer days of cover
    product_facts.sort(
        key=lambda f: (
            RISK_ORDER.get(f.risk_level, 99),
            f.days_of_stock_remaining if f.days_of_stock_remaining is not None else 10**9,
        )
    )

    # ── Risk list with deterministic reasons ──
    risks = [
        InventoryRiskItem(
            sku=f.sku,
            product=f.name,
            risk_level=f.risk_level,
            days_of_stock_remaining=f.days_of_stock_remaining,
            recommended_reorder_qty=f.recommended_reorder_qty,
            excess_stock_qty=f.excess_stock_qty,
            reason=_risk_reason(f),
        )
        for f in product_facts
        if f.risk_level in RISK_LEVELS
    ]

    # ── Summary aggregates ──
    summary = InventorySummary(
        total_active_products=len(product_facts),
        at_risk_count=sum(1 for f in product_facts if f.risk_level in AT_RISK_LEVELS),
        critical_count=sum(1 for f in product_facts if f.risk_level == "critical"),
        overstock_count=sum(1 for f in product_facts if f.risk_level == "overstock"),
        stagnant_count=sum(1 for f in product_facts if f.risk_level == "stagnant"),
        total_stock_value_retail=round(
            sum(f.stock_value_retail for f in product_facts), 2
        ),
        recommended_reorder_units=sum(f.recommended_reorder_qty for f in product_facts),
        recommended_reorder_cost=round(
            sum(f.recommended_reorder_qty * f.cost for f in product_facts), 2
        ),
        excess_stock_value_retail=round(
            sum(f.excess_stock_qty * f.price for f in product_facts), 2
        ),
    )

    return InventoryFacts(
        business_name=business.name,
        currency=business.currency or "PKR",
        as_of_date=as_of.isoformat(),
        velocity_window_days=effective_days,
        summary=summary,
        products=product_facts,
        risks=risks,
    )


# ── Deterministic classification and recommendation rules ───────────────────

def _classify(
    *, stock: int, velocity: float, days_remaining: Optional[float]
) -> tuple[str, int, int]:
    """Return (risk_level, recommended_reorder_qty, excess_stock_qty)."""
    if stock == 0:
        if velocity > 0:
            # Selling but nothing on the shelf — restock to full coverage.
            return "out_of_stock", math.ceil(velocity * TARGET_COVERAGE_DAYS), 0
        return "stagnant", 0, 0

    if velocity <= 0:
        # Stock on hand but zero sales in the window — dead stock.
        return "stagnant", 0, stock

    # velocity > 0 and stock > 0 → days_remaining is set
    if days_remaining <= CRITICAL_DAYS:
        return "critical", _reorder_qty(stock, velocity), 0
    if days_remaining <= HIGH_DAYS:
        return "high", _reorder_qty(stock, velocity), 0
    if days_remaining <= MEDIUM_DAYS:
        return "medium", _reorder_qty(stock, velocity), 0
    if days_remaining > OVERSTOCK_DAYS:
        excess = stock - math.ceil(velocity * OVERSTOCK_DAYS)
        return "overstock", 0, max(excess, 0)
    return "adequate", 0, 0


def _reorder_qty(stock: int, velocity: float) -> int:
    """Units needed to reach TARGET_COVERAGE_DAYS of supply (never negative)."""
    return max(math.ceil(velocity * TARGET_COVERAGE_DAYS) - stock, 0)


def _risk_reason(f: ProductInventoryFact) -> str:
    """Deterministic explanation quoting only computed numbers."""
    week = f.velocity_units_per_week
    if f.risk_level == "out_of_stock":
        return (
            f"Out of stock while still selling {week:.1f} units/week — "
            f"reorder {f.recommended_reorder_qty} units to restore "
            f"{TARGET_COVERAGE_DAYS} days of cover."
        )
    if f.risk_level == "critical":
        return (
            f"Only {f.current_stock} units in stock with sales velocity of "
            f"{week:.1f} units/week — about {f.days_of_stock_remaining:.1f} days "
            f"of cover remaining (reorder level: {f.reorder_threshold} units)."
        )
    if f.risk_level == "high":
        return (
            f"{f.current_stock} units in stock with sales velocity of "
            f"{week:.1f} units/week — about {f.days_of_stock_remaining:.1f} days "
            f"of cover remaining (reorder level: {f.reorder_threshold} units)."
        )
    if f.risk_level == "medium":
        return (
            f"{f.current_stock} units in stock with sales velocity of "
            f"{week:.1f} units/week — roughly {f.days_of_stock_remaining:.0f} days "
            f"of cover remaining."
        )
    if f.risk_level == "overstock":
        return (
            f"{f.current_stock} units in stock against {week:.1f} units/week "
            f"velocity — about {f.days_of_stock_remaining:.0f} days of supply. "
            f"{f.excess_stock_qty} units worth Rs "
            f"{f.excess_stock_qty * f.price:,.0f} retail sit beyond the "
            f"{OVERSTOCK_DAYS}-day horizon."
        )
    if f.risk_level == "stagnant":
        return (
            f"{f.current_stock} units in stock with no sales in the recent "
            f"window — dead stock tying up Rs "
            f"{f.stock_value_retail:,.0f} in retail value."
        )
    return "Stock levels are adequate."

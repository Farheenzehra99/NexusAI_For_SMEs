"""
Deterministic financial analysis service.

ARCHITECTURE RULE
-----------------
Every financial number the Finance Agent reports is computed HERE, in
plain Python, from database records. The LLM layer is strictly forbidden
from calculating or inventing numbers — it only receives the FinanceFacts
produced by this module and may rephrase them in plain language.

This makes every figure auditable and unit-testable against seed data.
"""

from sqlalchemy.orm import Session

from ..models.business import (
    Business,
    Product,
    MonthlySale,
    Expense,
)
from ..schemas.finance import (
    FinanceFacts,
    RevenueFacts,
    ExpenseFacts,
    ExpenseCategoryFact,
    ProfitFacts,
    ProductRevenueFact,
    WeakProductFact,
    UnusualChangeFact,
    MonthlyPoint,
)

MONTH_ORDER = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# Thresholds for anomaly detection (deterministic rules, tunable)
REVENUE_DECLINE_HIGH = 10.0       # % decline from peak → high severity
REVENUE_DECLINE_MEDIUM = 5.0      # % decline from peak → medium severity
MARGIN_COMPRESSION_HIGH = 4.0     # percentage points → high severity
MARGIN_COMPRESSION_MEDIUM = 2.0   # percentage points → medium severity
CONSECUTIVE_DECLINES_FLAG = 3     # consecutive MoM declines to flag
EXPENSE_SPIKE_PERCENT = 15.0      # % MoM increase in a category → flag
PROFIT_DROP_HIGH = 10.0           # % MoM profit drop → high severity

MIN_MONTHS = 1
MAX_MONTHS = 12
WEAK_PRODUCT_UNITS = 20           # products below this unit count are "weak"


class FinanceDataError(Exception):
    """Raised when the request cannot be served (bad range, no business)."""


class BusinessNotFoundError(FinanceDataError):
    pass


class InvalidRangeError(FinanceDataError):
    pass


def _pct_change(current: float, previous: float):
    """Percent change; None when previous is zero/absent."""
    if previous in (0, None):
        return None
    return round((current - previous) / previous * 100, 2)


def _sort_key(m: MonthlySale):
    return (m.year, MONTH_ORDER.get(m.month, 0))


def get_financial_snapshot(db: Session, months: int = 6, business_id: int | None = None) -> FinanceFacts:
    """Build the complete deterministic financial picture.

    Raises:
        InvalidRangeError: months outside [1, 12].
        BusinessNotFoundError: no business record in the database.
    """
    if not (MIN_MONTHS <= months <= MAX_MONTHS):
        raise InvalidRangeError(
            f"months must be between {MIN_MONTHS} and {MAX_MONTHS}, got {months}"
        )

    if business_id is not None:
        business = db.get(Business, business_id)
    else:
        business = db.query(Business).first()
    if not business:
        raise BusinessNotFoundError("No business found. Run seed.py first.")

    # ── Load and order monthly data ──
    all_sales = (
        db.query(MonthlySale)
        .filter(MonthlySale.business_id == business.id)
        .all()
    )
    all_sales.sort(key=_sort_key)
    window = all_sales[-months:] if months < len(all_sales) else all_sales

    if not window:
        raise FinanceDataError("No monthly sales data available for this business.")

    all_expenses = (
        db.query(Expense)
        .filter(Expense.business_id == business.id)
        .all()
    )
    expenses_by_month: dict = {}
    for e in all_expenses:
        key = (e.year, MONTH_ORDER.get(e.month, 0), e.month)
        expenses_by_month.setdefault(key, []).append(e)

    def _month_total(year: int, month: str) -> float:
        key = (year, MONTH_ORDER.get(month, 0), month)
        return sum(e.amount for e in expenses_by_month.get(key, []))

    # ── Build monthly series ──
    series: list[MonthlyPoint] = []
    for s in window:
        expenses_total = _month_total(s.year, s.month)
        margin = (s.profit / s.revenue * 100) if s.revenue else 0.0
        series.append(MonthlyPoint(
            month=s.month, year=s.year, revenue=s.revenue,
            profit=s.profit, expenses=expenses_total,
            margin_percent=round(margin, 2),
        ))

    current = series[-1]
    previous = series[-2] if len(series) >= 2 else None

    # ── Revenue facts ──
    peak = max(series, key=lambda p: p.revenue)
    decline_from_peak = round(
        (current.revenue - peak.revenue) / peak.revenue * 100, 2
    ) if peak.revenue else 0.0

    revenue_change = _pct_change(current.revenue, previous.revenue) if previous else None

    trend = "stable"
    if decline_from_peak <= -REVENUE_DECLINE_MEDIUM:
        trend = "declining"
    elif decline_from_peak >= REVENUE_DECLINE_MEDIUM:
        trend = "growing"

    revenue_facts = RevenueFacts(
        current_month=current.month,
        current_revenue=current.revenue,
        previous_month=previous.month if previous else None,
        previous_revenue=previous.revenue if previous else 0.0,
        change_percent=revenue_change,
        peak_month=peak.month,
        peak_revenue=peak.revenue,
        decline_from_peak_percent=decline_from_peak,
        series=series,
        trend=trend,
    )

    # ── Expense facts (current vs previous month) ──
    current_exp_rows = expenses_by_month.get(
        (current.year, MONTH_ORDER.get(current.month, 0), current.month), []
    )
    current_expenses_total = sum(e.amount for e in current_exp_rows)
    previous_expenses_total = (
        _month_total(previous.year, previous.month) if previous else 0.0
    )
    expense_change = (
        _pct_change(current_expenses_total, previous_expenses_total)
        if previous and previous_expenses_total else None
    )

    category_rows = sorted(current_exp_rows, key=lambda e: e.amount, reverse=True)
    category_facts = []
    for e in category_rows:
        share = (e.amount / current_expenses_total * 100) if current_expenses_total else 0.0
        category_facts.append(ExpenseCategoryFact(
            category=e.category, amount=e.amount, share_percent=round(share, 2),
        ))

    expense_facts = ExpenseFacts(
        month=current.month,
        total=current_expenses_total,
        previous_total=previous_expenses_total,
        change_percent=expense_change,
        top_category=category_rows[0].category if category_rows else "n/a",
        top_category_amount=category_rows[0].amount if category_rows else 0.0,
        categories=category_facts,
    )

    # ── Profit facts ──
    peak_margin_point = max(series, key=lambda p: p.margin_percent)
    profit_change = _pct_change(current.profit, previous.profit) if previous else None
    margin_compression = round(
        peak_margin_point.margin_percent - current.margin_percent, 2
    )

    profit_facts = ProfitFacts(
        current_month=current.month,
        current_profit=current.profit,
        previous_profit=previous.profit if previous else 0.0,
        change_percent=profit_change,
        current_margin_percent=current.margin_percent,
        peak_margin_percent=peak_margin_point.margin_percent,
        peak_margin_month=peak_margin_point.month,
        margin_compression_pp=margin_compression,
    )

    # ── Product revenue facts ──
    products = (
        db.query(Product)
        .filter(Product.business_id == business.id, Product.is_active == 1)
        .all()
    )
    total_product_revenue = sum(p.total_revenue for p in products)
    sorted_products = sorted(products, key=lambda p: p.total_revenue, reverse=True)

    top_products = [
        ProductRevenueFact(
            name=p.name, sku=p.sku, revenue=p.total_revenue,
            units_sold=p.total_sales,
            revenue_share_percent=round(
                p.total_revenue / total_product_revenue * 100, 2
            ) if total_product_revenue else 0.0,
        )
        for p in sorted_products[:5]
    ]

    weak_products = [
        WeakProductFact(
            name=p.name, sku=p.sku, revenue=p.total_revenue,
            units_sold=p.total_sales, stock_qty=p.stock_qty,
            reason=(
                f"Only {p.total_sales} units sold against {p.stock_qty} in stock — "
                f"capital tied up in slow-moving inventory"
                if p.stock_qty > p.total_sales * 2
                else f"Only {p.total_sales} units sold — consistently weak demand"
            ),
        )
        for p in sorted_products
        if p.total_sales < WEAK_PRODUCT_UNITS
    ]

    # ── Unusual changes (deterministic anomaly rules) ──
    unusual: list[UnusualChangeFact] = []

    # Rule 1: revenue decline from peak
    if decline_from_peak <= -REVENUE_DECLINE_HIGH:
        unusual.append(UnusualChangeFact(
            type="revenue_decline_from_peak",
            severity="high",
            description=(
                f"Revenue in {current.month} (Rs {current.revenue:,.0f}) is "
                f"{abs(decline_from_peak):.1f}% below the {peak.month} peak of "
                f"Rs {peak.revenue:,.0f}."
            ),
            metrics={
                "current_revenue": current.revenue,
                "peak_revenue": peak.revenue,
                "peak_month": peak.month,
                "decline_percent": decline_from_peak,
            },
        ))
    elif decline_from_peak <= -REVENUE_DECLINE_MEDIUM:
        unusual.append(UnusualChangeFact(
            type="revenue_decline_from_peak",
            severity="medium",
            description=(
                f"Revenue in {current.month} is {abs(decline_from_peak):.1f}% "
                f"below the {peak.month} peak."
            ),
            metrics={
                "current_revenue": current.revenue,
                "peak_revenue": peak.revenue,
                "decline_percent": decline_from_peak,
            },
        ))

    # Rule 2: longest run of consecutive month-over-month declines in the window
    best_run, best_end = 0, -1
    run = 0
    for i in range(1, len(series)):
        if series[i].revenue < series[i - 1].revenue:
            run += 1
            if run > best_run:
                best_run, best_end = run, i
        else:
            run = 0
    if best_run >= CONSECUTIVE_DECLINES_FLAG:
        start_m = series[best_end - best_run + 1].month
        end_m = series[best_end].month
        unusual.append(UnusualChangeFact(
            type="consecutive_monthly_declines",
            severity="medium" if best_run < 4 else "high",
            description=(
                f"{best_run} consecutive month-over-month revenue declines "
                f"from {start_m} to {end_m}."
            ),
            metrics={
                "consecutive_declines": best_run,
                "start_month": start_m,
                "end_month": end_m,
            },
        ))

    # Rule 3: margin compression from peak
    if margin_compression >= MARGIN_COMPRESSION_HIGH:
        unusual.append(UnusualChangeFact(
            type="margin_compression",
            severity="high",
            description=(
                f"Profit margin fell from {peak_margin_point.margin_percent:.1f}% in "
                f"{peak_margin_point.month} to {current.margin_percent:.1f}% in "
                f"{current.month} — {margin_compression:.1f} percentage points."
            ),
            metrics={
                "peak_margin_percent": peak_margin_point.margin_percent,
                "current_margin_percent": current.margin_percent,
                "compression_pp": margin_compression,
            },
        ))
    elif margin_compression >= MARGIN_COMPRESSION_MEDIUM:
        unusual.append(UnusualChangeFact(
            type="margin_compression",
            severity="medium",
            description=(
                f"Profit margin fell from {peak_margin_point.margin_percent:.1f}% in "
                f"{peak_margin_point.month} to {current.margin_percent:.1f}% in "
                f"{current.month} — {margin_compression:.1f} percentage points."
            ),
            metrics={
                "peak_margin_percent": peak_margin_point.margin_percent,
                "current_margin_percent": current.margin_percent,
                "compression_pp": margin_compression,
            },
        ))

    # Rule 4: expense category spikes vs previous month
    if previous:
        prev_key = (previous.year, MONTH_ORDER.get(previous.month, 0), previous.month)
        prev_rows = {e.category: e.amount for e in expenses_by_month.get(prev_key, [])}
        for e in current_exp_rows:
            prev_amount = prev_rows.get(e.category)
            if prev_amount:
                spike = _pct_change(e.amount, prev_amount)
                if spike is not None and spike >= EXPENSE_SPIKE_PERCENT:
                    unusual.append(UnusualChangeFact(
                        type="expense_category_spike",
                        severity="medium",
                        description=(
                            f"{e.category} expenses rose {spike:.1f}% month-over-month "
                            f"(Rs {prev_amount:,.0f} → Rs {e.amount:,.0f})."
                        ),
                        metrics={
                            "category": e.category,
                            "previous_amount": prev_amount,
                            "current_amount": e.amount,
                            "change_percent": spike,
                        },
                    ))

    # Rule 5: month-over-month profit drop
    if profit_change is not None and profit_change <= -PROFIT_DROP_HIGH:
        unusual.append(UnusualChangeFact(
            type="profit_drop_mom",
            severity="high",
            description=(
                f"Profit fell {abs(profit_change):.1f}% month-over-month "
                f"(Rs {previous.profit:,.0f} → Rs {current.profit:,.0f})."
            ),
            metrics={
                "previous_profit": previous.profit,
                "current_profit": current.profit,
                "change_percent": profit_change,
            },
        ))

    return FinanceFacts(
        business_name=business.name,
        currency=business.currency or "PKR",
        months_analyzed=len(series),
        revenue=revenue_facts,
        expenses=expense_facts,
        profit=profit_facts,
        top_revenue_products=top_products,
        weak_products=weak_products,
        unusual_changes=unusual,
    )

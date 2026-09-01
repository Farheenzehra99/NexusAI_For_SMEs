"""
Deterministic marketing analysis service.

ARCHITECTURE RULE
-----------------
Every marketing number the Marketing Agent reports is computed HERE, in
plain Python, from database records (marketing_campaigns, products).
The LLM layer is strictly forbidden from calculating or inventing
campaign metrics — it only receives the MarketingFacts produced by this
module and may explain them or suggest actions.

EXPLAINABLE UNDERPERFORMANCE RULE
---------------------------------
The cross-campaign benchmark is computed from all valid campaigns:
    - benchmark conversion rate  = total conversions / total clicks * 100
    - benchmark cost/conversion  = total spend / total conversions

A campaign is UNDERPERFORMING when any of these code-evaluated conditions
holds (thresholds are module constants):
    1. conversion rate < 50% of the benchmark conversion rate, OR
    2. cost per conversion > 150% of the benchmark cost/conversion, OR
    3. zero conversions recorded from tracked clicks despite spend.

A campaign is OUTPERFORMING (opportunity) when:
    - conversion rate >= 125% of the benchmark AND
    - cost per conversion <= 110% of the benchmark.

Malformed rows (missing metrics, negative values, clicks > impressions,
conversions > clicks) are flagged "invalid_data" and excluded from the
benchmark so they cannot corrupt the comparison.
"""

from typing import Optional

from sqlalchemy.orm import Session

from ..models.business import Business, MarketingCampaign, Product
from ..schemas.marketing import (
    MarketingFacts,
    MarketingBenchmark,
    CampaignPerformanceFact,
    ReallocationRecommendation,
    ProductMarketingFact,
    ProductMarketingHighlights,
)

# ── Deterministic thresholds (tunable constants, no LLM involvement) ────────

UNDERPERFORMING_CONV_RATIO = 0.5    # conv rate below 50% of benchmark → flag
UNDERPERFORMING_CPC_RATIO = 1.5     # cost/conversion above 150% of benchmark → flag
OUTPERFORMING_CONV_RATIO = 1.25     # conv rate at/above 125% of benchmark → opportunity
OUTPERFORMING_CPC_RATIO = 1.1       # cost/conversion at/below 110% of benchmark → opportunity

TOP_PRODUCTS_COUNT = 3
DECLINING_PROMO_MIN_REVENUE = 300_000.0   # falling revenue above this → promote
WEAK_SELLER_UNITS = 20                    # fewer units sold → clearance candidate

# Presentation order: problems first, opportunities last
PERFORMANCE_ORDER = {
    "underperforming": 0,
    "insufficient_data": 1,
    "invalid_data": 2,
    "acceptable": 3,
    "outperforming": 4,
}


class MarketingDataError(Exception):
    """Raised when the request cannot be served (missing data)."""


class BusinessNotFoundError(MarketingDataError):
    pass


class NoCampaignDataError(MarketingDataError):
    pass


def get_marketing_snapshot(db: Session) -> MarketingFacts:
    """Build the complete deterministic marketing picture.

    Raises:
        BusinessNotFoundError: no business record in the database.
        NoCampaignDataError: no campaign records exist.
    """
    business = db.query(Business).first()
    if not business:
        raise BusinessNotFoundError("No business found. Run seed.py first.")

    campaigns = (
        db.query(MarketingCampaign)
        .filter(MarketingCampaign.business_id == business.id)
        .all()
    )
    if not campaigns:
        raise NoCampaignDataError(
            "No marketing campaigns found. Run seed.py first."
        )

    # ── Per-campaign raw metrics + data validity ──
    raw_facts: list[CampaignPerformanceFact] = []
    for c in campaigns:
        raw_facts.append(_campaign_fact(c))

    valid = [f for f in raw_facts if f.performance != "invalid_data"]

    # ── Benchmark over all valid campaigns ──
    total_spend = sum(f.spend for f in valid)
    total_impressions = sum(f.impressions for f in valid)
    total_clicks = sum(f.clicks for f in valid)
    total_conversions = sum(f.conversions for f in valid)
    total_revenue = sum(f.revenue_generated for f in valid)

    benchmark = MarketingBenchmark(
        campaign_count=len(raw_facts),
        valid_campaign_count=len(valid),
        invalid_campaign_count=len(raw_facts) - len(valid),
        total_spend=total_spend,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_conversions=total_conversions,
        total_revenue_generated=total_revenue,
        conversion_rate_percent=round(
            total_conversions / total_clicks * 100, 2
        ) if total_clicks else 0.0,
        cost_per_conversion=round(
            total_spend / total_conversions, 2
        ) if total_conversions else None,
        overall_ctr_percent=round(
            total_clicks / total_impressions * 100, 2
        ) if total_impressions else 0.0,
        overall_roas=round(
            total_revenue / total_spend, 2
        ) if total_spend else None,
    )

    # ── Classify valid campaigns against the benchmark ──
    facts: list[CampaignPerformanceFact] = []
    for f in raw_facts:
        if f.performance in ("invalid_data", "insufficient_data"):
            facts.append(f)  # reason already set during validation
        else:
            facts.append(_classify(f, benchmark))

    # Problems first; within a class, weakest conversion rate first
    facts.sort(key=lambda f: (
        PERFORMANCE_ORDER.get(f.performance, 99),
        f.conversion_rate_percent if f.conversion_rate_percent is not None else -1.0,
    ))

    # ── Reallocation recommendation (problem → best opportunity) ──
    underperforming = [f for f in facts if f.performance == "underperforming"]
    candidates = [
        f for f in facts
        if f.performance in ("outperforming", "acceptable") and f.roas is not None
    ]
    best = max(candidates, key=lambda f: f.roas) if candidates else None

    reallocation: Optional[ReallocationRecommendation] = None
    if underperforming and best and best.roas is not None:
        # Move the budget of the highest-spending underperformer.
        worst = max(underperforming, key=lambda f: f.spend)
        worst_cr = (
            f"{worst.conversion_rate_percent:.2f}%"
            if worst.conversion_rate_percent is not None
            else "0.00% (no conversions)"
        )
        reallocation = ReallocationRecommendation(
            from_campaign=worst.name,
            from_campaign_spend=worst.spend,
            to_campaign=best.name,
            to_campaign_roas=best.roas,
            to_campaign_cost_per_conversion=best.cost_per_conversion,
            rationale=(
                f"{worst.name} converts at {worst_cr} versus the "
                f"{benchmark.conversion_rate_percent}% benchmark, while "
                f"{best.name} delivers ROAS {best.roas} at "
                f"Rs {best.cost_per_conversion:,.2f} per conversion."
            ),
        )

    # ── Product performance relevant to marketing ──
    highlights = _product_highlights(db, business.id)

    return MarketingFacts(
        business_name=business.name,
        currency=business.currency or "PKR",
        benchmark=benchmark,
        campaigns=facts,
        underperforming_campaign_names=[f.name for f in underperforming],
        best_campaign_name=best.name if best else None,
        reallocation=reallocation,
        product_highlights=highlights,
    )


# ── Per-campaign metric computation and validation ──────────────────────────

def _campaign_fact(c: MarketingCampaign) -> CampaignPerformanceFact:
    """Compute rounded metrics for one campaign; flag malformed data."""
    spend = c.spend
    impressions = c.impressions
    clicks = c.clicks
    conversions = c.conversions
    revenue = c.revenue_generated if c.revenue_generated is not None else 0.0

    # Metrics are None while the row is untrusted; filled after validation.
    fact = CampaignPerformanceFact(
        name=c.name or "Unnamed campaign",
        channel=c.channel or "unknown",
        status=c.status or "unknown",
        start_date=c.start_date.isoformat() if c.start_date else None,
        end_date=c.end_date.isoformat() if c.end_date else None,
        spend=float(spend or 0),
        impressions=int(impressions or 0),
        clicks=int(clicks or 0),
        conversions=int(conversions or 0),
        revenue_generated=float(revenue),
        ctr_percent=None,
        conversion_rate_percent=None,
        cost_per_conversion=None,
        cost_per_click=None,
        roas=None,
        roi_percent=None,
        performance="unclassified",
        reason="",
    )

    problem = _validate_row(spend, impressions, clicks, conversions)
    if problem:
        fact.performance = "invalid_data"
        fact.reason = f"Malformed campaign data — {problem}. Excluded from the benchmark."
        return fact

    # Valid row → compute metrics (rounded once; classification reuses them).
    fact.ctr_percent = (
        round(clicks / impressions * 100, 2) if impressions > 0 else None
    )
    fact.conversion_rate_percent = (
        round(conversions / clicks * 100, 2) if clicks > 0 else None
    )
    fact.cost_per_conversion = (
        round(spend / conversions, 2) if conversions > 0 else None
    )
    fact.cost_per_click = round(spend / clicks, 2) if clicks > 0 else None
    fact.roas = round(revenue / spend, 2) if spend > 0 else None
    fact.roi_percent = (
        round((revenue - spend) / spend * 100, 1) if spend > 0 else None
    )

    if clicks == 0:
        fact.performance = "insufficient_data"
        fact.reason = (
            f"No clicks recorded from {impressions:,} impressions — "
            f"conversion rate cannot be computed."
        )
    return fact


def _validate_row(spend, impressions, clicks, conversions) -> Optional[str]:
    """Return a description of the data problem, or None when valid."""
    if any(v is None for v in (spend, impressions, clicks, conversions)):
        return "missing metric values"
    if spend < 0:
        return f"negative spend ({spend})"
    if impressions < 0 or clicks < 0 or conversions < 0:
        return "negative impression/click/conversion counts"
    if clicks > impressions:
        return f"clicks ({clicks:,}) exceed impressions ({impressions:,})"
    if conversions > clicks:
        return f"conversions ({conversions:,}) exceed clicks ({clicks:,})"
    return None


def _classify(f: CampaignPerformanceFact, b: MarketingBenchmark) -> CampaignPerformanceFact:
    """Apply the explainable rules. Uses the already-rounded metrics so the
    displayed numbers and the rule evaluation agree exactly."""
    cr = f.conversion_rate_percent
    cpc = f.cost_per_conversion
    b_cr = b.conversion_rate_percent
    b_cpc = b.cost_per_conversion

    # Rule 3: money spent, clicks tracked, no conversions at all.
    if f.conversions == 0 and f.clicks > 0:
        f.performance = "underperforming"
        f.reason = (
            f"No conversions recorded from {f.clicks:,} clicks despite "
            f"Rs {f.spend:,.0f} spend."
        )
        return f

    # Rule 1: conversion rate below 50% of the benchmark.
    if cr is not None and b_cr > 0 and cr < round(b_cr * UNDERPERFORMING_CONV_RATIO, 2):
        f.performance = "underperforming"
        f.reason = (
            f"Conversion rate {cr}% is below "
            f"{int(UNDERPERFORMING_CONV_RATIO * 100)}% of the {b_cr}% "
            f"cross-campaign benchmark ({round(b_cr * UNDERPERFORMING_CONV_RATIO, 2)}% floor)."
        )
        return f

    # Rule 2: cost per conversion above 150% of the benchmark.
    if cpc is not None and b_cpc is not None and cpc > round(b_cpc * UNDERPERFORMING_CPC_RATIO, 2):
        f.performance = "underperforming"
        f.reason = (
            f"Cost per conversion Rs {cpc:,.2f} exceeds "
            f"{int(UNDERPERFORMING_CPC_RATIO * 100)}% of the Rs {b_cpc:,.2f} "
            f"benchmark (Rs {round(b_cpc * UNDERPERFORMING_CPC_RATIO, 2):,.2f} ceiling)."
        )
        return f

    # Opportunity: strong conversion rate at an efficient cost.
    if (
        cr is not None and b_cr > 0
        and cr >= round(b_cr * OUTPERFORMING_CONV_RATIO, 2)
        and (cpc is None or b_cpc is None or cpc <= round(b_cpc * OUTPERFORMING_CPC_RATIO, 2))
    ):
        f.performance = "outperforming"
        f.reason = (
            f"Conversion rate {cr}% is at least "
            f"{int(OUTPERFORMING_CONV_RATIO * 100)}% of the {b_cr}% benchmark "
            f"({round(b_cr * OUTPERFORMING_CONV_RATIO, 2)}% bar)"
            + (
                f" at Rs {cpc:,.2f} per conversion, below the Rs {b_cpc:,.2f} benchmark."
                if cpc is not None and b_cpc is not None else "."
            )
        )
        return f

    f.performance = "acceptable"
    f.reason = (
        f"Conversion rate {cr if cr is not None else 0.0}% is within the acceptable "
        f"band around the {b_cr}% benchmark."
        if cr is not None
        else "No clicks recorded — performance cannot be assessed."
    )
    return f


# ── Product highlights for marketing decisions ──────────────────────────────

def _product_highlights(db: Session, business_id: int) -> ProductMarketingHighlights:
    products = (
        db.query(Product)
        .filter(Product.business_id == business_id, Product.is_active == 1)
        .all()
    )
    by_revenue = sorted(products, key=lambda p: p.total_revenue, reverse=True)

    top = [
        _product_fact(p, _top_note(p)) for p in by_revenue[:TOP_PRODUCTS_COUNT]
    ]
    declining = [
        _product_fact(p, _declining_note(p))
        for p in by_revenue
        if p.trend == "down" and p.total_revenue >= DECLINING_PROMO_MIN_REVENUE
    ]
    weak = [
        _product_fact(p, _weak_note(p))
        for p in by_revenue
        if p.total_sales < WEAK_SELLER_UNITS
    ]
    return ProductMarketingHighlights(
        top_performers=top, declining=declining, weak_sellers=weak,
    )


def _product_fact(p: Product, note: str) -> ProductMarketingFact:
    return ProductMarketingFact(
        name=p.name,
        sku=p.sku,
        category=p.category or "",
        revenue=float(p.total_revenue or 0),
        units_sold=int(p.total_sales or 0),
        trend=p.trend or "stable",
        stock_qty=int(p.stock_qty or 0),
        note=note,
    )


def _top_note(p: Product) -> str:
    note = f"Top revenue product — Rs {p.total_revenue:,.0f} from {p.total_sales} units sold"
    if p.stock_qty < 20:
        note += f"; only {p.stock_qty} units in stock — restock before scaling ads"
    return note


def _declining_note(p: Product) -> str:
    return (
        f"Declining trend with Rs {p.total_revenue:,.0f} revenue and "
        f"{p.total_sales} units sold — promotion candidate"
    )


def _weak_note(p: Product) -> str:
    return (
        f"Only {p.total_sales} units sold against {p.stock_qty} in stock — "
        f"clearance candidate"
    )

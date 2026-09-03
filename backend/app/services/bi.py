"""
Deterministic Business Intelligence service — the Business Health Score.

FORMULA (documented, explainable, deterministic, reproducible)
==============================================================

The Business Health Score is a weighted average of four domain
sub-scores, each on a 0-100 scale:

    Health Score = 35% x Finance + 25% x Inventory
                   + 20% x Marketing + 20% x Support

Weights reflect each domain's impact on a small retailer's survival:
cash and profit first (Finance), then the ability to keep selling
(Inventory), then demand generation (Marketing) and customer retention
(Support). When a domain's data is unavailable, its weight is
re-distributed proportionally across the available domains (weights are
re-normalized to sum to 1.0) and a data-coverage signal is emitted.

Each domain sub-score starts at 100 and applies the fixed rules below.
Every rule's points are rounded to 2 decimals, sub-scores are floored
at 0 (and capped at 100), and the composite is computed FROM THE
ROUNDED sub-scores so every published number stays mutually consistent.

FINANCE (weight 0.35)
    revenue_decline_from_peak  -0.5 pts per percentage point of revenue
                                decline from the 6-month peak, cap 25.
    margin_compression         -1.5 pts per percentage point the current
                                profit margin sits below its peak, cap 15.
    declining_trend            -5 pts when monthly revenue shows a
                                declining trend (consecutive declines).
    profit_drop_mom            -0.25 pts per percentage point of a
                                month-over-month profit drop, cap 10.
    (worst possible Finance sub-score: 45)

INVENTORY (weight 0.25)
    critical_stockout          -15 per critical-risk product, cap 30.
    out_of_stock               -15 per out-of-stock product, cap 30.
    high_risk                  -8 per high-risk product, cap 16.
    medium_risk                -4 per medium-risk product, cap 12.
    overstock                  -4 per overstocked product, cap 24.
    stagnant                   -3 per stagnant product, cap 12.
    (worst possible Inventory sub-score: 0)

MARKETING (weight 0.20)
    underperforming_campaign   -12 per campaign flagged by the Marketing
                                Agent's explainable rule, cap 48.
    outperforming_campaign     +4 per outperforming campaign, cap +8.
    low_roas                   -10 when the overall ROAS is known and
                                below 2.0 (ad spend not paying for itself).
    (worst possible Marketing sub-score: 42)

SUPPORT (weight 0.20)
    negative_feedback          -0.5 pts per percentage point of negative
                                feedback above a 30% baseline, cap 25.
    low_resolution             -0.3 pts per percentage point the ticket
                                resolution rate sits below 70%, cap 10.
    complaint_surge            -8 when complaints more than doubled vs
                                the prior period (>+100%); -6 when >+50%;
                                -3 when >+20%.
    (worst possible Support sub-score: 57)

ROUNDING
    Sub-scores and the composite are rounded half-up to integers using
    int(x + 0.5) — deterministic and identical on every platform.

RISK BANDS
    80-100 low | 60-79 moderate | 40-59 high | 0-39 critical

The LLM NEVER computes this score. It only receives the computed result
and may explain it. All inputs come verbatim from the four domain
services — this module never re-derives or invents business facts.
"""

from typing import Optional

from sqlalchemy.orm import Session

from ..models.business import Business
from ..schemas.bi import (
    BIFacts,
    DomainScore,
    HealthScore,
    KeySignal,
    ScoreComponent,
)
from ..schemas.finance import FinanceFacts
from ..schemas.inventory import InventoryFacts
from ..schemas.marketing import MarketingFacts
from ..schemas.support import SupportFacts
from .finance import FinanceDataError, get_financial_snapshot
from .inventory import InventoryDataError, get_inventory_snapshot
from .marketing import MarketingDataError, get_marketing_snapshot
from .support import SupportDataError, get_support_snapshot

# ---------------------------------------------------------------------------
# Configuration (documented constants — the formula's only free parameters)
# ---------------------------------------------------------------------------

DOMAIN_ORDER = ("finance", "inventory", "marketing", "support")
DOMAIN_LABELS = {
    "finance": "Finance",
    "inventory": "Inventory",
    "marketing": "Marketing",
    "support": "Support",
}
DOMAIN_WEIGHTS = {
    "finance": 0.35,
    "inventory": 0.25,
    "marketing": 0.20,
    "support": 0.20,
}

# Risk bands
RISK_LOW_THRESHOLD = 80      # score >= 80  -> low
RISK_MODERATE_THRESHOLD = 60  # score >= 60 -> moderate
RISK_HIGH_THRESHOLD = 40      # score >= 40 -> high
                                # score < 40 -> critical

# Finance rules
FINANCE_DECLINE_PTS_PER_PCT = 0.5
FINANCE_DECLINE_CAP = 25.0
FINANCE_MARGIN_PTS_PER_PP = 1.5
FINANCE_MARGIN_CAP = 15.0
FINANCE_DECLINING_TREND_PENALTY = 5.0
FINANCE_PROFIT_DROP_PTS_PER_PCT = 0.25
FINANCE_PROFIT_DROP_CAP = 10.0

# Inventory rules
INVENTORY_CRITICAL_PENALTY = 15.0
INVENTORY_CRITICAL_CAP = 30.0
INVENTORY_OUT_OF_STOCK_PENALTY = 15.0
INVENTORY_OUT_OF_STOCK_CAP = 30.0
INVENTORY_HIGH_PENALTY = 8.0
INVENTORY_HIGH_CAP = 16.0
INVENTORY_MEDIUM_PENALTY = 4.0
INVENTORY_MEDIUM_CAP = 12.0
INVENTORY_OVERSTOCK_PENALTY = 4.0
INVENTORY_OVERSTOCK_CAP = 24.0
INVENTORY_STAGNANT_PENALTY = 3.0
INVENTORY_STAGNANT_CAP = 12.0

# Marketing rules
MARKETING_UNDERPERFORMING_PENALTY = 12.0
MARKETING_UNDERPERFORMING_CAP = 48.0
MARKETING_OUTPERFORMING_BONUS = 4.0
MARKETING_OUTPERFORMING_CAP = 8.0
MARKETING_LOW_ROAS_THRESHOLD = 2.0
MARKETING_LOW_ROAS_PENALTY = 10.0

# Support rules
SUPPORT_NEGATIVE_BASELINE_PCT = 30.0
SUPPORT_NEGATIVE_PTS_PER_PCT = 0.5
SUPPORT_NEGATIVE_CAP = 25.0
SUPPORT_RESOLUTION_TARGET_PCT = 70.0
SUPPORT_RESOLUTION_PTS_PER_PCT = 0.3
SUPPORT_RESOLUTION_CAP = 10.0
SUPPORT_SURGE_HIGH_PCT = 100.0     # > +100% -> -8
SUPPORT_SURGE_MEDIUM_PCT = 50.0    # > +50%  -> -6
SUPPORT_SURGE_LOW_PCT = 20.0       # > +20%  -> -3
SUPPORT_SURGE_HIGH_PENALTY = 8.0
SUPPORT_SURGE_MEDIUM_PENALTY = 6.0
SUPPORT_SURGE_LOW_PENALTY = 3.0


class BIDataError(Exception):
    """Base error for BI data problems."""


class BusinessNotFoundError(BIDataError):
    pass


class NoBIDataError(BIDataError):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round_half_up(x: float) -> int:
    """Deterministic round-half-up (immune to float noise at .5)."""
    return int(x + 0.5)


def _component(rule: str, points: float, reason: str) -> ScoreComponent:
    return ScoreComponent(rule=rule, points=round(points, 2), reason=reason)


def _fmt_weight(w: float) -> str:
    """0.35 -> '35%'; 0.4375 -> '43.75%'."""
    return f"{w * 100:g}%"


def risk_level(score: int) -> str:
    """Map a 0-100 score to its documented risk band."""
    if score >= RISK_LOW_THRESHOLD:
        return "low"
    if score >= RISK_MODERATE_THRESHOLD:
        return "moderate"
    if score >= RISK_HIGH_THRESHOLD:
        return "high"
    return "critical"


# ---------------------------------------------------------------------------
# Domain sub-scores (pure functions of the domain facts — controlled-input
# testable, no database access)
# ---------------------------------------------------------------------------

def finance_subscore(
    f: FinanceFacts,
) -> tuple[int, list[ScoreComponent], list[KeySignal]]:
    components: list[ScoreComponent] = []

    decline = f.revenue.decline_from_peak_percent  # negative when below peak
    decline_pct = abs(min(decline, 0.0))
    pts = min(FINANCE_DECLINE_PTS_PER_PCT * decline_pct, FINANCE_DECLINE_CAP)
    if pts > 0:
        components.append(_component(
            "revenue_decline_from_peak", -pts,
            f"Revenue is {decline:+.2f}% from the {f.revenue.peak_month} peak "
            f"(Rs {f.revenue.current_revenue:,.0f} vs Rs "
            f"{f.revenue.peak_revenue:,.0f}); "
            f"-{FINANCE_DECLINE_PTS_PER_PCT} pts per pct point, "
            f"capped at {FINANCE_DECLINE_CAP:.0f}.",
        ))

    compression = max(f.profit.margin_compression_pp, 0.0)
    pts = min(FINANCE_MARGIN_PTS_PER_PP * compression, FINANCE_MARGIN_CAP)
    if pts > 0:
        components.append(_component(
            "margin_compression", -pts,
            f"Profit margin is {f.profit.current_margin_percent:.2f}% vs the "
            f"{f.profit.peak_margin_percent:.2f}% peak ({compression:.2f}pp "
            f"compression); -{FINANCE_MARGIN_PTS_PER_PP} pts per pp, "
            f"capped at {FINANCE_MARGIN_CAP:.0f}.",
        ))

    if f.revenue.trend == "declining":
        components.append(_component(
            "declining_trend", -FINANCE_DECLINING_TREND_PENALTY,
            f"Monthly revenue trend is declining; flat "
            f"-{FINANCE_DECLINING_TREND_PENALTY:.0f} pts.",
        ))

    mom = f.profit.change_percent
    if mom is not None and mom < 0:
        pts = min(
            FINANCE_PROFIT_DROP_PTS_PER_PCT * abs(mom),
            FINANCE_PROFIT_DROP_CAP,
        )
        components.append(_component(
            "profit_drop_mom", -pts,
            f"Profit fell {mom:+.2f}% month-over-month; "
            f"-{FINANCE_PROFIT_DROP_PTS_PER_PCT} pts per pct point, "
            f"capped at {FINANCE_PROFIT_DROP_CAP:.0f}.",
        ))

    score = max(0.0, 100.0 + sum(c.points for c in components))

    signals = [
        KeySignal(
            domain="finance", label="Revenue vs peak",
            value=f"{decline:+.2f}% from {f.revenue.peak_month} peak",
            direction=(
                "negative" if decline <= -5
                else ("neutral" if decline < 0 else "positive")
            ),
        ),
        KeySignal(
            domain="finance", label="Profit margin",
            value=(
                f"{f.profit.current_margin_percent:.2f}% "
                f"(-{compression:.2f}pp vs peak)"
            ),
            direction=(
                "negative" if compression > 2
                else ("neutral" if compression > 0 else "positive")
            ),
        ),
        KeySignal(
            domain="finance", label="Revenue trend",
            value=f.revenue.trend,
            direction={
                "declining": "negative", "growing": "positive",
            }.get(f.revenue.trend, "neutral"),
        ),
    ]
    return _round_half_up(score), components, signals


def inventory_subscore(
    f: InventoryFacts,
) -> tuple[int, list[ScoreComponent], list[KeySignal]]:
    counts: dict[str, int] = {}
    for r in f.risks:
        counts[r.risk_level] = counts.get(r.risk_level, 0) + 1
    critical = counts.get("critical", 0)
    out_of_stock = counts.get("out_of_stock", 0)
    high = counts.get("high", 0)
    medium = counts.get("medium", 0)
    overstock = counts.get("overstock", 0)
    stagnant = counts.get("stagnant", 0)

    components: list[ScoreComponent] = []
    if critical:
        pts = min(
            INVENTORY_CRITICAL_PENALTY * critical, INVENTORY_CRITICAL_CAP
        )
        components.append(_component(
            "critical_stockout", -pts,
            f"{critical} product(s) at critical stock-out risk; "
            f"-{INVENTORY_CRITICAL_PENALTY:.0f} each, "
            f"capped at {INVENTORY_CRITICAL_CAP:.0f}.",
        ))
    if out_of_stock:
        pts = min(
            INVENTORY_OUT_OF_STOCK_PENALTY * out_of_stock,
            INVENTORY_OUT_OF_STOCK_CAP,
        )
        components.append(_component(
            "out_of_stock", -pts,
            f"{out_of_stock} product(s) out of stock; "
            f"-{INVENTORY_OUT_OF_STOCK_PENALTY:.0f} each, "
            f"capped at {INVENTORY_OUT_OF_STOCK_CAP:.0f}.",
        ))
    if high:
        pts = min(INVENTORY_HIGH_PENALTY * high, INVENTORY_HIGH_CAP)
        components.append(_component(
            "high_risk", -pts,
            f"{high} product(s) at high stock-out risk; "
            f"-{INVENTORY_HIGH_PENALTY:.0f} each, "
            f"capped at {INVENTORY_HIGH_CAP:.0f}.",
        ))
    if medium:
        pts = min(INVENTORY_MEDIUM_PENALTY * medium, INVENTORY_MEDIUM_CAP)
        components.append(_component(
            "medium_risk", -pts,
            f"{medium} product(s) at medium stock-out risk; "
            f"-{INVENTORY_MEDIUM_PENALTY:.0f} each, "
            f"capped at {INVENTORY_MEDIUM_CAP:.0f}.",
        ))
    if overstock:
        pts = min(
            INVENTORY_OVERSTOCK_PENALTY * overstock, INVENTORY_OVERSTOCK_CAP
        )
        components.append(_component(
            "overstock", -pts,
            f"{overstock} overstocked product(s); "
            f"-{INVENTORY_OVERSTOCK_PENALTY:.0f} each, "
            f"capped at {INVENTORY_OVERSTOCK_CAP:.0f}.",
        ))
    if stagnant:
        pts = min(
            INVENTORY_STAGNANT_PENALTY * stagnant, INVENTORY_STAGNANT_CAP
        )
        components.append(_component(
            "stagnant", -pts,
            f"{stagnant} stagnant product(s) with no sales; "
            f"-{INVENTORY_STAGNANT_PENALTY:.0f} each, "
            f"capped at {INVENTORY_STAGNANT_CAP:.0f}.",
        ))

    score = max(0.0, 100.0 + sum(c.points for c in components))

    s = f.summary
    signals = [
        KeySignal(
            domain="inventory", label="Critical stock-out risks",
            value=f"{s.critical_count} product(s)",
            direction="negative" if s.critical_count > 0 else "positive",
        ),
        KeySignal(
            domain="inventory", label="Overstocked products",
            value=(
                f"{s.overstock_count} product(s), excess value "
                f"Rs {s.excess_stock_value_retail:,.0f}"
            ),
            direction="negative" if s.overstock_count > 0 else "neutral",
        ),
        KeySignal(
            domain="inventory", label="Reorder recommendation",
            value=(
                f"{s.recommended_reorder_units} units "
                f"(Rs {s.recommended_reorder_cost:,.0f})"
                if s.recommended_reorder_units > 0
                else "no reorder needed"
            ),
            direction="neutral" if s.recommended_reorder_units > 0
            else "positive",
        ),
    ]
    return _round_half_up(score), components, signals


def marketing_subscore(
    f: MarketingFacts,
) -> tuple[int, list[ScoreComponent], list[KeySignal]]:
    under = len(f.underperforming_campaign_names)
    out = sum(1 for c in f.campaigns if c.performance == "outperforming")
    roas = f.benchmark.overall_roas

    components: list[ScoreComponent] = []
    if under:
        pts = min(
            MARKETING_UNDERPERFORMING_PENALTY * under,
            MARKETING_UNDERPERFORMING_CAP,
        )
        components.append(_component(
            "underperforming_campaign", -pts,
            f"{under} campaign(s) flagged by the explainable rule "
            f"({', '.join(f.underperforming_campaign_names)}); "
            f"-{MARKETING_UNDERPERFORMING_PENALTY:.0f} each, "
            f"capped at {MARKETING_UNDERPERFORMING_CAP:.0f}.",
        ))
    if out:
        pts = min(
            MARKETING_OUTPERFORMING_BONUS * out, MARKETING_OUTPERFORMING_CAP
        )
        components.append(_component(
            "outperforming_campaign", pts,
            f"{out} outperforming campaign(s); "
            f"+{MARKETING_OUTPERFORMING_BONUS:.0f} each, "
            f"capped at +{MARKETING_OUTPERFORMING_CAP:.0f}.",
        ))
    if roas is not None and roas < MARKETING_LOW_ROAS_THRESHOLD:
        components.append(_component(
            "low_roas", -MARKETING_LOW_ROAS_PENALTY,
            f"Overall ROAS {roas:g} is below "
            f"{MARKETING_LOW_ROAS_THRESHOLD:g}; "
            f"flat -{MARKETING_LOW_ROAS_PENALTY:.0f}.",
        ))

    score = 100.0 + sum(c.points for c in components)
    score = max(0.0, min(100.0, score))

    out_names = [
        c.name for c in f.campaigns if c.performance == "outperforming"
    ]
    signals = [
        KeySignal(
            domain="marketing", label="Underperforming campaigns",
            value=(
                f"{under}: {', '.join(f.underperforming_campaign_names)}"
                if under else "none"
            ),
            direction="negative" if under > 0 else "positive",
        ),
        KeySignal(
            domain="marketing", label="Outperforming campaigns",
            value=f"{out}: {', '.join(out_names)}" if out else "none",
            direction="positive" if out > 0 else "neutral",
        ),
        KeySignal(
            domain="marketing", label="Overall ROAS",
            value=f"{roas:g}" if roas is not None else "not available",
            direction=(
                "positive" if roas is not None and roas >= 2.0
                else ("negative" if roas is not None else "neutral")
            ),
        ),
    ]
    return _round_half_up(score), components, signals


def support_subscore(
    f: SupportFacts,
) -> tuple[int, list[ScoreComponent], list[KeySignal]]:
    s = f.summary
    t = f.trend
    components: list[ScoreComponent] = []

    excess = max(0.0, s.negative_feedback_percent - SUPPORT_NEGATIVE_BASELINE_PCT)
    pts = min(SUPPORT_NEGATIVE_PTS_PER_PCT * excess, SUPPORT_NEGATIVE_CAP)
    if pts > 0:
        components.append(_component(
            "negative_feedback", -pts,
            f"Negative feedback is {s.negative_feedback_percent}% of "
            f"{s.total_tickets} tickets, above the "
            f"{SUPPORT_NEGATIVE_BASELINE_PCT:.0f}% baseline; "
            f"-{SUPPORT_NEGATIVE_PTS_PER_PCT} pts per pct point, "
            f"capped at {SUPPORT_NEGATIVE_CAP:.0f}.",
        ))

    shortfall = max(
        0.0, SUPPORT_RESOLUTION_TARGET_PCT - s.resolution_rate_percent
    )
    pts = min(SUPPORT_RESOLUTION_PTS_PER_PCT * shortfall, SUPPORT_RESOLUTION_CAP)
    if pts > 0:
        components.append(_component(
            "low_resolution", -pts,
            f"Ticket resolution rate is {s.resolution_rate_percent}%, below "
            f"the {SUPPORT_RESOLUTION_TARGET_PCT:.0f}% target; "
            f"-{SUPPORT_RESOLUTION_PTS_PER_PCT} pts per pct point, "
            f"capped at {SUPPORT_RESOLUTION_CAP:.0f}.",
        ))

    change = t.complaints_change_percent
    if change is not None:
        if change > SUPPORT_SURGE_HIGH_PCT:
            components.append(_component(
                "complaint_surge", -SUPPORT_SURGE_HIGH_PENALTY,
                f"Complaints are up {change:+.2f}% vs the prior period "
                f"(more than doubled); flat "
                f"-{SUPPORT_SURGE_HIGH_PENALTY:.0f}.",
            ))
        elif change > SUPPORT_SURGE_MEDIUM_PCT:
            components.append(_component(
                "complaint_surge", -SUPPORT_SURGE_MEDIUM_PENALTY,
                f"Complaints are up {change:+.2f}% vs the prior period; "
                f"flat -{SUPPORT_SURGE_MEDIUM_PENALTY:.0f}.",
            ))
        elif change > SUPPORT_SURGE_LOW_PCT:
            components.append(_component(
                "complaint_surge", -SUPPORT_SURGE_LOW_PENALTY,
                f"Complaints are up {change:+.2f}% vs the prior period; "
                f"flat -{SUPPORT_SURGE_LOW_PENALTY:.0f}.",
            ))

    score = max(0.0, 100.0 + sum(c.points for c in components))

    signals = [
        KeySignal(
            domain="support", label="Negative feedback",
            value=f"{s.negative_feedback_percent}% of {s.total_tickets} tickets",
            direction=(
                "negative" if s.negative_feedback_percent > 50
                else ("neutral" if s.negative_feedback_percent > 30
                      else "positive")
            ),
        ),
        KeySignal(
            domain="support", label="Complaint volume trend",
            value=(
                f"{change:+.2f}% vs prior period"
                if change is not None else "no prior-period comparison"
            ),
            direction=(
                "negative" if change is not None and change > 20
                else ("positive" if change is not None and change < -20
                      else "neutral")
            ),
        ),
        KeySignal(
            domain="support", label="Open tickets",
            value=f"{s.open} of {s.total_tickets} open",
            direction=(
                "negative"
                if s.total_tickets and s.open > s.total_tickets / 2
                else "neutral"
            ),
        ),
    ]
    return _round_half_up(score), components, signals


# ---------------------------------------------------------------------------
# Composite score (pure function — controlled-input testable)
# ---------------------------------------------------------------------------

def compute_health_score(subscores: dict[str, int]) -> tuple[int, str]:
    """Weighted composite from ALREADY-ROUNDED domain sub-scores.

    Weights are re-normalized over the provided domains, so a missing
    domain never breaks the score. Returns (score, risk_level).
    """
    available = [d for d in DOMAIN_ORDER if d in subscores]
    if not available:
        raise NoBIDataError("No domain sub-scores available.")

    total_weight = sum(DOMAIN_WEIGHTS[d] for d in available)
    weighted = sum(
        subscores[d] * (DOMAIN_WEIGHTS[d] / total_weight) for d in available
    )
    score = _round_half_up(weighted)
    return score, risk_level(score)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_LOADERS = {
    "finance": (get_financial_snapshot, FinanceDataError),
    "inventory": (get_inventory_snapshot, InventoryDataError),
    "marketing": (get_marketing_snapshot, MarketingDataError),
    "support": (get_support_snapshot, SupportDataError),
}

_SUBSCORERS = {
    "finance": finance_subscore,
    "inventory": inventory_subscore,
    "marketing": marketing_subscore,
    "support": support_subscore,
}


def get_bi_snapshot(db: Session, business_id: int | None = None) -> BIFacts:
    """Assemble one business picture from the four agent snapshots.

    Each domain is loaded independently; a failing domain is marked
    missing and its weight re-distributed. Raises BusinessNotFoundError
    when there is no business at all, and NoBIDataError when EVERY
    domain failed.
    """
    if business_id is not None:
        business = db.get(Business, business_id)
    else:
        business = db.query(Business).first()
    if business is None:
        raise BusinessNotFoundError("No business found.")

    facts_by_domain: dict[str, object] = {}
    missing: list[str] = []
    for domain in DOMAIN_ORDER:
        loader, error_cls = _LOADERS[domain]
        try:
            facts_by_domain[domain] = loader(db, business_id=business.id)
        except error_cls:
            missing.append(domain)

    if not facts_by_domain:
        raise NoBIDataError(
            "No agent data available for this business."
        )

    available = [d for d in DOMAIN_ORDER if d in facts_by_domain]
    total_weight = sum(DOMAIN_WEIGHTS[d] for d in available)

    domain_scores: list[DomainScore] = []
    signals: list[KeySignal] = []
    for domain in available:
        score, components, domain_signals = _SUBSCORERS[domain](
            facts_by_domain[domain]
        )
        domain_scores.append(DomainScore(
            domain=domain,
            label=DOMAIN_LABELS[domain],
            score=score,
            weight=round(DOMAIN_WEIGHTS[domain] / total_weight, 4),
            data_available=True,
            components=components,
        ))
        signals.extend(domain_signals)

    if missing:
        signals.append(KeySignal(
            domain="bi", label="Data coverage",
            value=(
                f"{', '.join(missing)} data unavailable; "
                "weights re-normalized"
            ),
            direction="neutral",
        ))

    score_by_domain = {ds.domain: ds.score for ds in domain_scores}
    composite, level = compute_health_score(score_by_domain)

    formula = (
        "Business Health Score = "
        + " + ".join(
            f"{_fmt_weight(ds.weight)} {ds.label} ({ds.score})"
            for ds in domain_scores
        )
        + f" = {composite} ({level} risk)"
    )
    if missing:
        formula += "; weights re-normalized over available domains"

    weakest = sorted(
        available,
        key=lambda d: (score_by_domain[d], DOMAIN_ORDER.index(d)),
    )[0]
    strongest = sorted(
        available,
        key=lambda d: (-score_by_domain[d], DOMAIN_ORDER.index(d)),
    )[0]

    as_of: Optional[str] = None
    if "support" in facts_by_domain:
        as_of = facts_by_domain["support"].as_of_date
    elif "inventory" in facts_by_domain:
        as_of = facts_by_domain["inventory"].as_of_date

    return BIFacts(
        business_name=business.name,
        currency=business.currency or "PKR",
        as_of_date=as_of,
        included_domains=available,
        missing_domains=missing,
        health_score=HealthScore(
            score=composite,
            risk_level=level,
            formula=formula,
            domain_scores=domain_scores,
            weakest_domain=weakest,
            strongest_domain=strongest,
        ),
        key_signals=signals,
        finance=facts_by_domain.get("finance"),
        inventory=facts_by_domain.get("inventory"),
        marketing=facts_by_domain.get("marketing"),
        support=facts_by_domain.get("support"),
    )


__all__ = [
    "get_bi_snapshot",
    "compute_health_score",
    "risk_level",
    "finance_subscore",
    "inventory_subscore",
    "marketing_subscore",
    "support_subscore",
    "BusinessNotFoundError",
    "NoBIDataError",
    "DOMAIN_WEIGHTS",
    "DOMAIN_ORDER",
]

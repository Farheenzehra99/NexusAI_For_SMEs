"""
Deterministic CEO orchestration service.

The CEO Agent answers the owner's question in three deterministic steps:

1. ROUTE (route_question)
   Keyword rules decide which specialized agents are needed. A
   sales/revenue question routes to ALL FOUR agents, because a sales
   decline can come from any of them. Domain-specific questions route
   only to the relevant agent(s). Unrecognized questions get the full
   business review (all four agents).

2. GATHER (get_bi_snapshot)
   The BI snapshot is the aggregation layer: it already loads the four
   agents' structured findings, re-normalizes weights when a domain is
   unavailable, and computes the Business Health Score. The CEO never
   queries raw tables and never re-derives business facts.

3. SYNTHESIZE (pure rules below)
   Key findings come verbatim from the BI key signals. Root causes and
   recommended actions are produced by fixed, documented rules that only
   quote numbers already present in the agents' structured outputs.
   Priorities are fixed per rule:

       urgent  — the top-selling product is about to stock out
       high    — a customer-facing failure that compounds daily
       medium  — money left on the table (marketing / working capital)
       low     — structural improvements

Partial failure: a domain that fails to load is marked missing, its
findings/actions are simply absent, and the answer is flagged
incomplete with the reason. If EVERY domain fails, NoBIDataError is
raised (mapped to HTTP 404 by the API layer).

The LLM never participates in steps 1-3. It only narrates the finished
plan (app/services/llm.py, interpret_ceo_answer).
"""

from typing import Optional

from sqlalchemy.orm import Session

from ..schemas.bi import BIFacts
from ..schemas.ceo import (
    CEOAnswer,
    KeyFinding,
    RecommendedAction,
    RootCause,
    RoutingDecision,
)
from .bi import (
    DOMAIN_LABELS,
    NoBIDataError,          # noqa: F401  (re-exported for the API layer)
    BusinessNotFoundError,  # noqa: F401
    get_bi_snapshot,
)

# ---------------------------------------------------------------------------
# Routing (deterministic keyword rules)
# ---------------------------------------------------------------------------

AGENT_NAMES = {
    "finance": "Finance Agent",
    "inventory": "Inventory Agent",
    "marketing": "Marketing Agent",
    "support": "Customer Support Agent",
}

# A sales/revenue problem needs every lens — this is the demo question.
_SALES_PROBLEM_KEYWORDS = (
    "sales", "revenue", "profit", "income",
    "decline", "declining", "down", "falling", "dropping", "losing",
)
_INVENTORY_KEYWORDS = ("stock", "inventory", "reorder", "supply", "shelf")
_MARKETING_KEYWORDS = ("campaign", "ad", "ads", "marketing", "budget",
                       "promotion", "advert")
_SUPPORT_KEYWORDS = ("customer", "complaint", "delivery", "feedback",
                     "return", "refund", "courier")
_FINANCE_KEYWORDS = ("expense", "expenses", "cost", "costs", "margin",
                     "cash", "money", "pricing")

_SALES_ROUTING_REASONS = {
    "finance": "revenue and margin trends diagnose the decline",
    "inventory": "stock-outs of best sellers directly cap sales",
    "marketing": "campaign performance drives customer demand",
    "support": "delivery complaints hurt repeat purchases",
}
_DOMAIN_ROUTING_REASONS = {
    "finance": "the question concerns money, costs, or margins",
    "inventory": "the question concerns stock and availability",
    "marketing": "the question concerns campaigns and ad spend",
    "support": "the question concerns customers and complaints",
}


def route_question(question: str) -> dict[str, str]:
    """Deterministically map a question to the domains that must answer it.

    Returns {domain: reason}. Rules (checked in order):
        1. Any sales/revenue keyword  -> all four agents.
        2. Otherwise, each domain's own keywords add that domain.
        3. No keyword matched at all  -> all four agents (full review).
    """
    q = (question or "").lower()

    if any(k in q for k in _SALES_PROBLEM_KEYWORDS):
        return dict(_SALES_ROUTING_REASONS)

    routed: dict[str, str] = {}
    if any(k in q for k in _FINANCE_KEYWORDS):
        routed["finance"] = _DOMAIN_ROUTING_REASONS["finance"]
    if any(k in q for k in _INVENTORY_KEYWORDS):
        routed["inventory"] = _DOMAIN_ROUTING_REASONS["inventory"]
    if any(k in q for k in _MARKETING_KEYWORDS):
        routed["marketing"] = _DOMAIN_ROUTING_REASONS["marketing"]
    if any(k in q for k in _SUPPORT_KEYWORDS):
        routed["support"] = _DOMAIN_ROUTING_REASONS["support"]

    if not routed:
        # Unrecognized question -> full business review.
        return {
            "finance": "general business review",
            "inventory": "general business review",
            "marketing": "general business review",
            "support": "general business review",
        }
    return routed


def _understood_as(question: str, routed: dict[str, str]) -> str:
    q = (question or "").lower()
    if any(k in q for k in _SALES_PROBLEM_KEYWORDS):
        return (
            "The owner wants to understand why sales have fallen and what "
            "to do about it."
        )
    if len(routed) == 4:
        return "The owner wants an overall business assessment and action plan."
    areas = " and ".join(DOMAIN_LABELS[d] for d in routed)
    return f"The owner is asking about {areas.lower()}."


def understand_question(question: str) -> tuple[dict[str, str], str]:
    """Public routing helper for the UI: returns (domain -> reason,
    plain-language restatement) WITHOUT touching the database.

    GET /api/ceo/route uses this so the Command Center can show the
    CEO's real routing decision before the specialist agents run.
    """
    routed = route_question(question)
    return routed, _understood_as(question, routed)


# ---------------------------------------------------------------------------
# Synthesis rules (pure functions of the BI facts — controlled-input testable)
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


def _key_findings(bi: BIFacts, consulted: list[str]) -> list[KeyFinding]:
    """BI key signals verbatim, restricted to the consulted agents."""
    return [
        KeyFinding(
            domain=sig.domain,
            agent_name=AGENT_NAMES[sig.domain],
            statement=f"{sig.label}: {sig.value}",
            severity=sig.direction,
        )
        for sig in bi.key_signals
        if sig.domain in consulted
    ]


def _best_seller_stockout(bi: BIFacts) -> Optional[RootCause]:
    """Critical stock-out on a product that is also a top revenue driver."""
    inv = bi.inventory
    fin = bi.finance
    if inv is None or fin is None:
        return None

    top_skus = {p.sku for p in fin.top_revenue_products[:3]}
    for product in inv.products:
        if product.sku in top_skus and product.risk_level == "critical":
            revenue = next(
                (p.revenue for p in fin.top_revenue_products
                 if p.sku == product.sku),
                0.0,
            )
            days = (
                f"{product.days_of_stock_remaining:.2f}"
                if product.days_of_stock_remaining is not None else "unknown"
            )
            return RootCause(
                title="Best-selling product is about to stock out",
                statement=(
                    f"{product.name} generates Rs {revenue:,.0f} of revenue "
                    f"(the business's top seller) but only "
                    f"{product.current_stock} units remain — about {days} "
                    "days of sales — so the best seller is about to stop "
                    "selling entirely."
                ),
                contributing_domains=["inventory", "finance"],
                evidence=[
                    f"Stock: {product.current_stock} units "
                    f"(about {days} days of sales left)",
                    f"Revenue contribution: Rs {revenue:,.0f} "
                    "(top revenue product)",
                    f"Recommended reorder quantity: "
                    f"{product.recommended_reorder_qty} units",
                ],
            )
    return None


def _delivery_root_cause(bi: BIFacts) -> Optional[RootCause]:
    """Delivery problems are the dominant complaint theme."""
    sup = bi.support
    if sup is None:
        return None
    if sup.top_theme != "delivery_problems":
        return None

    delivery_theme = next(
        (t for t in sup.themes if t.theme == "delivery_problems"), None
    )
    change = sup.trend.complaints_change_percent
    surge = (
        f", up {change:+.2f}% vs the prior period"
        if change is not None else ""
    )
    return RootCause(
        title="Delivery problems are driving customers away",
        statement=(
            f"Delivery issues are the top complaint theme "
            f"({delivery_theme.count} of {sup.summary.total_tickets} tickets, "
            f"{delivery_theme.share_percent}% of feedback){surge}, with "
            f"{sup.delivery.open_count} still unresolved — repeat purchases "
            "are at risk."
        ),
        contributing_domains=["support"],
        evidence=[
            f"Negative feedback: {sup.summary.negative_feedback_percent}% "
            f"of {sup.summary.total_tickets} tickets",
            f"Delivery complaints: {delivery_theme.count} tickets "
            f"({delivery_theme.share_percent}% of feedback)",
            f"Open delivery tickets: {sup.delivery.open_count}",
            f"Reported delays average {sup.delivery.avg_reported_delay_days} "
            f"days (longest {sup.delivery.max_reported_delay_days})",
        ],
    )


def _campaign_root_cause(bi: BIFacts) -> Optional[RootCause]:
    """An underperforming campaign weakens demand generation."""
    mk = bi.marketing
    if mk is None or not mk.underperforming_campaign_names:
        return None

    worst = next(
        c for c in mk.campaigns
        if c.performance == "underperforming"
    )
    bench = mk.benchmark
    cpc = (
        f"Rs {worst.cost_per_conversion:,.2f} per conversion vs the "
        f"benchmark Rs {bench.cost_per_conversion:,.2f}"
        if worst.cost_per_conversion is not None
        and bench.cost_per_conversion is not None
        else "no conversions recorded"
    )
    rate = (
        f"{worst.conversion_rate_percent}% vs the cross-campaign "
        f"benchmark {bench.conversion_rate_percent}%"
        if worst.conversion_rate_percent is not None
        else "no conversions from tracked clicks"
    )
    return RootCause(
        title="An underperforming campaign is wasting ad spend",
        statement=(
            f"The {worst.name} campaign converts at {rate}, so ad money "
            "generates fewer customers than the other campaigns."
        ),
        contributing_domains=["marketing"],
        evidence=[
            f"Conversion rate: {rate}",
            f"Cost efficiency: {cpc}",
            f"Spend tied up: Rs {worst.spend:,.0f}",
            f"Campaigns flagged: "
            f"{', '.join(mk.underperforming_campaign_names)}",
        ],
    )


def _revenue_context_root_cause(bi: BIFacts) -> Optional[RootCause]:
    """The confirmed top-line symptom the root causes explain."""
    fin = bi.finance
    if fin is None:
        return None
    decline = fin.revenue.decline_from_peak_percent
    if decline > -5:
        return None
    return RootCause(
        title="Revenue is significantly below its peak",
        statement=(
            f"Revenue is {decline:+.2f}% below the {fin.revenue.peak_month} "
            f"peak (Rs {fin.revenue.current_revenue:,.0f} vs Rs "
            f"{fin.revenue.peak_revenue:,.0f}), with the profit margin "
            f"compressed to {fin.profit.current_margin_percent:.2f}% from "
            f"the {fin.profit.peak_margin_percent:.2f}% peak — the problem "
            "the other causes add up to."
        ),
        contributing_domains=["finance"],
        evidence=[
            f"Revenue: Rs {fin.revenue.current_revenue:,.0f} "
            f"({decline:+.2f}% vs {fin.revenue.peak_month} peak)",
            f"Profit margin: {fin.profit.current_margin_percent:.2f}% "
            f"vs {fin.profit.peak_margin_percent:.2f}% peak "
            f"({fin.profit.margin_compression_pp:.2f}pp compression)",
            f"Monthly trend: {fin.revenue.trend}",
        ],
    )


_ROOT_CAUSE_RULES = (
    _best_seller_stockout,
    _delivery_root_cause,
    _campaign_root_cause,
    _revenue_context_root_cause,
)


def _root_causes(bi: BIFacts, consulted: list[str]) -> list[RootCause]:
    causes = []
    for rule in _ROOT_CAUSE_RULES:
        cause = rule(bi)
        if cause is None:
            continue
        if any(d in consulted for d in cause.contributing_domains):
            causes.append(cause)
    return causes


def _reorder_action(bi: BIFacts) -> Optional[RecommendedAction]:
    inv = bi.inventory
    fin = bi.finance
    if inv is None or fin is None:
        return None

    top_skus = {p.sku for p in fin.top_revenue_products[:3]}
    for product in inv.products:
        if product.sku in top_skus and product.risk_level == "critical":
            revenue = next(
                (p.revenue for p in fin.top_revenue_products
                 if p.sku == product.sku),
                0.0,
            )
            days = (
                f"{product.days_of_stock_remaining:.2f} days"
                if product.days_of_stock_remaining is not None
                else "an unknown number of days"
            )
            return RecommendedAction(
                priority="urgent",
                title=f"Reorder {product.name} today",
                description=(
                    f"Place a reorder of {product.recommended_reorder_qty} "
                    f"units of {product.name} with the supplier immediately "
                    "to restore availability of the best-selling product."
                ),
                domain="inventory",
                agent_name=AGENT_NAMES["inventory"],
                evidence=[
                    f"Only {product.current_stock} units remain "
                    f"(about {days} of sales)",
                    f"Generates Rs {revenue:,.0f} of revenue — "
                    "the top seller",
                    f"Recommended reorder quantity: "
                    f"{product.recommended_reorder_qty} units",
                ],
                expected_impact=(
                    "Restores availability of the top revenue product "
                    "before it stocks out completely."
                ),
            )
    return None


def _delivery_action(bi: BIFacts) -> Optional[RecommendedAction]:
    sup = bi.support
    if sup is None or sup.top_theme != "delivery_problems":
        return None
    return RecommendedAction(
        priority="high",
        title="Fix the delivery process with the courier partner",
        description=(
            f"Investigate the courier delays behind the delivery "
            f"complaints, resolve the {sup.delivery.open_count} open "
            "delivery tickets, and agree a delivery SLA before the peak "
            "season."
        ),
        domain="support",
        agent_name=AGENT_NAMES["support"],
        evidence=[
            f"Delivery is the top complaint theme: "
            f"{sup.delivery.total_tickets} of "
            f"{sup.summary.total_tickets} tickets "
            f"({sup.delivery.share_percent}% of feedback)",
            f"Complaints up {sup.trend.complaints_change_percent:+.2f}% "
            "vs the prior period",
            f"Reported delays average "
            f"{sup.delivery.avg_reported_delay_days} days "
            f"(longest {sup.delivery.max_reported_delay_days})",
        ],
        expected_impact=(
            "Protects repeat purchases and stops the complaint surge from "
            "compounding."
        ),
    )


def _reallocation_action(bi: BIFacts) -> Optional[RecommendedAction]:
    mk = bi.marketing
    if mk is None or mk.reallocation is None:
        return None
    r = mk.reallocation
    to_roas = f" (ROAS {r.to_campaign_roas:g})" if r.to_campaign_roas else ""
    return RecommendedAction(
        priority="medium",
        title=(
            f"Move Rs {r.from_campaign_spend:,.0f} from "
            f"{r.from_campaign} to {r.to_campaign}"
        ),
        description=(
            f"Pause the underperforming {r.from_campaign} campaign and "
            f"shift its Rs {r.from_campaign_spend:,.0f} budget to "
            f"{r.to_campaign}{to_roas}, the best-performing campaign."
        ),
        domain="marketing",
        agent_name=AGENT_NAMES["marketing"],
        evidence=[
            f"{r.from_campaign} is the only campaign flagged as "
            "underperforming by the explainable rule",
            f"{r.to_campaign} has the best return on ad spend"
            + (f" (ROAS {r.to_campaign_roas:g})" if r.to_campaign_roas else ""),
            f"Budget to reallocate: Rs {r.from_campaign_spend:,.0f}",
        ],
        expected_impact=(
            "Improves the conversion efficiency of the ad budget without "
            "spending more."
        ),
    )


def _overstock_action(bi: BIFacts) -> Optional[RecommendedAction]:
    inv = bi.inventory
    if inv is None or inv.summary.overstock_count == 0:
        return None
    s = inv.summary
    return RecommendedAction(
        priority="medium",
        title="Clear overstocked inventory",
        description=(
            f"Run clearance pricing or bundle offers on the "
            f"{s.overstock_count} overstocked products to release the "
            "working capital tied up in slow-moving stock."
        ),
        domain="inventory",
        agent_name=AGENT_NAMES["inventory"],
        evidence=[
            f"{s.overstock_count} products are overstocked",
            f"Excess stock value: Rs {s.excess_stock_value_retail:,.0f} "
            "at retail price",
        ],
        expected_impact=(
            "Frees working capital and shelf space for faster-moving "
            "products."
        ),
    )


def _margin_action(bi: BIFacts) -> Optional[RecommendedAction]:
    fin = bi.finance
    if fin is None or fin.profit.margin_compression_pp < 2:
        return None
    p = fin.profit
    return RecommendedAction(
        priority="low",
        title="Review pricing and expenses to rebuild margin",
        description=(
            "Re-examine supplier costs, pricing, and the largest expense "
            "categories to restore the profit margin toward its peak."
        ),
        domain="finance",
        agent_name=AGENT_NAMES["finance"],
        evidence=[
            f"Margin is {p.current_margin_percent:.2f}% vs the "
            f"{p.peak_margin_percent:.2f}% peak "
            f"({p.margin_compression_pp:.2f}pp compression)",
            f"Largest expense category: {fin.expenses.top_category} at "
            f"Rs {fin.expenses.top_category_amount:,.0f}/month",
        ],
        expected_impact=(
            "Restores profitability as the revenue recovery actions take "
            "effect."
        ),
    )


_ACTION_RULES = (
    _reorder_action,
    _delivery_action,
    _reallocation_action,
    _overstock_action,
    _margin_action,
)


def _recommended_actions(
    bi: BIFacts, consulted: list[str]
) -> list[RecommendedAction]:
    actions = []
    for rule in _ACTION_RULES:
        action = rule(bi)
        if action is not None and action.domain in consulted:
            actions.append(action)
    actions.sort(key=lambda a: _PRIORITY_ORDER[a.priority])
    return actions


# ---------------------------------------------------------------------------
# Orchestration entry point
# ---------------------------------------------------------------------------

def get_ceo_answer_from_bi(bi: BIFacts, question: str) -> CEOAnswer:
    """Synthesize the CEO answer from an ALREADY-LOADED BI snapshot.

    Pure orchestration step (no DB access) — shared by the CEO Agent and
    the dashboard endpoint so both present the exact same grounded plan.
    """
    routed = route_question(question)
    available = set(bi.included_domains)

    routing: list[RoutingDecision] = []
    consulted: list[str] = []
    missing: list[str] = []
    for domain in routed:
        is_available = domain in available
        routing.append(RoutingDecision(
            domain=domain,
            agent_name=AGENT_NAMES[domain],
            reason=routed[domain],
            consulted=is_available,
        ))
        if is_available:
            consulted.append(domain)
        else:
            missing.append(domain)

    incomplete_reason: Optional[str] = None
    if missing:
        missing_names = ", ".join(AGENT_NAMES[d] for d in missing)
        incomplete_reason = (
            f"Analysis is incomplete: {missing_names} could not be "
            "consulted (data unavailable). The findings and actions above "
            "cover the remaining areas only."
        )

    return CEOAnswer(
        question=question,
        understood_as=_understood_as(question, routed),
        routing=routing,
        consulted_agents=[AGENT_NAMES[d] for d in consulted],
        missing_agents=[AGENT_NAMES[d] for d in missing],
        incomplete_analysis=bool(missing),
        incomplete_reason=incomplete_reason,
        health_score=bi.health_score,
        key_findings=_key_findings(bi, consulted),
        root_causes=_root_causes(bi, consulted),
        recommended_actions=_recommended_actions(bi, consulted),
    )


def get_ceo_answer(db: Session, question: str) -> CEOAnswer:
    """Route the question, gather the agents' findings, synthesize the plan.

    Raises BusinessNotFoundError when there is no business, and
    NoBIDataError when every agent failed (both mapped to HTTP 404).
    Single-domain failures degrade gracefully into an incomplete answer.
    """
    bi = get_bi_snapshot(db)
    return get_ceo_answer_from_bi(bi, question)


__all__ = [
    "get_ceo_answer",
    "get_ceo_answer_from_bi",
    "route_question",
    "understand_question",
    "BusinessNotFoundError",
    "NoBIDataError",
    "AGENT_NAMES",
]

"""
Deterministic customer support analysis service.

Counts every metric from the support_tickets table with code/database logic:
negative feedback percentage, recurring issue themes, delivery problems,
product complaints, and a recent-vs-prior trend. Ticket descriptions are
always preserved VERBATIM — nothing here rewrites, paraphrases, or invents
customer feedback.

The LLM is used ONLY to classify sentiment for tickets whose stored
sentiment is missing/invalid. If the LLM fails (or is not configured), a
deterministic heuristic classifies them instead. In both cases the
classification outcome is recorded per ticket (sentiment_source).

All percentages are rounded to 2 decimals once and reused everywhere so the
facts stay mutually consistent for the BI and CEO agents.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..models.business import Business, SupportTicket
from ..schemas.support import (
    DeliveryFacts,
    SupportFacts,
    SupportSummary,
    SupportTicketFact,
    SupportTrendFact,
    ThemeBreakdown,
)
from ..services import llm

# ---------------------------------------------------------------------------
# Configuration (explainable constants)
# ---------------------------------------------------------------------------

MIN_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 90

# A theme is "recurring" once at least this many tickets share it.
RECURRING_MIN_COUNT = 2

# Cap on verbatim sample quotes included in the facts.
MAX_SAMPLE_QUOTES = 5

VALID_SENTIMENTS = {"positive", "neutral", "negative"}

# Matches "Delivery delayed by 3 days" style reports (case-insensitive).
_DELAY_PATTERN = re.compile(r"delayed by\s+(\d+)\s+day", re.IGNORECASE)

# Keyword rules assign each ticket exactly ONE primary theme, in priority
# order: delivery -> wrong item -> quality -> inquiry -> other.
_DELIVERY_KEYWORDS = (
    "delayed by", "delivery delayed", "courier",
    "tracking", "no notification", "not received", "did not attempt",
)
_WRONG_ITEM_KEYWORDS = (
    "wrong size", "wrong item", "wrong color", "wrong colour", "instead of",
)
_QUALITY_KEYWORDS = (
    "quality", "fabric", "stitching", "loose",
    "damaged", "different from website", "color different", "colour different",
)

THEME_LABELS = {
    "delivery_problems": "Delivery problems",
    "wrong_item_fulfillment": "Wrong item / size / color",
    "product_quality": "Product quality",
    "general_inquiry": "General inquiries",
    "other": "Other",
}


class SupportDataError(Exception):
    """Base error for support data problems."""


class BusinessNotFoundError(SupportDataError):
    pass


class NoTicketDataError(SupportDataError):
    pass


class InvalidRangeError(SupportDataError):
    pass


# ---------------------------------------------------------------------------
# Theme detection (deterministic)
# ---------------------------------------------------------------------------

def _theme_of(ticket: SupportTicket) -> str:
    """Assign one primary theme from the ticket text, using fixed rules."""
    text = (ticket.description or "").lower()
    if any(k in text for k in _DELIVERY_KEYWORDS):
        return "delivery_problems"
    if any(k in text for k in _WRONG_ITEM_KEYWORDS):
        return "wrong_item_fulfillment"
    if any(k in text for k in _QUALITY_KEYWORDS):
        return "product_quality"
    if (ticket.ticket_type or "").lower() == "inquiry":
        return "general_inquiry"
    return "other"


def _heuristic_sentiment(ticket_type: str) -> str:
    """Deterministic sentiment fallback when the LLM cannot classify."""
    return "neutral" if (ticket_type or "").lower() == "inquiry" else "negative"


def _pct_change(new: int, old: int) -> Optional[float]:
    """Percent change; None when the prior value is zero (undefined)."""
    if old == 0:
        return None
    return round((new - old) / old * 100, 2)


# ---------------------------------------------------------------------------
# Sentiment completion (LLM only where data is missing)
# ---------------------------------------------------------------------------

def _complete_sentiments(records: list[dict]) -> None:
    """Fill sentiment for records that lack a valid stored value.

    ``records`` must already be sorted newest first; LLM labels are applied
    in that same order. Tries the LLM classifier first; any failure (not
    configured, network, timeout, malformed response, wrong length,
    unknown label) falls back to the deterministic heuristic. Never raises.
    """
    missing = [r for r in records if r["sentiment"] is None]
    if not missing:
        return

    labels = llm.classify_sentiments(
        [r["ticket"].description or "" for r in missing]
    )
    if labels is not None:
        for record, label in zip(missing, labels):
            record["sentiment"] = label
            record["source"] = "llm"
    else:
        for record in missing:
            record["sentiment"] = _heuristic_sentiment(
                record["ticket"].ticket_type
            )
            record["source"] = "heuristic"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def get_support_snapshot(db: Session, days: int = 30) -> SupportFacts:
    """Build the deterministic support facts for the default business."""
    if not (MIN_WINDOW_DAYS <= days <= MAX_WINDOW_DAYS):
        raise InvalidRangeError(
            f"days must be between {MIN_WINDOW_DAYS} and {MAX_WINDOW_DAYS}."
        )

    business = db.query(Business).first()
    if business is None:
        raise BusinessNotFoundError("No business found.")

    all_tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.business_id == business.id)
        .all()
    )
    if not all_tickets:
        raise NoTicketDataError("No customer feedback found for this business.")

    dated = [t for t in all_tickets if t.created_at is not None]
    if not dated:
        raise NoTicketDataError("Customer feedback has no timestamps.")

    as_of_date = max(t.created_at for t in dated).date()
    cutoff = as_of_date - timedelta(days=days - 1)
    tickets = [t for t in dated if t.created_at.date() >= cutoff]
    if not tickets:
        raise NoTicketDataError(
            f"No customer feedback in the last {days} days."
        )

    # --- enrich: theme + sentiment (stored / llm / heuristic) ------------
    records = []
    for ticket in tickets:
        stored = (ticket.sentiment or "").strip().lower()
        records.append({
            "ticket": ticket,
            "theme": _theme_of(ticket),
            "sentiment": stored if stored in VALID_SENTIMENTS else None,
            "source": "stored" if stored in VALID_SENTIMENTS else None,
        })

    # Sort newest first once; sentiment classification and every derived
    # list reuse this order.
    records.sort(key=lambda r: r["ticket"].created_at, reverse=True)

    _complete_sentiments(records)

    total = len(records)
    missing_count = sum(1 for r in records if r["source"] != "stored")
    llm_count = sum(1 for r in records if r["source"] == "llm")
    heuristic_count = sum(1 for r in records if r["source"] == "heuristic")

    by_type = {"complaint": 0, "inquiry": 0, "return": 0}
    by_sentiment = {"negative": 0, "neutral": 0, "positive": 0}
    open_count = 0
    resolved_count = 0
    for r in records:
        t = r["ticket"]
        by_type[(t.ticket_type or "").lower()] = by_type.get(
            (t.ticket_type or "").lower(), 0
        ) + 1
        by_sentiment[r["sentiment"]] = by_sentiment.get(r["sentiment"], 0) + 1
        if (t.status or "").lower() == "open":
            open_count += 1
        else:
            resolved_count += 1

    summary = SupportSummary(
        total_tickets=total,
        complaints=by_type.get("complaint", 0),
        inquiries=by_type.get("inquiry", 0),
        returns=by_type.get("return", 0),
        open=open_count,
        resolved=resolved_count,
        resolution_rate_percent=round(resolved_count / total * 100, 2),
        negative_count=by_sentiment.get("negative", 0),
        neutral_count=by_sentiment.get("neutral", 0),
        positive_count=by_sentiment.get("positive", 0),
        negative_feedback_percent=round(
            by_sentiment.get("negative", 0) / total * 100, 2
        ),
        sentiment_missing_count=missing_count,
        llm_classified_count=llm_count,
        heuristic_classified_count=heuristic_count,
    )

    # --- themes ------------------------------------------------------------
    themes: list[ThemeBreakdown] = []
    theme_keys = sorted({r["theme"] for r in records})
    for key in theme_keys:
        group = [r for r in records if r["theme"] == key]
        themes.append(ThemeBreakdown(
            theme=key,
            label=THEME_LABELS.get(key, key),
            count=len(group),
            share_percent=round(len(group) / total * 100, 2),
            negative_count=sum(1 for g in group if g["sentiment"] == "negative"),
            open_count=sum(
                1 for g in group if (g["ticket"].status or "").lower() == "open"
            ),
            example_description=group[0]["ticket"].description or "",
        ))
    themes.sort(key=lambda t: (-t.count, t.theme))
    recurring = [t for t in themes if t.count >= RECURRING_MIN_COUNT]
    top_theme = themes[0].theme if themes else None

    # --- delivery deep-dive -------------------------------------------------
    delivery_group = [r for r in records if r["theme"] == "delivery_problems"]
    delay_days: list[int] = []
    for r in delivery_group:
        match = _DELAY_PATTERN.search(r["ticket"].description or "")
        if match:
            delay_days.append(int(match.group(1)))
    delivery = DeliveryFacts(
        total_tickets=len(delivery_group),
        share_percent=round(len(delivery_group) / total * 100, 2),
        open_count=sum(
            1 for r in delivery_group
            if (r["ticket"].status or "").lower() == "open"
        ),
        delay_reports=len(delay_days),
        avg_reported_delay_days=(
            round(sum(delay_days) / len(delay_days), 2) if delay_days else None
        ),
        max_reported_delay_days=max(delay_days) if delay_days else None,
    )

    # --- trend: recent half vs prior half of the window ---------------------
    half = max(days // 2, 1)
    recent_cutoff = as_of_date - timedelta(days=half - 1)
    recent = [
        r for r in records if r["ticket"].created_at.date() >= recent_cutoff
    ]
    prior = [
        r for r in records if r["ticket"].created_at.date() < recent_cutoff
    ]

    def _count(rows: list[dict], predicate) -> int:
        return sum(1 for r in rows if predicate(r))

    trend = SupportTrendFact(
        recent_complaints=_count(
            recent, lambda r: (r["ticket"].ticket_type or "").lower() == "complaint"
        ),
        prior_complaints=_count(
            prior, lambda r: (r["ticket"].ticket_type or "").lower() == "complaint"
        ),
        recent_delivery_issues=_count(
            recent, lambda r: r["theme"] == "delivery_problems"
        ),
        prior_delivery_issues=_count(
            prior, lambda r: r["theme"] == "delivery_problems"
        ),
    )
    trend.complaints_change_percent = _pct_change(
        trend.recent_complaints, trend.prior_complaints
    )
    trend.delivery_change_percent = _pct_change(
        trend.recent_delivery_issues, trend.prior_delivery_issues
    )

    # --- tickets (originals preserved) + verbatim sample quotes -------------
    ticket_facts = [
        SupportTicketFact(
            id=r["ticket"].id,
            customer_name=r["ticket"].customer_name or "",
            ticket_type=r["ticket"].ticket_type or "",
            status=r["ticket"].status or "",
            sentiment=r["sentiment"],
            sentiment_source=r["source"],
            channel=r["ticket"].channel or "",
            theme=r["theme"],
            description=r["ticket"].description or "",
            created_at=r["ticket"].created_at,
            resolved_at=r["ticket"].resolved_at,
            age_days=(
                (as_of_date - r["ticket"].created_at.date()).days
                if (r["ticket"].status or "").lower() == "open"
                else None
            ),
        )
        for r in records
    ]
    sample_quotes = [
        r["ticket"].description or ""
        for r in records
        if r["sentiment"] == "negative"
    ][:MAX_SAMPLE_QUOTES]

    return SupportFacts(
        business_name=business.name,
        currency=business.currency or "PKR",
        as_of_date=as_of_date.isoformat(),
        window_days=days,
        summary=summary,
        themes=themes,
        recurring_issues=recurring,
        top_theme=top_theme,
        delivery=delivery,
        trend=trend,
        tickets=ticket_facts,
        sample_negative_feedback=sample_quotes,
    )


# Re-exported for the API layer's error handling.
__all__ = [
    "get_support_snapshot",
    "BusinessNotFoundError",
    "NoTicketDataError",
    "InvalidRangeError",
    "MIN_WINDOW_DAYS",
    "MAX_WINDOW_DAYS",
]

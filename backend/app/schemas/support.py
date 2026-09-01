"""Pydantic schemas for the Customer Support Agent.

All numbers are computed deterministically by app/services/support.py.
Ticket descriptions are preserved verbatim so downstream agents (BI, CEO)
and the dashboard never see fabricated feedback.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SupportTicketFact(BaseModel):
    """One support ticket with its deterministic theme and sentiment.

    ``description`` is the ORIGINAL customer feedback, stored verbatim.
    ``sentiment_source`` is one of: stored (already in DB), llm
    (classified by the LLM), heuristic (deterministic fallback).
    """

    id: int
    customer_name: str
    ticket_type: str
    status: str
    sentiment: str
    sentiment_source: str
    channel: str
    theme: str
    description: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    age_days: Optional[int] = None  # only for open tickets


class ThemeBreakdown(BaseModel):
    """A recurring customer issue theme with deterministic counts."""

    theme: str
    label: str
    count: int
    share_percent: float
    negative_count: int
    open_count: int
    example_description: str  # verbatim, from the most recent ticket in theme


class DeliveryFacts(BaseModel):
    """Deep-dive on delivery problems (the demo story's main pain point)."""

    total_tickets: int
    share_percent: float
    open_count: int
    delay_reports: int  # tickets with an explicit "delayed by N days" figure
    avg_reported_delay_days: Optional[float] = None
    max_reported_delay_days: Optional[int] = None


class SupportTrendFact(BaseModel):
    """Comparison of the recent half vs prior half of the analysis window."""

    recent_complaints: int
    prior_complaints: int
    complaints_change_percent: Optional[float] = None
    recent_delivery_issues: int
    prior_delivery_issues: int
    delivery_change_percent: Optional[float] = None


class SupportSummary(BaseModel):
    """Headline counts for the dashboard and CEO Agent."""

    total_tickets: int
    complaints: int
    inquiries: int
    returns: int
    open: int
    resolved: int
    resolution_rate_percent: float
    negative_count: int
    neutral_count: int
    positive_count: int
    negative_feedback_percent: float
    sentiment_missing_count: int  # tickets that had no stored sentiment
    llm_classified_count: int
    heuristic_classified_count: int


class SupportFacts(BaseModel):
    """Structured facts consumed by the BI and CEO agents."""

    business_name: str
    currency: str
    as_of_date: str  # ISO date of the most recent ticket
    window_days: int
    summary: SupportSummary
    themes: List[ThemeBreakdown]
    recurring_issues: List[ThemeBreakdown]  # themes with count >= 2
    top_theme: Optional[str] = None
    delivery: DeliveryFacts
    trend: SupportTrendFact
    tickets: List[SupportTicketFact]  # originals preserved, newest first
    sample_negative_feedback: List[str]  # verbatim quotes, newest first


class SupportAnalysisResponse(BaseModel):
    """Full response of GET /api/support/analysis."""

    agent: str
    facts: SupportFacts
    interpretation: str
    interpretation_source: str  # "llm" | "fallback"
    generated_at: str

"""
Marketing Agent schemas — structured campaign performance facts.

Design rule (same as Finance/Inventory agents): every numeric field here
is computed by deterministic code (app/services/marketing.py) from
database records. The LLM never produces campaign metrics; it only
receives these facts and may explain them or suggest actions.

Explainable underperformance rule (evaluated by code, never by the LLM):
a campaign is flagged when its conversion rate falls below 50% of the
cross-campaign benchmark (total conversions / total clicks), or its cost
per conversion exceeds 150% of the benchmark (total spend / total
conversions), or it recorded zero conversions from tracked clicks.
"""

from pydantic import BaseModel
from typing import List, Optional


class CampaignPerformanceFact(BaseModel):
    """Performance metrics for one marketing campaign."""
    name: str
    channel: str
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    # Raw campaign data (as recorded in the database)
    spend: float
    impressions: int
    clicks: int
    conversions: int
    revenue_generated: float
    # Computed metrics (None when the denominator is zero/invalid)
    ctr_percent: Optional[float]                 # clicks / impressions * 100
    conversion_rate_percent: Optional[float]     # conversions / clicks * 100
    cost_per_conversion: Optional[float]         # spend / conversions
    cost_per_click: Optional[float]              # spend / clicks
    roas: Optional[float]                        # revenue / spend
    roi_percent: Optional[float]                 # (revenue - spend) / spend * 100
    # Classification by deterministic rules
    performance: str          # underperforming|acceptable|outperforming|insufficient_data|invalid_data
    reason: str               # deterministic explanation quoting computed numbers


class MarketingBenchmark(BaseModel):
    """Cross-campaign benchmark computed from all valid campaigns."""
    campaign_count: int
    valid_campaign_count: int
    invalid_campaign_count: int
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_revenue_generated: float
    conversion_rate_percent: float           # weighted: conversions / clicks * 100
    cost_per_conversion: Optional[float]     # total spend / conversions (None if 0 conversions)
    overall_ctr_percent: float               # clicks / impressions * 100
    overall_roas: Optional[float]            # revenue / spend


class ReallocationRecommendation(BaseModel):
    """Deterministic budget reallocation suggestion (problem → opportunity)."""
    from_campaign: str
    from_campaign_spend: float
    to_campaign: str
    to_campaign_roas: Optional[float]
    to_campaign_cost_per_conversion: Optional[float]
    rationale: str


class ProductMarketingFact(BaseModel):
    """Product performance relevant to marketing decisions."""
    name: str
    sku: str
    category: str
    revenue: float
    units_sold: int
    trend: str
    stock_qty: int
    note: str


class ProductMarketingHighlights(BaseModel):
    """Product views a marketer can act on (promote / fix / clear)."""
    top_performers: List[ProductMarketingFact]      # strongest revenue — scale winners
    declining: List[ProductMarketingFact]           # high revenue, falling — promotion candidates
    weak_sellers: List[ProductMarketingFact]        # minimal sales — clearance candidates


class MarketingFacts(BaseModel):
    """Complete, deterministic marketing picture. Suitable for the
    dashboard and for consumption by the CEO Agent."""
    business_name: str
    currency: str
    benchmark: MarketingBenchmark
    campaigns: List[CampaignPerformanceFact]         # sorted: problems first
    underperforming_campaign_names: List[str]
    best_campaign_name: Optional[str] = None
    reallocation: Optional[ReallocationRecommendation] = None
    product_highlights: ProductMarketingHighlights


class MarketingAnalysisResponse(BaseModel):
    """Full Marketing Agent response: verified facts + plain-language
    interpretation (LLM or deterministic fallback)."""
    agent: str
    facts: MarketingFacts
    interpretation: str
    interpretation_source: str      # "llm" | "fallback"
    generated_at: str

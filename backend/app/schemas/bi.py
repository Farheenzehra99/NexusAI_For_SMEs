"""Pydantic schemas for the BI Agent.

The Business Health Score is computed by app/services/bi.py using a
documented, deterministic, weighted formula (see that module's docstring
for the full formula). The LLM NEVER calculates or adjusts the score —
it only receives the already-computed result and may explain it.

BI does not invent raw business facts: every number in BIFacts comes
verbatim from the Finance, Inventory, Marketing, and Customer Support
snapshots produced by their deterministic services. The nested domain
facts are embedded so the CEO Agent and the dashboard get ONE coherent
picture.
"""

from typing import List, Optional

from pydantic import BaseModel

from .finance import FinanceFacts
from .inventory import InventoryFacts
from .marketing import MarketingFacts
from .support import SupportFacts


class ScoreComponent(BaseModel):
    """One documented rule applied to a domain sub-score."""

    rule: str        # documented rule identifier, e.g. "revenue_decline_from_peak"
    points: float    # points applied (negative = deduction, positive = bonus)
    reason: str      # quotes the exact computed inputs


class DomainScore(BaseModel):
    """Sub-score for one business domain on the 0-100 scale."""

    domain: str              # finance|inventory|marketing|support
    label: str               # human-readable domain name
    score: int               # 0-100 (rounded half-up)
    weight: float            # effective weight after re-normalization
    data_available: bool
    components: List[ScoreComponent]


class KeySignal(BaseModel):
    """A business-level signal extracted from one domain's findings."""

    domain: str              # finance|inventory|marketing|support|bi
    label: str
    value: str               # exact computed value, formatted
    direction: str           # positive|negative|neutral


class HealthScore(BaseModel):
    """The documented composite Business Health Score."""

    score: int               # 0-100
    risk_level: str          # low|moderate|high|critical
    formula: str             # human-readable weighted formula
    domain_scores: List[DomainScore]
    weakest_domain: Optional[str] = None
    strongest_domain: Optional[str] = None


class BIFacts(BaseModel):
    """One coherent business picture assembled from the four agents'
    findings — suitable for the dashboard and the CEO Agent."""

    business_name: str
    currency: str
    as_of_date: Optional[str] = None
    included_domains: List[str]
    missing_domains: List[str]
    health_score: HealthScore
    key_signals: List[KeySignal]
    # The underlying agent findings, embedded verbatim (never re-derived).
    finance: Optional[FinanceFacts] = None
    inventory: Optional[InventoryFacts] = None
    marketing: Optional[MarketingFacts] = None
    support: Optional[SupportFacts] = None


class BIAnalysisResponse(BaseModel):
    """Full BI Agent response: computed score + plain-language explanation
    (LLM or deterministic fallback)."""

    agent: str
    facts: BIFacts
    interpretation: str
    interpretation_source: str      # "llm" | "fallback"
    generated_at: str

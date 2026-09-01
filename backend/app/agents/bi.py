"""
BI Agent — one understandable business-level picture.

Layering (same pattern as the other agents, with one difference: BI does
not query the database directly — it consumes the four domain agents'
snapshots and never re-derives or invents raw business facts):
    1. app/services/bi.py — the Business Health Score: a documented,
       deterministic, weighted formula over the Finance, Inventory,
       Marketing, and Customer Support snapshots (weights 35/25/20/20,
       re-normalized when a domain's data is unavailable)
    2. app/services/llm.py — optional plain-language explanation of the
                             ALREADY-COMPUTED score; the LLM is strictly
                             forbidden from computing or adjusting it
    3. this module         — orchestrates 1 + 2 and guarantees a valid
                             BIAnalysisResponse even when the LLM fails
                             (deterministic fallback)
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .base import BaseAgent, register_agent
from ..schemas.bi import BIFacts, BIAnalysisResponse
from ..services.bi import get_bi_snapshot
from ..services import llm


# Deterministic "most important action" per weakest domain (facts-driven).
_WEAKNESS_ACTIONS = {
    "support": (
        "resolve the open delivery complaints with the courier partner "
        "to stop the complaint surge"
    ),
    "finance": (
        "arrest the revenue decline — review pricing, best-seller stock "
        "availability, and spending"
    ),
    "inventory": (
        "reorder the critical stock items and plan clearance for the "
        "overstocked products"
    ),
    "marketing": (
        "reallocate budget from the underperforming campaign to the best "
        "performer"
    ),
}


class BIAgent(BaseAgent):
    name = "BI Agent"
    role = "Business Intelligence Analyst"
    description = (
        "Combines the Finance, Inventory, Marketing, and Customer Support "
        "findings into one Business Health Score (0-100) using a "
        "documented, deterministic formula, and surfaces the key business "
        "signals behind it."
    )
    icon = "chart"
    color = "blue"

    def tasks(self) -> list[str]:
        return [
            "Business Health Score computation",
            "Risk level assessment",
            "Cross-agent signal aggregation",
            "Business-level explanation",
        ]

    # ── Core analysis ──────────────────────────────────────────────────────

    def analyze(self, db: Session) -> BIAnalysisResponse:
        """Produce the full BI Agent response."""
        facts = get_bi_snapshot(db)

        interpretation, source = self._interpret(facts)

        return BIAnalysisResponse(
            agent=self.name,
            facts=facts,
            interpretation=interpretation,
            interpretation_source=source,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _interpret(self, facts: BIFacts) -> tuple[str, str]:
        """LLM interpretation with safe deterministic fallback."""
        llm_text = llm.interpret_bi_facts(facts)
        if llm_text:
            return llm_text, "llm"
        return self._fallback_interpretation(facts), "fallback"

    # ── Deterministic fallback (facts-only, no invented numbers) ───────────

    @staticmethod
    def _fallback_interpretation(facts: BIFacts) -> str:
        hs = facts.health_score
        parts: list[str] = []

        # Headline: the computed score and its formula
        parts.append(
            f"Business Health Score: {hs.score}/100 — {hs.risk_level} "
            f"risk. Formula: {hs.formula}."
        )

        # Weakest and strongest domains
        by_domain = {ds.domain: ds for ds in hs.domain_scores}
        if hs.weakest_domain and hs.strongest_domain:
            w = by_domain[hs.weakest_domain]
            s = by_domain[hs.strongest_domain]
            parts.append(
                f"Weakest area: {w.label} ({w.score}/100); strongest: "
                f"{s.label} ({s.score}/100)."
            )

        # Biggest warnings: one negative signal per domain (deterministic)
        negatives = []
        seen_domains: set[str] = set()
        for sig in facts.key_signals:
            if sig.direction == "negative" and sig.domain not in seen_domains:
                negatives.append(sig)
                seen_domains.add(sig.domain)
        if negatives:
            listed = "; ".join(
                f"{sig.label} — {sig.value}" for sig in negatives
            )
            parts.append(f"Biggest warnings: {listed}.")

        # Single most important action, driven by the weakest domain
        action = _WEAKNESS_ACTIONS.get(
            hs.weakest_domain,
            "review the flagged warnings with the business owner",
        )
        parts.append(f"Most important action: {action}.")

        return " ".join(parts)


register_agent(BIAgent())

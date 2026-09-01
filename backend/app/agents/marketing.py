"""
Marketing Agent — reliable campaign performance facts for the business.

Layering (same pattern as the Finance and Inventory agents):
    1. app/services/marketing.py — ALL deterministic calculations
       (CTR, conversion rate, cost per conversion, ROAS, benchmark,
       explainable underperformance rule, reallocation suggestion)
    2. app/services/llm.py       — optional plain-language explanation of
                                   already-computed facts (never calculates
                                   or invents campaign metrics)
    3. this module               — orchestrates 1 + 2 and guarantees a valid
                                   MarketingAnalysisResponse even when the
                                   LLM fails (deterministic fallback)

The LLM never produces campaign metrics. If it is unavailable,
unconfigured, slow, or erroring, the agent answers with a template built
exclusively from the computed facts.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .base import BaseAgent, register_agent
from ..schemas.marketing import MarketingFacts, MarketingAnalysisResponse
from ..services.marketing import get_marketing_snapshot
from ..services import llm


class MarketingAgent(BaseAgent):
    name = "Marketing Agent"
    role = "Growth Strategist"
    description = (
        "Analyzes campaign spend, conversions, and costs using deterministic "
        "calculations, flags underperformers with explainable rules, and "
        "suggests budget reallocation."
    )
    icon = "megaphone"
    color = "gold"

    def tasks(self) -> list[str]:
        return [
            "Campaign performance analysis",
            "Cost per conversion tracking",
            "Underperforming campaign detection",
            "Budget reallocation recommendations",
            "Promotion opportunity identification",
        ]

    # ── Core analysis ──────────────────────────────────────────────────────

    def analyze(self, db: Session) -> MarketingAnalysisResponse:
        """Produce the full Marketing Agent response."""
        facts = get_marketing_snapshot(db)

        interpretation, source = self._interpret(facts)

        return MarketingAnalysisResponse(
            agent=self.name,
            facts=facts,
            interpretation=interpretation,
            interpretation_source=source,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _interpret(self, facts: MarketingFacts) -> tuple[str, str]:
        """LLM interpretation with safe deterministic fallback."""
        llm_text = llm.interpret_marketing_facts(facts)
        if llm_text:
            return llm_text, "llm"
        return self._fallback_interpretation(facts), "fallback"

    # ── Deterministic fallback (facts-only, no invented numbers) ───────────

    @staticmethod
    def _fallback_interpretation(facts: MarketingFacts) -> str:
        b = facts.benchmark
        parts: list[str] = []

        # Overall performance
        cpc_sentence = (
            f"at an average Rs {b.cost_per_conversion:,.2f} per conversion"
            if b.cost_per_conversion is not None
            else "with no conversions recorded"
        )
        roas_sentence = (
            f" for Rs {b.total_revenue_generated:,.0f} in attributed revenue "
            f"(ROAS {b.overall_roas})"
            if b.overall_roas is not None
            else ""
        )
        parts.append(
            f"Marketing spent Rs {b.total_spend:,.0f} across {b.campaign_count} "
            f"campaigns, generating {b.total_conversions:,} conversions from "
            f"{b.total_clicks:,} clicks {cpc_sentence}{roas_sentence}."
        )

        # Underperformers
        if facts.underperforming_campaign_names:
            worst = facts.campaigns[0]  # sorted: problems first
            parts.append(
                f"Underperforming: {', '.join(facts.underperforming_campaign_names)}. "
                f"{worst.reason}"
            )
        else:
            parts.append("No campaigns are currently flagged as underperforming.")

        # Opportunity / reallocation
        if facts.reallocation:
            r = facts.reallocation
            parts.append(
                f"Best opportunity: {facts.best_campaign_name} (ROAS "
                f"{r.to_campaign_roas}, Rs {r.to_campaign_cost_per_conversion:,.2f} "
                f"per conversion). Recommended: move the Rs "
                f"{r.from_campaign_spend:,.0f} budget from {r.from_campaign} "
                f"to {r.to_campaign}."
            )

        # Product tie-in
        top = facts.product_highlights.top_performers
        if top:
            t = top[0]
            parts.append(f"Product note: {t.name} — {t.note}.")

        return " ".join(parts)


register_agent(MarketingAgent())

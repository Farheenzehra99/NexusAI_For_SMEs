"""
Inventory Agent — reliable inventory risk facts for the business.

Layering (same pattern as the Finance Agent):
    1. app/services/inventory.py — ALL deterministic calculations
       (stock, velocity, days of cover, risk level, reorder quantity)
    2. app/services/llm.py       — optional plain-language explanation of
                                   already-computed facts (never calculates)
    3. this module               — orchestrates 1 + 2 and guarantees a valid
                                   InventoryAnalysisResponse even when the
                                   LLM fails (deterministic fallback)

The LLM never produces stock numbers. If it is unavailable, unconfigured,
slow, or erroring, the agent answers with a template built exclusively
from the computed facts.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .base import BaseAgent, register_agent
from ..schemas.inventory import InventoryFacts, InventoryAnalysisResponse
from ..services.inventory import get_inventory_snapshot
from ..services import llm


class InventoryAgent(BaseAgent):
    name = "Inventory Agent"
    role = "Supply Chain Manager"
    description = (
        "Tracks stock levels, sales velocity, and reorder needs using "
        "deterministic calculations, and explains the verified numbers in "
        "plain language."
    )
    icon = "package"
    color = "purple"

    def tasks(self) -> list[str]:
        return [
            "Stock monitoring",
            "Sales velocity analysis",
            "Stock-out risk detection",
            "Reorder quantity calculation",
            "Overstock identification",
        ]

    # ── Core analysis ──────────────────────────────────────────────────────

    def analyze(self, db: Session, days: int = 30, business_id: int | None = None) -> InventoryAnalysisResponse:
        """Produce the full Inventory Agent response.

        Args:
            db: database session.
            days: velocity window in days (7-90).
            business_id: scope to authenticated business.
        """
        facts = get_inventory_snapshot(db, days=days, business_id=business_id)

        interpretation, source = self._interpret(facts)

        return InventoryAnalysisResponse(
            agent=self.name,
            facts=facts,
            interpretation=interpretation,
            interpretation_source=source,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _interpret(self, facts: InventoryFacts) -> tuple[str, str]:
        """LLM interpretation with safe deterministic fallback."""
        llm_text = llm.interpret_inventory_facts(facts)
        if llm_text:
            return llm_text, "llm"
        return self._fallback_interpretation(facts), "fallback"

    # ── Deterministic fallback (facts-only, no invented numbers) ───────────

    @staticmethod
    def _fallback_interpretation(facts: InventoryFacts) -> str:
        s = facts.summary
        parts: list[str] = []

        # Stock-out risks first
        stockout_risks = [
            r for r in facts.risks
            if r.risk_level in ("critical", "high", "medium", "out_of_stock")
        ]
        if stockout_risks:
            top = stockout_risks[0]
            parts.append(
                f"Urgent: {top.product} — {top.reason} "
                f"Recommended reorder: {top.recommended_reorder_qty} units."
            )
        else:
            parts.append("No stock-out risks detected in the current window.")

        # Overstock / dead stock — highlight the largest excess (most capital tied up)
        overstock = [r for r in facts.risks if r.risk_level == "overstock"]
        if overstock:
            worst = max(overstock, key=lambda r: r.excess_stock_qty)
            parts.append(
                f"On the other side, {worst.product} — {worst.reason} "
                f"Consider clearance pricing or bundles."
            )
        stagnant = [r for r in facts.risks if r.risk_level == "stagnant"]
        if stagnant:
            parts.append(
                f"{len(stagnant)} product(s) had no sales at all in the last "
                f"{facts.velocity_window_days} days."
            )

        # Portfolio summary
        parts.append(
            f"Across {s.total_active_products} active products, {s.at_risk_count} "
            f"face stock-out risk and {s.overstock_count} are overstocked. "
            f"Inventory holds Rs {s.total_stock_value_retail:,.0f} at retail value, "
            f"with Rs {s.excess_stock_value_retail:,.0f} sitting in excess stock."
        )
        if s.recommended_reorder_units > 0:
            parts.append(
                f"Total recommended reorder: {s.recommended_reorder_units} units "
                f"(about Rs {s.recommended_reorder_cost:,.0f} at cost)."
            )

        return " ".join(parts)


register_agent(InventoryAgent())

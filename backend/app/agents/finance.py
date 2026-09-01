"""
Finance Agent — reliable financial facts for the business.

Layering (per the approved specification):
    1. app/services/finance.py  — ALL deterministic calculations (code + DB)
    2. app/services/llm.py      — optional plain-language explanation of
                                  already-computed facts (never calculates)
    3. this module              — orchestrates 1 + 2 and guarantees a valid
                                  FinanceAnalysisResponse even when the LLM
                                  fails (deterministic fallback template)

The LLM never produces numbers. If it is unavailable, unconfigured, slow,
or erroring, the agent answers with a template built exclusively from the
computed facts.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .base import BaseAgent, register_agent
from ..schemas.finance import FinanceFacts, FinanceAnalysisResponse
from ..services.finance import get_financial_snapshot
from ..services import llm


class FinanceAgent(BaseAgent):
    name = "Finance Agent"
    role = "Financial Analyst"
    description = (
        "Monitors revenue, expenses, profit, and margins using deterministic "
        "calculations, and explains the verified numbers in plain language."
    )
    icon = "calculator"
    color = "blue"

    def tasks(self) -> list[str]:
        return [
            "P&L analysis",
            "Expense breakdown",
            "Profit margin tracking",
            "Financial anomaly detection",
            "Cash flow monitoring",
        ]

    # ── Core analysis ──────────────────────────────────────────────────────

    def analyze(self, db: Session, months: int = 6) -> FinanceAnalysisResponse:
        """Produce the full Finance Agent response for the last `months` months."""
        facts = get_financial_snapshot(db, months=months)

        interpretation, source = self._interpret(facts)

        return FinanceAnalysisResponse(
            agent=self.name,
            facts=facts,
            interpretation=interpretation,
            interpretation_source=source,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _interpret(self, facts: FinanceFacts) -> tuple[str, str]:
        """LLM interpretation with safe deterministic fallback."""
        llm_text = llm.interpret_finance_facts(facts)
        if llm_text:
            return llm_text, "llm"
        return self._fallback_interpretation(facts), "fallback"

    # ── Deterministic fallback (facts-only, no invented numbers) ───────────

    @staticmethod
    def _fallback_interpretation(facts: FinanceFacts) -> str:
        r = facts.revenue
        p = facts.profit
        e = facts.expenses

        parts: list[str] = []

        # Revenue paragraph
        rev_sentence = (
            f"Revenue in {r.current_month} was Rs {r.current_revenue:,.0f}"
        )
        if r.change_percent is not None:
            direction = "up" if r.change_percent >= 0 else "down"
            rev_sentence += f", {direction} {abs(r.change_percent):.1f}% from {r.previous_month}"
        rev_sentence += (
            f", but {abs(r.decline_from_peak_percent):.1f}% below the {r.peak_month} "
            f"peak of Rs {r.peak_revenue:,.0f}. The overall trend is {r.trend}."
        )
        parts.append(rev_sentence)

        # Profit & margin paragraph
        profit_sentence = (
            f"Profit was Rs {p.current_profit:,.0f} at a {p.current_margin_percent:.1f}% margin, "
            f"compressed {p.margin_compression_pp:.1f} percentage points from the "
            f"{p.peak_margin_month} peak of {p.peak_margin_percent:.1f}%. "
            f"Operating expenses in {e.month} totaled Rs {e.total:,.0f}, "
            f"led by {e.top_category} at Rs {e.top_category_amount:,.0f}."
        )
        parts.append(profit_sentence)

        # Products paragraph
        if facts.top_revenue_products:
            top = facts.top_revenue_products[0]
            product_sentence = (
                f"The top revenue product is {top.name} "
                f"(Rs {top.revenue:,.0f}, {top.revenue_share_percent:.1f}% of product revenue, "
                f"{top.units_sold} units sold)."
            )
            if facts.weak_products:
                names = ", ".join(w.name for w in facts.weak_products[:3])
                product_sentence += (
                    f" {len(facts.weak_products)} products sold fewer than "
                    f"20 units, including {names}."
                )
            parts.append(product_sentence)

        # Anomalies paragraph
        if facts.unusual_changes:
            top_anomaly = facts.unusual_changes[0]
            parts.append(
                f"Most important issue: {top_anomaly.description} "
                f"Recommended action: focus on restoring the top revenue drivers."
            )
        else:
            parts.append("No unusual financial changes were detected in this period.")

        return " ".join(parts)


register_agent(FinanceAgent())

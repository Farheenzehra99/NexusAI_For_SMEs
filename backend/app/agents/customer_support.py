"""
Customer Support Agent — reliable customer problem facts for the business.

Layering (same pattern as the Finance, Inventory, and Marketing agents):
    1. app/services/support.py — ALL deterministic calculations (negative
       feedback percentage, recurring issue themes, delivery problems,
       product complaints, recent-vs-prior trend) plus LLM sentiment
       classification ONLY for tickets whose stored sentiment is missing
    2. app/services/llm.py     — optional plain-language explanation of
                                 already-computed facts; never invents
                                 feedback or metrics
    3. this module             — orchestrates 1 + 2 and guarantees a valid
                                 SupportAnalysisResponse even when the LLM
                                 fails (deterministic fallback)

Original customer feedback is preserved verbatim everywhere. Nothing in
this agent rewrites, paraphrases, or fabricates what customers said.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .base import BaseAgent, register_agent
from ..schemas.support import SupportFacts, SupportAnalysisResponse
from ..services.support import get_support_snapshot
from ..services import llm


class CustomerSupportAgent(BaseAgent):
    name = "Customer Support Agent"
    role = "Customer Experience Lead"
    description = (
        "Analyzes customer feedback with deterministic counting, tracks "
        "negative sentiment, recurring issues, and delivery problems, and "
        "preserves the original customer words verbatim."
    )
    icon = "headset"
    color = "rose"

    def tasks(self) -> list[str]:
        return [
            "Negative feedback tracking",
            "Recurring issue detection",
            "Delivery problem analysis",
            "Sentiment classification",
        ]

    # ── Core analysis ──────────────────────────────────────────────────────

    def analyze(self, db: Session, days: int = 30) -> SupportAnalysisResponse:
        """Produce the full Customer Support Agent response."""
        facts = get_support_snapshot(db, days=days)

        interpretation, source = self._interpret(facts)

        return SupportAnalysisResponse(
            agent=self.name,
            facts=facts,
            interpretation=interpretation,
            interpretation_source=source,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _interpret(self, facts: SupportFacts) -> tuple[str, str]:
        """LLM interpretation with safe deterministic fallback."""
        llm_text = llm.interpret_support_facts(facts)
        if llm_text:
            return llm_text, "llm"
        return self._fallback_interpretation(facts), "fallback"

    # ── Deterministic fallback (facts-only, no invented feedback) ──────────

    @staticmethod
    def _fallback_interpretation(facts: SupportFacts) -> str:
        s = facts.summary
        d = facts.delivery
        t = facts.trend
        parts: list[str] = []

        # Headline: negative feedback percentage
        parts.append(
            f"Customer feedback in the last {facts.window_days} days: "
            f"{s.total_tickets} tickets, {s.negative_feedback_percent}% "
            f"negative ({s.negative_count} of {s.total_tickets}), with "
            f"{s.open} still open."
        )

        # Trend (recent half vs prior half of the window)
        if t.complaints_change_percent is not None:
            direction = "up" if t.complaints_change_percent > 0 else "down"
            parts.append(
                f"Complaints are {direction}: {t.prior_complaints} in the "
                f"earlier half of the window vs {t.recent_complaints} in the "
                f"more recent half ({t.complaints_change_percent:+.2f}%)."
            )
        elif t.prior_complaints == 0:
            parts.append(
                f"Complaints: {t.recent_complaints} in the recent half of "
                "the window, with no complaints recorded earlier."
            )

        # Top recurring issue (usually delivery in the demo story)
        if facts.recurring_issues:
            top = facts.recurring_issues[0]
            parts.append(
                f"Top recurring issue: {top.label} — {top.count} tickets "
                f"({top.share_percent}% of feedback), {top.open_count} "
                "still open."
            )

        # Delivery deep-dive with verbatim example
        if d.total_tickets > 0:
            delay_sentence = ""
            if d.avg_reported_delay_days is not None:
                delay_sentence = (
                    f" Reported delays average {d.avg_reported_delay_days} "
                    f"days (longest {d.max_reported_delay_days} days)."
                )
            delivery_theme = next(
                (th for th in facts.themes if th.theme == "delivery_problems"),
                None,
            )
            example = delivery_theme.example_description if delivery_theme else ""
            quote = f' One customer wrote: "{example}".' if example else ""
            parts.append(
                f"Delivery problems account for {d.total_tickets} tickets "
                f"({d.share_percent}% of feedback).{delay_sentence}{quote}"
            )

        # Sentiment classification transparency
        if s.sentiment_missing_count > 0:
            parts.append(
                f"{s.sentiment_missing_count} tickets had no stored "
                "sentiment; they were classified "
                + (
                    f"by the LLM ({s.llm_classified_count})"
                    if s.llm_classified_count > 0
                    else f"by keyword rules ({s.heuristic_classified_count})"
                )
                + ". Original wording is preserved unchanged."
            )

        # Single most important action
        if facts.top_theme == "delivery_problems":
            parts.append(
                "Most important action: fix the delivery process with the "
                "courier partner and clear the open delivery tickets first."
            )
        elif facts.recurring_issues:
            parts.append(
                f"Most important action: address the {facts.recurring_issues[0].label.lower()} "
                "problem first and resolve the open tickets."
            )
        else:
            parts.append(
                "Most important action: resolve the open tickets to keep "
                "customers satisfied."
            )

        return " ".join(parts)


register_agent(CustomerSupportAgent())

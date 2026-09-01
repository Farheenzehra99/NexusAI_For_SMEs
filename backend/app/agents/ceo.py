"""
CEO Agent — the orchestration layer of the AI workforce.

Layering (same pattern as the other agents):
    1. app/services/ceo.py — deterministic routing (which agents are
       needed), gathering (the BI snapshot aggregates the four domain
       agents' findings and the Business Health Score), and synthesis
       (key findings, root causes, and a prioritized action plan built
       ONLY from the agents' structured outputs)
    2. app/services/llm.py — optional plain-language narration of the
                             ALREADY-COMPUTED plan; strictly forbidden
                             from inventing findings, actions, or numbers
    3. this module         — orchestrates 1 + 2, records the
       collaboration as agent activity rows for the UI, and guarantees a
       valid CEOAnalysisResponse even when the LLM fails

Partial failure is handled in the service layer: if one specialized
agent's data is unavailable, the remaining agents' results are preserved
and the answer is flagged incomplete. Activity recording is best-effort
and NEVER fails the response.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .base import BaseAgent, register_agent
from ..models.business import AgentActivity, Business
from ..schemas.ceo import CEOAnswer, CEOAnalysisResponse
from ..services.ceo import get_ceo_answer
from ..services import llm


class CEOAgent(BaseAgent):
    name = "CEO Agent"
    role = "Chief Executive Officer"
    description = (
        "Answers the owner's business questions by routing them to the "
        "right specialized agents, combining their verified findings into "
        "a Business Health Score assessment, and producing a prioritized, "
        "evidence-backed action plan."
    )
    icon = "crown"
    color = "violet"

    def tasks(self) -> list[str]:
        return [
            "Question routing to specialized agents",
            "Cross-agent findings synthesis",
            "Root cause analysis",
            "Prioritized action planning",
        ]

    # ── Core analysis ──────────────────────────────────────────────────────

    def analyze(self, db: Session, question: str) -> CEOAnalysisResponse:
        """Produce the full CEO Agent response to the owner's question."""
        answer = get_ceo_answer(db, question)

        response = CEOAnalysisResponse(
            agent=self.name,
            question=question,
            answer=answer,
            interpretation="",           # filled below
            interpretation_source="fallback",
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Best-effort collaboration log for the UI — never fails the answer.
        # The recorder has its own try/except; this guard is defense in
        # depth so NOTHING escaping it can break the owner's answer.
        try:
            self._record_activity(db, response)
        except Exception:
            db.rollback()

        llm_text = llm.interpret_ceo_answer(response)
        if llm_text:
            response.interpretation = llm_text
            response.interpretation_source = "llm"
        else:
            response.interpretation = self._fallback_interpretation(answer)

        return response

    # ── Agent activity (collaboration log for the UI) ─────────────────────

    @staticmethod
    def _record_activity(db: Session, response: CEOAnalysisResponse) -> None:
        """Log one row per consulted agent plus the CEO synthesis row.

        Best-effort: any failure is rolled back and swallowed so the
        owner still gets the full answer.
        """
        answer = response.answer
        try:
            business = db.query(Business).first()
            business_id = business.id if business else None

            # One row per consulted agent: what it contributed.
            findings_by_domain: dict[str, str] = {}
            for finding in answer.key_findings:
                findings_by_domain.setdefault(
                    finding.domain, finding.statement
                )
            for decision in answer.routing:
                if not decision.consulted:
                    continue
                headline = findings_by_domain.get(
                    decision.domain, "Findings contributed."
                )
                db.add(AgentActivity(
                    business_id=business_id,
                    agent_name=decision.agent_name,
                    action="Contributed findings to CEO Agent analysis",
                    finding=headline,
                    data_points=(
                        f"question={response.question!r}, "
                        f"routing_reason={decision.reason}"
                    ),
                ))

            # The CEO synthesis row: the collaboration outcome.
            hs = answer.health_score
            top_action = (
                answer.recommended_actions[0]
                if answer.recommended_actions else None
            )
            top_text = (
                f" Top priority: {top_action.title}."
                if top_action else ""
            )
            db.add(AgentActivity(
                business_id=business_id,
                agent_name="CEO Agent",
                action="Answered owner question with cross-agent analysis",
                finding=(
                    f"Routed '{response.question}' to "
                    f"{len(answer.consulted_agents)} agent(s): "
                    f"{', '.join(answer.consulted_agents)}. Health Score "
                    f"{hs.score}/100 ({hs.risk_level} risk) with "
                    f"{len(answer.recommended_actions)} prioritized "
                    f"actions.{top_text}"
                    if hs is not None else
                    f"Routed '{response.question}' to "
                    f"{len(answer.consulted_agents)} agent(s)."
                ),
                data_points=(
                    f"question={response.question!r}, "
                    f"agents={len(answer.consulted_agents)}, "
                    + (
                        f"health_score={hs.score}, "
                        f"risk={hs.risk_level}, "
                        if hs is not None else ""
                    )
                    + f"actions={len(answer.recommended_actions)}"
                    + (
                        f", top_priority={top_action.priority}"
                        if top_action else ""
                    )
                ),
            ))
            db.commit()
        except Exception:
            db.rollback()

    # ── Deterministic fallback (facts-only, no invented numbers) ───────────

    @staticmethod
    def _fallback_interpretation(answer: CEOAnswer) -> str:
        parts: list[str] = []
        hs = answer.health_score

        # 1. Direct answer to the question
        if answer.root_causes:
            main = "; ".join(rc.title.lower() for rc in answer.root_causes)
            parts.append(f"Your sales are down mainly because {main}.")
        elif answer.key_findings:
            negatives = [
                f.statement for f in answer.key_findings
                if f.severity == "negative"
            ][:3]
            if negatives:
                parts.append(
                    "The main issues right now: " + "; ".join(negatives) + "."
                )
        else:
            parts.append("No significant problems were detected.")

        # 2. Health score and risk level
        if hs is not None:
            parts.append(
                f"Business Health Score: {hs.score}/100 — {hs.risk_level} "
                f"risk ({hs.formula})."
            )

        # 3. Prioritized actions
        if answer.recommended_actions:
            lines = [
                f"{i}) [{a.priority}] {a.title} — {a.evidence[0]}"
                if a.evidence else f"{i}) [{a.priority}] {a.title}"
                for i, a in enumerate(answer.recommended_actions, start=1)
            ]
            parts.append("Do these in order: " + " ".join(lines) + ".")

        # 4. Incomplete analysis note
        if answer.incomplete_analysis and answer.incomplete_reason:
            parts.append(answer.incomplete_reason)

        return " ".join(parts)


register_agent(CEOAgent())

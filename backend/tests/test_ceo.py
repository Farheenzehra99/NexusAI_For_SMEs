"""
CEO Agent orchestration tests — the complete "Why are my sales down?"
scenario against the canonical Ali Garments seed data.

Expected values (hand-verified from the seed):

    Health Score: 75/100, moderate risk (from the BI formula)
    Routing for a sales question: ALL FOUR agents
    Root causes:
        1. Best seller "Embroidered Kurti — White" at 5 units
           (4.29 days of sales, Rs 1,090,000 revenue, reorder 66)
        2. Delivery complaints: 8 of 18 tickets (44.44%),
           complaints +233.33%, delays average 5.83 days
        3. Khan Fabrics Counter converts at 1.4% vs 3.4% benchmark
        4. Revenue -16.38% from Apr peak, margin 18.35% vs 21.55%
    Actions (priority order):
        urgent   reorder the best seller (66 units)
        high     fix delivery with the courier partner
        medium   move Rs 30,000 Khan Fabrics -> Digital Lookbook
        medium   clear 8 overstocked products (Rs 3,219,300 excess)
        low      rebuild margin (18.35% vs 21.55% peak)
"""

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.business import AgentActivity, Business
from app.services.ceo import get_ceo_answer, route_question
from app.services.ceo import BusinessNotFoundError, NoBIDataError
from app.agents.ceo import CEOAgent
from app.agents.base import AGENT_REGISTRY


@pytest.fixture()
def activity_guard(db):
    """Delete any agent-activity rows a test creates (keeps the seed
    canonical) while still letting the test assert on them."""
    before = db.query(func.max(AgentActivity.id)).scalar() or 0
    yield before
    db.query(AgentActivity).filter(AgentActivity.id > before).delete()
    db.commit()


# ── Routing (pure function, controlled inputs) ─────────────────────────────

class TestRouting:
    def test_sales_question_routes_to_all_four_agents(self):
        routed = route_question("Why are my sales down?")
        assert set(routed) == {"finance", "inventory", "marketing", "support"}
        assert "diagnose the decline" in routed["finance"]
        assert "stock-outs" in routed["inventory"]
        assert "demand" in routed["marketing"]
        assert "repeat purchases" in routed["support"]

    @pytest.mark.parametrize("question", [
        "Why are my sales down?",
        "Revenue is declining, what happened?",
        "Our profit is falling — help",
        "Why are we losing income?",
    ])
    def test_sales_variants_route_to_all_four(self, question):
        assert set(route_question(question)) == {
            "finance", "inventory", "marketing", "support",
        }

    def test_stock_question_routes_to_inventory(self):
        routed = route_question("Should I reorder my stock?")
        assert set(routed) == {"inventory"}

    def test_ad_budget_question_routes_to_marketing(self):
        routed = route_question("Is my ad budget working?")
        assert set(routed) == {"marketing"}

    def test_complaint_question_routes_to_support(self):
        routed = route_question("Why are customers complaining about delivery?")
        assert set(routed) == {"support"}

    def test_expense_question_routes_to_finance(self):
        routed = route_question("How are my expenses this month?")
        assert set(routed) == {"finance"}

    def test_unrecognized_question_gets_full_review(self):
        routed = route_question("What should I focus on?")
        assert set(routed) == {"finance", "inventory", "marketing", "support"}
        assert routed["finance"] == "general business review"

    def test_empty_question_gets_full_review(self):
        assert set(route_question("")) == {
            "finance", "inventory", "marketing", "support",
        }


# ── Routing endpoint (GET /api/ceo/route — used by the Command Center) ─────

def _route(question: str):
    """Call the routing endpoint function directly (same pattern as the
    dashboard tests — framework-level Query validation is not under test)."""
    import asyncio

    from app.api.ceo import ceo_route

    return asyncio.run(ceo_route(question=question))


class TestCEORouteEndpoint:
    def test_sales_question_routes_to_all_four(self):
        res = _route("Why are my sales down?")
        assert res.agent == "CEO Agent"
        assert res.question == "Why are my sales down?"
        assert res.understood_as == (
            "The owner wants to understand why sales have fallen and what "
            "to do about it."
        )
        assert [s.domain for s in res.routing] == [
            "finance", "inventory", "marketing", "support",
        ]
        for step in res.routing:
            assert step.agent_name
            assert step.reason

    def test_stock_question_routes_to_inventory_only(self):
        res = _route("What should I stock for Eid season?")
        assert [s.domain for s in res.routing] == ["inventory"]
        assert res.routing[0].agent_name == "Inventory Agent"

    def test_routing_matches_the_analysis_answer(self, db, activity_guard):
        """The route endpoint and the final answer must agree on routing —
        the UI shows the route steps before the answer arrives."""
        res = _route("Why are my sales down?")
        answer = get_ceo_answer(db, "Why are my sales down?")
        assert [s.domain for s in res.routing] == [
            r.domain for r in answer.routing
        ]
        assert [s.reason for s in res.routing] == [
            r.reason for r in answer.routing
        ]


# ── The complete "Why are my sales down?" scenario ─────────────────────────

class TestSalesDownScenario:
    def test_all_four_agents_participate(self, db, activity_guard):
        answer = get_ceo_answer(db, "Why are my sales down?")
        assert answer.consulted_agents == [
            "Finance Agent", "Inventory Agent",
            "Marketing Agent", "Customer Support Agent",
        ]
        assert answer.missing_agents == []
        assert answer.incomplete_analysis is False
        assert answer.incomplete_reason is None
        assert all(r.consulted for r in answer.routing)

    def test_question_and_intent(self, db, activity_guard):
        answer = get_ceo_answer(db, "Why are my sales down?")
        assert answer.question == "Why are my sales down?"
        assert answer.understood_as == (
            "The owner wants to understand why sales have fallen and what "
            "to do about it."
        )

    def test_health_score_and_risk_level_included(self, db, activity_guard):
        answer = get_ceo_answer(db, "Why are my sales down?")
        hs = answer.health_score
        assert hs is not None
        assert hs.score == 75
        assert hs.risk_level == "moderate"
        assert "35% Finance (82)" in hs.formula

    def test_key_findings_quote_agent_numbers(self, db, activity_guard):
        answer = get_ceo_answer(db, "Why are my sales down?")
        statements = [f.statement for f in answer.key_findings]
        assert len(statements) == 12   # 3 per consulted domain
        assert any("Revenue vs peak: -16.38% from Apr peak" in s
                   for s in statements)
        assert any("Critical stock-out risks: 1 product(s)" in s
                   for s in statements)
        assert any("Underperforming campaigns: 1: Khan Fabrics Counter" in s
                   for s in statements)
        assert any("Negative feedback: 83.33% of 18 tickets" in s
                   for s in statements)
        # every finding carries its agent's name
        assert {f.agent_name for f in answer.key_findings} == {
            "Finance Agent", "Inventory Agent",
            "Marketing Agent", "Customer Support Agent",
        }

    def test_root_causes_match_seed_story(self, db, activity_guard):
        answer = get_ceo_answer(db, "Why are my sales down?")
        causes = answer.root_causes
        assert [c.title for c in causes] == [
            "Best-selling product is about to stock out",
            "Delivery problems are driving customers away",
            "An underperforming campaign is wasting ad spend",
            "Revenue is significantly below its peak",
        ]

        stockout = causes[0]
        assert "Embroidered Kurti — White" in stockout.statement
        assert "Rs 1,090,000" in stockout.statement
        assert "5 units" in stockout.statement
        assert "4.29" in stockout.statement
        assert "66 units" in " ".join(stockout.evidence)

        delivery = causes[1]
        assert "8 of 18 tickets" in delivery.statement
        assert "44.44%" in delivery.statement
        assert "+233.33%" in delivery.statement
        assert "5.83" in " ".join(delivery.evidence)

        campaign = causes[2]
        assert "Khan Fabrics Counter" in campaign.statement
        assert "1.4%" in campaign.statement
        assert "3.4%" in campaign.statement

        revenue = causes[3]
        assert "-16.38%" in revenue.statement
        assert "18.35%" in revenue.statement
        assert "21.55%" in revenue.statement

    def test_recommended_actions_are_grounded_and_sorted(self, db,
                                                         activity_guard):
        answer = get_ceo_answer(db, "Why are my sales down?")
        actions = answer.recommended_actions
        assert [a.priority for a in actions] == [
            "urgent", "high", "medium", "medium", "low",
        ]

        reorder = actions[0]
        assert reorder.title == "Reorder Embroidered Kurti — White today"
        assert "66 units" in reorder.description
        joined = " ".join(reorder.evidence)
        assert "5 units" in joined
        assert "4.29" in joined
        assert "Rs 1,090,000" in joined

        delivery = actions[1]
        assert delivery.title == "Fix the delivery process with the courier partner"

        reallocation = actions[2]
        assert reallocation.title == (
            "Move Rs 30,000 from Khan Fabrics Counter to Digital Lookbook"
        )
        assert "Rs 30,000" in reallocation.description

        overstock = actions[3]
        assert overstock.title == "Clear overstocked inventory"
        assert "8 overstocked products" in overstock.description
        assert "Rs 3,219,300" in " ".join(overstock.evidence)

        margin = actions[4]
        assert margin.title == "Review pricing and expenses to rebuild margin"
        assert "18.35%" in " ".join(margin.evidence)

        # every action is actionable: title, description, evidence, impact
        for action in actions:
            assert action.title and action.description
            assert action.evidence            # evidence is mandatory
            assert action.expected_impact
            assert action.agent_name in answer.consulted_agents

    def test_no_fabricated_numbers(self, db, activity_guard):
        """Sanity: known seed numbers appear; nothing outside agent output."""
        answer = get_ceo_answer(db, "Why are my sales down?")
        text = " ".join(
            [a.statement for a in answer.key_findings]
            + [c.statement for c in answer.root_causes]
            + [t for a in answer.recommended_actions for t in a.evidence]
        )
        for real in ("16.38", "1,090,000", "83.33", "30,000",
                     "3,219,300", "233.33", "4.29", "66"):
            assert real in text
        # the fake-looking numbers from the OLD activity narrative must
        # never leak into the computed answer
        for fabricated in ("Rs 25,000 per day", "6.2 months", "platform avg"):
            assert fabricated not in text

    def test_answer_json_serializable(self, db, activity_guard):
        data = get_ceo_answer(db, "Why are my sales down?").model_dump()
        assert data["health_score"]["score"] == 75
        assert len(data["recommended_actions"]) == 5
        assert data["recommended_actions"][0]["priority"] == "urgent"


# ── Partial failure handling ───────────────────────────────────────────────

class TestPartialFailure:
    def test_marketing_failure_preserves_other_agents(self, db, monkeypatch):
        import app.services.bi as bi_service
        from app.services.marketing import MarketingDataError

        def _raise(db_):
            raise MarketingDataError("no campaigns")

        monkeypatch.setitem(
            bi_service._LOADERS, "marketing",
            (_raise, MarketingDataError),
        )
        answer = get_ceo_answer(db, "Why are my sales down?")

        # Partial results preserved from the remaining agents
        assert answer.consulted_agents == [
            "Finance Agent", "Inventory Agent", "Customer Support Agent",
        ]
        assert answer.missing_agents == ["Marketing Agent"]
        assert answer.incomplete_analysis is True
        assert answer.incomplete_reason == (
            "Analysis is incomplete: Marketing Agent could not be "
            "consulted (data unavailable). The findings and actions above "
            "cover the remaining areas only."
        )
        # routing decision reflects the failure
        marketing_routing = next(
            r for r in answer.routing if r.domain == "marketing"
        )
        assert marketing_routing.consulted is False
        assert marketing_routing.reason == (
            "campaign performance drives customer demand"
        )
        # findings/actions exclude marketing; others kept
        assert all(f.domain != "marketing" for f in answer.key_findings)
        assert all(a.domain != "marketing" for a in answer.recommended_actions)
        assert any(a.domain == "inventory" for a in answer.recommended_actions)
        # health score re-normalized (70 with marketing missing)
        assert answer.health_score.score == 70
        assert answer.health_score.risk_level == "moderate"

    def test_every_agent_failure_raises(self, db, monkeypatch):
        import app.services.bi as bi_service
        from app.services.finance import FinanceDataError
        from app.services.inventory import InventoryDataError
        from app.services.marketing import MarketingDataError
        from app.services.support import SupportDataError

        def _raise(error_cls):
            def loader(db_):
                raise error_cls("no data")
            return loader

        monkeypatch.setitem(bi_service._LOADERS, "finance",
                            (_raise(FinanceDataError), FinanceDataError))
        monkeypatch.setitem(bi_service._LOADERS, "inventory",
                            (_raise(InventoryDataError), InventoryDataError))
        monkeypatch.setitem(bi_service._LOADERS, "marketing",
                            (_raise(MarketingDataError), MarketingDataError))
        monkeypatch.setitem(bi_service._LOADERS, "support",
                            (_raise(SupportDataError), SupportDataError))
        with pytest.raises(NoBIDataError):
            get_ceo_answer(db, "Why are my sales down?")

    def test_missing_business_raises(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            with pytest.raises(BusinessNotFoundError):
                get_ceo_answer(session, "Why are my sales down?")
        finally:
            session.close()

    def test_marketing_question_with_marketing_failure(self, db, monkeypatch):
        """A marketing-only question with marketing down still answers."""
        import app.services.bi as bi_service
        from app.services.marketing import MarketingDataError

        def _raise(db_):
            raise MarketingDataError("no campaigns")

        monkeypatch.setitem(
            bi_service._LOADERS, "marketing",
            (_raise, MarketingDataError),
        )
        answer = get_ceo_answer(db, "Is my ad budget working?")
        assert answer.consulted_agents == []
        assert answer.missing_agents == ["Marketing Agent"]
        assert answer.incomplete_analysis is True
        assert answer.key_findings == []
        assert answer.recommended_actions == []
        # health score from the remaining domains is still included
        assert answer.health_score.score == 70


# ── Full agent response + collaboration log ─────────────────────────────────

class TestCEOAgent:
    def test_agent_registered(self):
        assert "ceo_agent" in AGENT_REGISTRY
        assert isinstance(AGENT_REGISTRY["ceo_agent"], CEOAgent)

    def test_agent_metadata_intact(self):
        info = AGENT_REGISTRY["ceo_agent"].info()
        assert info.name == "CEO Agent"
        assert info.status == "active"
        assert "Prioritized action planning" in info.tasks

    def test_analyze_returns_valid_response(self, db, activity_guard):
        agent = AGENT_REGISTRY["ceo_agent"]
        response = agent.analyze(db, question="Why are my sales down?")
        assert response.agent == "CEO Agent"
        assert response.question == "Why are my sales down?"
        assert response.answer.health_score.score == 75
        assert response.interpretation_source in ("llm", "fallback")
        assert len(response.interpretation) > 50
        assert response.generated_at

    def test_fallback_interpretation_quotes_computed_numbers(self, db,
                                                             activity_guard):
        agent = AGENT_REGISTRY["ceo_agent"]
        answer = get_ceo_answer(db, "Why are my sales down?")
        text = agent._fallback_interpretation(answer)

        assert "sales are down mainly because" in text
        assert "stock out" in text                     # root cause headline
        assert "75/100" in text                        # health score
        assert "moderate risk" in text
        assert "[urgent]" in text                      # priority markers
        assert "Reorder Embroidered Kurti — White today" in text
        assert "Move Rs 30,000" in text
        assert "Do these in order" in text

    def test_activity_log_records_the_collaboration(self, db, activity_guard):
        """The UI story: each agent logs its contribution, CEO logs the
        synthesis."""
        agent = AGENT_REGISTRY["ceo_agent"]
        agent.analyze(db, question="Why are my sales down?")

        rows = (
            db.query(AgentActivity)
            .filter(AgentActivity.id > activity_guard)
            .all()
        )
        assert len(rows) == 5   # 4 contributions + 1 CEO synthesis

        by_agent = {r.agent_name: r for r in rows}
        assert set(by_agent) == {
            "Finance Agent", "Inventory Agent",
            "Marketing Agent", "Customer Support Agent", "CEO Agent",
        }
        for name in ("Finance Agent", "Inventory Agent",
                     "Marketing Agent", "Customer Support Agent"):
            assert by_agent[name].action == (
                "Contributed findings to CEO Agent analysis"
            )
            assert by_agent[name].finding  # a real headline finding
            assert "Why are my sales down?" in by_agent[name].data_points

        ceo = by_agent["CEO Agent"]
        assert ceo.action == (
            "Answered owner question with cross-agent analysis"
        )
        assert "Health Score 75/100 (moderate risk)" in ceo.finding
        assert "Reorder Embroidered Kurti — White today" in ceo.finding
        assert "health_score=75" in ceo.data_points
        assert "agents=4" in ceo.data_points

    def test_activity_failure_never_breaks_the_answer(self, db, monkeypatch,
                                                      activity_guard):
        """Even if activity logging blows up, the owner still gets the plan."""
        def _boom(self, db_, response_):
            raise RuntimeError("activity table broken")

        monkeypatch.setattr(CEOAgent, "_record_activity", _boom)
        agent = AGENT_REGISTRY["ceo_agent"]
        response = agent.analyze(db, question="Why are my sales down?")
        assert response.answer.health_score.score == 75
        assert len(response.answer.recommended_actions) == 5

    def test_llm_not_configured_returns_none(self, db, activity_guard,
                                             monkeypatch):
        from app.config import settings
        from app.services import llm as llm_service
        from app.schemas.ceo import CEOAnalysisResponse

        answer = get_ceo_answer(db, "Why are my sales down?")
        response = CEOAnalysisResponse(
            agent="CEO Agent", question="Why are my sales down?",
            answer=answer, interpretation="", interpretation_source="fallback",
            generated_at="2026-09-01T00:00:00",
        )
        monkeypatch.setattr(settings, "gemini_api_key", "")
        assert llm_service.is_llm_configured() is False
        assert llm_service.interpret_ceo_answer(response) is None

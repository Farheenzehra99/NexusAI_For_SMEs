"""Dashboard endpoint tests — the business overview must be grounded in the
REAL AI workforce outputs (BI health score + CEO action plan) and the seeded
business data, never in static or fabricated values.

Hand-verified expectations for the canonical seed:

    BI Health Score (computed live, NOT the static business.health_score=72):
        75/100, moderate risk
        "35% Finance (82) + 25% Inventory (61) + 20% Marketing (96) +
         20% Support (59) = 75 (moderate risk)"
    Metrics (current month = Aug 2026):
        Revenue   Rs 4,850,000  +5.4% MoM   (vs Jul Rs 4,600,000)
        Profit    Rs   890,000  +4.7% MoM   (vs Jul Rs   850,000)
        Orders           96     -5.9% MoM   (vs Jul 102)
        Customers       847    +400.0% active customers (10 in Aug vs 2 in Jul)
    Recommendations = the CEO Agent's plan for "Why are my sales down?":
        urgent  reorder Embroidered Kurti — White (66 units)
        high    fix the delivery process with the courier partner
        medium  move Rs 30,000 Khan Fabrics Counter -> Digital Lookbook
        medium  clear overstocked inventory
        low     review pricing and expenses to rebuild margin
    Inventory alerts enriched with agent-computed numbers:
        Embroidered Kurti — White: 4.29 days of stock left, reorder 66
"""

import asyncio

import pytest

from app.api.dashboard import get_dashboard
from app.services.bi import NoBIDataError


def _dashboard(db):
    return asyncio.run(get_dashboard(db))


@pytest.mark.usefixtures("_ensure_seeded")
class TestDashboardGroundedInAIWorkforce:
    def test_health_score_is_bi_computed_not_static(self, db):
        """The dashboard must show the LIVE BI score (75), never the static
        seeded column (business.health_score == 72)."""
        data = _dashboard(db)

        from app.models.business import Business

        static = db.query(Business).first().health_score
        assert static == 72  # the stale seed column still exists...
        assert data.health_score == 75  # ...but is NOT what we serve
        assert data.risk_level == "moderate"

    def test_health_formula_and_domain_scores(self, db):
        data = _dashboard(db)

        assert data.health_formula is not None
        assert "35% Finance (82)" in data.health_formula
        assert "25% Inventory (61)" in data.health_formula
        assert "20% Marketing (96)" in data.health_formula
        assert "20% Support (59)" in data.health_formula
        assert "= 75 (moderate risk)" in data.health_formula

        by_domain = {d.domain: d for d in data.domain_scores}
        assert set(by_domain) == {"finance", "inventory", "marketing", "support"}
        assert by_domain["finance"].score == 82
        assert by_domain["inventory"].score == 61
        assert by_domain["marketing"].score == 96
        assert by_domain["support"].score == 59

        assert data.weakest_domain == "support"
        assert data.strongest_domain == "marketing"
        assert data.missing_domains == []
        assert data.as_of_date == "2026-08-28"

    def test_recommendations_are_the_ceo_action_plan(self, db):
        data = _dashboard(db)

        priorities = [r.priority for r in data.recommendations]
        assert priorities == ["urgent", "high", "medium", "medium", "low"]

        first = data.recommendations[0]
        assert first.title == "Reorder Embroidered Kurti — White today"
        assert first.agent == "Inventory Agent"
        assert "66 units" in first.description
        assert first.evidence, "every action must carry evidence"
        assert any("5 units" in e for e in first.evidence)
        assert first.expected_impact

        titles = [r.title for r in data.recommendations]
        assert "Fix the delivery process with the courier partner" in titles

        # Legacy alias stays in sync with the priority.
        assert all(r.impact == r.priority for r in data.recommendations)

    def test_metrics_are_real_current_month_values(self, db):
        data = _dashboard(db)
        by_label = {m.label: m for m in data.metrics}

        assert by_label["Revenue"].value == 4_850_000
        assert by_label["Revenue"].change == 5.4
        assert by_label["Profit"].value == 890_000
        assert by_label["Profit"].change == 4.7

        # Orders: the CURRENT month's count, matching the monthly cards.
        assert by_label["Orders"].value == 96
        assert by_label["Orders"].change == -5.9

        assert by_label["Customers"].value == 847
        # Computed from Customer.last_order_date: 10 active in Aug vs 2 in Jul.
        assert by_label["Customers"].change == 400.0
        assert by_label["Customers"].change_label == "active customers"

    def test_inventory_alerts_enriched_with_agent_numbers(self, db):
        data = _dashboard(db)
        by_item = {a.item: a for a in data.inventory_alerts}

        kurti = by_item["Embroidered Kurti — White"]
        assert kurti.status == "critical"
        assert kurti.qty == 5
        assert kurti.days_of_stock_remaining == pytest.approx(4.29, abs=0.01)
        assert kurti.recommended_reorder_qty == 66

        shalwar = by_item["Formal Shalwar — Navy"]
        assert shalwar.status == "overstock"
        assert shalwar.excess_stock_qty is not None and shalwar.excess_stock_qty > 0

    def test_raw_business_sections_present(self, db):
        data = _dashboard(db)

        assert data.business_name == "Ali Garments"
        assert data.owner_name == "Ahmed Ali"
        assert len(data.sales_trend) == 6
        assert data.sales_trend[-1].month == "Aug"
        assert len(data.top_products) == 5
        assert data.top_products[0].name == "Embroidered Kurti — White"
        assert len(data.weak_products) == 5
        assert data.support_ticket_summary["total"] == 18
        assert data.support_ticket_summary["open"] == 10
        assert data.recent_activity, "seeded agent activity must be listed"


class TestDashboardGracefulDegradation:
    def test_bi_failure_still_returns_raw_dashboard(self, db, monkeypatch):
        """If the whole AI analysis layer fails, the dashboard degrades to
        the raw business data with null health fields — never a 500."""
        import app.api.dashboard as dash

        def _boom(db_):
            raise NoBIDataError("every agent failed")

        monkeypatch.setattr(dash, "get_bi_snapshot", _boom)
        data = asyncio.run(dash.get_dashboard(db))

        assert data.health_score is None
        assert data.risk_level is None
        assert data.recommendations == []
        assert data.domain_scores == []
        # The raw business data is still fully served.
        assert data.business_name == "Ali Garments"
        assert len(data.sales_trend) == 6
        assert len(data.metrics) == 4

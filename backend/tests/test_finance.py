"""
Finance Agent deterministic calculation tests.

Every expected value below was derived by hand from the canonical seed
data in backend/seed.py (Ali Garments demo):

    Monthly revenue (2026): Mar 5,200,000 / Apr 5,800,000 / May 5,500,000 /
                            Jun 5,100,000 / Jul 4,600,000 / Aug 4,850,000
    Monthly profit:         Mar 1,100,000 / Apr 1,250,000 / May 1,150,000 /
                            Jun   980,000 / Jul   850,000 / Aug   890,000
    Monthly expenses:       3,855,000 every month
                            (Salaries 1.8M, Rent 650K, Utilities 280K,
                             Marketing 155K, Logistics 320K,
                             Raw Materials 450K, Misc 200K)

These tests prove that all financial numbers come from code + database
logic — never from the LLM.
"""

import pytest

from app.services.finance import (
    get_financial_snapshot,
    InvalidRangeError,
    BusinessNotFoundError,
)
from app.agents.finance import FinanceAgent
from app.agents.base import AGENT_REGISTRY


# ── Validation ──────────────────────────────────────────────────────────────

class TestRangeValidation:
    def test_months_zero_rejected(self, db):
        with pytest.raises(InvalidRangeError):
            get_financial_snapshot(db, months=0)

    def test_months_negative_rejected(self, db):
        with pytest.raises(InvalidRangeError):
            get_financial_snapshot(db, months=-3)

    def test_months_over_twelve_rejected(self, db):
        with pytest.raises(InvalidRangeError):
            get_financial_snapshot(db, months=13)

    def test_months_boundary_values_accepted(self, db):
        assert get_financial_snapshot(db, months=1) is not None
        assert get_financial_snapshot(db, months=12) is not None

    def test_missing_business_raises(self):
        """An empty database must fail loudly, not return fake zeros."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        try:
            with pytest.raises(BusinessNotFoundError):
                get_financial_snapshot(session, months=6)
        finally:
            session.close()


# ── Revenue facts ───────────────────────────────────────────────────────────

class TestRevenueFacts:
    def test_current_revenue_matches_seed(self, db):
        facts = get_financial_snapshot(db, months=6)
        assert facts.revenue.current_month == "Aug"
        assert facts.revenue.current_revenue == 4_850_000

    def test_mom_change_matches_seed(self, db):
        facts = get_financial_snapshot(db, months=6)
        # (4,850,000 - 4,600,000) / 4,600,000 * 100 = 5.4348%
        assert facts.revenue.change_percent == pytest.approx(5.43, abs=0.01)
        assert facts.revenue.previous_month == "Jul"
        assert facts.revenue.previous_revenue == 4_600_000

    def test_peak_and_decline_from_peak(self, db):
        facts = get_financial_snapshot(db, months=6)
        assert facts.revenue.peak_month == "Apr"
        assert facts.revenue.peak_revenue == 5_800_000
        # (4,850,000 - 5,800,000) / 5,800,000 * 100 = -16.3793%
        assert facts.revenue.decline_from_peak_percent == pytest.approx(-16.38, abs=0.01)

    def test_trend_is_declining(self, db):
        facts = get_financial_snapshot(db, months=6)
        assert facts.revenue.trend == "declining"

    def test_series_covers_six_months_in_order(self, db):
        facts = get_financial_snapshot(db, months=6)
        months = [p.month for p in facts.revenue.series]
        assert months == ["Mar", "Apr", "May", "Jun", "Jul", "Aug"]
        assert facts.months_analyzed == 6

    def test_series_revenue_values_match_seed(self, db):
        facts = get_financial_snapshot(db, months=6)
        revenues = [p.revenue for p in facts.revenue.series]
        assert revenues == [
            5_200_000, 5_800_000, 5_500_000, 5_100_000, 4_600_000, 4_850_000,
        ]

    def test_short_window_uses_last_months(self, db):
        facts = get_financial_snapshot(db, months=2)
        assert facts.months_analyzed == 2
        assert [p.month for p in facts.revenue.series] == ["Jul", "Aug"]
        # In the Jul-Aug window, Aug (4.85M) is above Jul (4.6M) → peak is Aug
        assert facts.revenue.peak_month == "Aug"


# ── Expense facts ───────────────────────────────────────────────────────────

class TestExpenseFacts:
    def test_total_matches_seed(self, db):
        facts = get_financial_snapshot(db, months=6)
        # 1,800,000 + 650,000 + 280,000 + 155,000 + 320,000 + 450,000 + 200,000
        assert facts.expenses.total == 3_855_000

    def test_expenses_flat_month_over_month(self, db):
        facts = get_financial_snapshot(db, months=6)
        assert facts.expenses.previous_total == 3_855_000
        assert facts.expenses.change_percent == pytest.approx(0.0, abs=0.01)

    def test_top_category_is_salaries(self, db):
        facts = get_financial_snapshot(db, months=6)
        assert facts.expenses.top_category == "Salaries"
        assert facts.expenses.top_category_amount == 1_800_000

    def test_seven_categories_present(self, db):
        facts = get_financial_snapshot(db, months=6)
        names = {c.category for c in facts.expenses.categories}
        assert names == {
            "Salaries", "Rent", "Utilities", "Marketing",
            "Logistics", "Raw Materials", "Misc",
        }

    def test_category_shares_sum_to_100(self, db):
        facts = get_financial_snapshot(db, months=6)
        total_share = sum(c.share_percent for c in facts.expenses.categories)
        assert total_share == pytest.approx(100.0, abs=0.05)

    def test_salaries_share(self, db):
        facts = get_financial_snapshot(db, months=6)
        salaries = next(c for c in facts.expenses.categories if c.category == "Salaries")
        # 1,800,000 / 3,855,000 * 100 = 46.69%
        assert salaries.share_percent == pytest.approx(46.69, abs=0.01)


# ── Profit & margin facts ───────────────────────────────────────────────────

class TestProfitFacts:
    def test_current_profit_matches_seed(self, db):
        facts = get_financial_snapshot(db, months=6)
        assert facts.profit.current_profit == 890_000
        assert facts.profit.previous_profit == 850_000

    def test_profit_mom_change(self, db):
        facts = get_financial_snapshot(db, months=6)
        # (890,000 - 850,000) / 850,000 * 100 = 4.7059%
        assert facts.profit.change_percent == pytest.approx(4.71, abs=0.01)

    def test_current_margin_matches_formula(self, db):
        facts = get_financial_snapshot(db, months=6)
        # 890,000 / 4,850,000 * 100 = 18.3505%
        assert facts.profit.current_margin_percent == pytest.approx(18.35, abs=0.01)

    def test_peak_margin_is_april(self, db):
        facts = get_financial_snapshot(db, months=6)
        # 1,250,000 / 5,800,000 * 100 = 21.5517%
        assert facts.profit.peak_margin_month == "Apr"
        assert facts.profit.peak_margin_percent == pytest.approx(21.55, abs=0.01)

    def test_margin_compression(self, db):
        facts = get_financial_snapshot(db, months=6)
        # 21.5517% - 18.3505% = 3.2012 pp
        assert facts.profit.margin_compression_pp == pytest.approx(3.2, abs=0.05)

    def test_every_month_margin_matches_formula(self, db):
        facts = get_financial_snapshot(db, months=6)
        for point in facts.revenue.series:
            expected = round(point.profit / point.revenue * 100, 2)
            assert point.margin_percent == expected


# ── Product facts ───────────────────────────────────────────────────────────

class TestProductFacts:
    def test_top_product_is_kurti_white(self, db):
        facts = get_financial_snapshot(db, months=6)
        top = facts.top_revenue_products[0]
        assert top.name == "Embroidered Kurti — White"
        assert top.sku == "AG-KT-001"
        assert top.revenue == 1_090_000
        assert top.units_sold == 218

    def test_top_product_share(self, db):
        facts = get_financial_snapshot(db, months=6)
        top = facts.top_revenue_products[0]
        # 1,090,000 / 7,338,100 * 100 = 14.8544%
        assert top.revenue_share_percent == pytest.approx(14.85, abs=0.01)

    def test_five_top_products_descending(self, db):
        facts = get_financial_snapshot(db, months=6)
        assert len(facts.top_revenue_products) == 5
        revenues = [p.revenue for p in facts.top_revenue_products]
        assert revenues == sorted(revenues, reverse=True)

    def test_weak_products_under_20_units(self, db):
        facts = get_financial_snapshot(db, months=6)
        # Denim Jeans 15, Shawl 12, Denim Jacket 11, Kids Boys 8, Kids Girls 6
        assert len(facts.weak_products) == 5
        assert all(w.units_sold < 20 for w in facts.weak_products)

    def test_weakest_product_is_kids_girls(self, db):
        facts = get_financial_snapshot(db, months=6)
        weakest = facts.weak_products[-1]
        assert weakest.name == "Kids Festive — Girls"
        assert weakest.units_sold == 6


# ── Unusual changes (anomaly rules) ─────────────────────────────────────────

class TestUnusualChanges:
    def test_decline_from_peak_flagged_high(self, db):
        facts = get_financial_snapshot(db, months=6)
        anomaly = next(
            (u for u in facts.unusual_changes if u.type == "revenue_decline_from_peak"), None
        )
        assert anomaly is not None
        assert anomaly.severity == "high"
        assert anomaly.metrics["decline_percent"] == pytest.approx(-16.38, abs=0.01)

    def test_margin_compression_flagged(self, db):
        facts = get_financial_snapshot(db, months=6)
        anomaly = next(
            (u for u in facts.unusual_changes if u.type == "margin_compression"), None
        )
        assert anomaly is not None
        assert anomaly.metrics["compression_pp"] == pytest.approx(3.2, abs=0.05)

    def test_consecutive_declines_flagged(self, db):
        facts = get_financial_snapshot(db, months=6)
        anomaly = next(
            (u for u in facts.unusual_changes if u.type == "consecutive_monthly_declines"), None
        )
        assert anomaly is not None
        assert anomaly.metrics["consecutive_declines"] == 3
        assert anomaly.metrics["start_month"] == "May"
        assert anomaly.metrics["end_month"] == "Jul"

    def test_no_false_expense_spike(self, db):
        """Expenses are flat in the seed — no spike should be reported."""
        facts = get_financial_snapshot(db, months=6)
        spikes = [u for u in facts.unusual_changes if u.type == "expense_category_spike"]
        assert spikes == []

    def test_anomaly_descriptions_contain_computed_numbers(self, db):
        facts = get_financial_snapshot(db, months=6)
        for anomaly in facts.unusual_changes:
            assert anomaly.description
            assert anomaly.metrics


# ── Full agent response ─────────────────────────────────────────────────────

class TestFinanceAgent:
    def test_agent_registered(self):
        assert "finance_agent" in AGENT_REGISTRY
        assert isinstance(AGENT_REGISTRY["finance_agent"], FinanceAgent)

    def test_agent_metadata_intact(self):
        agent = AGENT_REGISTRY["finance_agent"]
        info = agent.info()
        assert info.name == "Finance Agent"
        assert info.status == "active"
        assert "P&L analysis" in info.tasks

    def test_analyze_returns_valid_response(self, db):
        agent = AGENT_REGISTRY["finance_agent"]
        response = agent.analyze(db, months=6)
        assert response.agent == "Finance Agent"
        assert response.facts.months_analyzed == 6
        assert response.interpretation_source in ("llm", "fallback")
        assert len(response.interpretation) > 50
        assert response.generated_at

    def test_fallback_interpretation_uses_only_facts(self, db):
        """With no LLM key configured, the deterministic fallback must
        quote the real computed numbers, never invented ones."""
        agent = AGENT_REGISTRY["finance_agent"]
        facts = get_financial_snapshot(db, months=6)
        text = agent._fallback_interpretation(facts)

        # Numbers that must appear (from the seed data)
        assert "4,850,000" in text          # Aug revenue
        assert "5,800,000" in text          # Apr peak
        assert "3,855,000" in text          # Aug expenses
        assert "1,800,000" in text          # Salaries
        assert "1,090,000" in text          # Kurti White revenue
        assert "Embroidered Kurti" in text
        assert "declining" in text

    def test_llm_unconfigured_returns_fallback(self, db):
        from app.services import llm as llm_service
        if not llm_service.is_llm_configured():
            agent = AGENT_REGISTRY["finance_agent"]
            response = agent.analyze(db, months=6)
            assert response.interpretation_source == "fallback"
        else:
            pytest.skip("LLM key is configured — fallback path skipped")

    def test_facts_are_json_serializable_for_ceo_agent(self, db):
        """The CEO Agent must be able to consume these facts as JSON."""
        facts = get_financial_snapshot(db, months=6)
        data = facts.model_dump()
        assert data["revenue"]["current_revenue"] == 4_850_000
        assert data["business_name"] == "Ali Garments"
        assert isinstance(data["unusual_changes"], list)

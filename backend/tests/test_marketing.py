"""
Marketing Agent deterministic calculation tests.

Every expected value below was derived by hand from the canonical seed
data in backend/seed.py (Ali Garments demo):

    Campaign                    Spend   Impr    Clicks  Conv   Revenue
    Summer Lawn Push            80,000  125,000 8,500   340    1,700,000
    Eid Preview Teasers         45,000  89,000  4,200   180      900,000
    Khan Fabrics Counter        30,000  67,000  6,786    95      285,000
    Digital Lookbook            25,000  45,000  2,800   142      710,000
    ─────────────────────────────────────────────────────────────────────
    Totals                     180,000  326,000 22,286   757   3,595,000

Hand-computed benchmarks:
    conversion rate  = 757 / 22,286  * 100 = 3.40 %
    cost/conversion  = 180,000 / 757       = Rs 237.78
    overall CTR      = 22,286 / 326,000 * 100 = 6.84 %
    overall ROAS     = 3,595,000 / 180,000  = 19.97

Underperformance rule (50% floor on the benchmark): 1.70 %.
    Khan Fabrics Counter converts at 1.4 % → the only underperformer.
Opportunity rule (125% bar): 4.25 %.
    Digital Lookbook (5.07 %) and Eid Preview (4.29 %) qualify;
    Digital Lookbook has the best ROAS (28.4).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.business import Business, MarketingCampaign, Product
from app.services.marketing import (
    get_marketing_snapshot,
    BusinessNotFoundError,
    NoCampaignDataError,
    UNDERPERFORMING_CONV_RATIO,
    OUTPERFORMING_CONV_RATIO,
)
from app.agents.marketing import MarketingAgent
from app.agents.base import AGENT_REGISTRY


def _campaign(facts, name):
    return next(f for f in facts.campaigns if f.name == name)


def _make_db_with_campaigns(*campaigns):
    """In-memory database with one business and the given campaigns."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(Business(name="Test Co", owner_name="Owner"))
    session.commit()
    for c in campaigns:
        c.business_id = 1
        session.add(c)
    session.commit()
    return session


# ── Validation and missing data ─────────────────────────────────────────────

class TestValidation:
    def test_missing_business_raises(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            with pytest.raises(BusinessNotFoundError):
                get_marketing_snapshot(session)
        finally:
            session.close()

    def test_business_without_campaigns_raises(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            session.add(Business(name="Empty Co", owner_name="Owner"))
            session.commit()
            with pytest.raises(NoCampaignDataError):
                get_marketing_snapshot(session)
        finally:
            session.close()


# ── Benchmark totals (all seed campaigns are valid) ─────────────────────────

class TestBenchmark:
    def test_totals_match_seed(self, db):
        b = get_marketing_snapshot(db).benchmark
        assert b.campaign_count == 4
        assert b.valid_campaign_count == 4
        assert b.invalid_campaign_count == 0
        assert b.total_spend == 180_000
        assert b.total_impressions == 326_000
        assert b.total_clicks == 22_286
        assert b.total_conversions == 757
        assert b.total_revenue_generated == 3_595_000

    def test_benchmark_ratios_match_hand_computed_values(self, db):
        b = get_marketing_snapshot(db).benchmark
        assert b.conversion_rate_percent == pytest.approx(3.4, abs=0.01)
        assert b.cost_per_conversion == pytest.approx(237.78, abs=0.01)
        assert b.overall_ctr_percent == pytest.approx(6.84, abs=0.01)
        assert b.overall_roas == pytest.approx(19.97, abs=0.01)

    def test_benchmark_formulas(self, db):
        b = get_marketing_snapshot(db).benchmark
        assert b.conversion_rate_percent == pytest.approx(
            b.total_conversions / b.total_clicks * 100, abs=0.01
        )
        assert b.cost_per_conversion == pytest.approx(
            b.total_spend / b.total_conversions, abs=0.01
        )
        assert b.overall_roas == pytest.approx(
            b.total_revenue_generated / b.total_spend, abs=0.01
        )


# ── Per-campaign metrics ────────────────────────────────────────────────────

class TestCampaignMetrics:
    def test_summer_lawn_push_metrics(self, db):
        f = _campaign(get_marketing_snapshot(db), "Summer Lawn Push")
        assert f.ctr_percent == pytest.approx(6.8, abs=0.01)
        assert f.conversion_rate_percent == pytest.approx(4.0, abs=0.01)
        assert f.cost_per_conversion == pytest.approx(235.29, abs=0.01)
        assert f.cost_per_click == pytest.approx(9.41, abs=0.01)
        assert f.roas == pytest.approx(21.25, abs=0.01)
        assert f.roi_percent == pytest.approx(2025.0, abs=0.1)

    def test_khan_fabrics_metrics(self, db):
        f = _campaign(get_marketing_snapshot(db), "Khan Fabrics Counter")
        assert f.ctr_percent == pytest.approx(10.13, abs=0.01)
        assert f.conversion_rate_percent == pytest.approx(1.4, abs=0.01)
        assert f.cost_per_conversion == pytest.approx(315.79, abs=0.01)
        assert f.roas == pytest.approx(9.5, abs=0.01)

    def test_digital_lookbook_metrics(self, db):
        f = _campaign(get_marketing_snapshot(db), "Digital Lookbook")
        assert f.conversion_rate_percent == pytest.approx(5.07, abs=0.01)
        assert f.cost_per_conversion == pytest.approx(176.06, abs=0.01)
        assert f.roas == pytest.approx(28.4, abs=0.01)

    def test_metric_formulas_hold_for_every_campaign(self, db):
        facts = get_marketing_snapshot(db)
        for f in facts.campaigns:
            if f.impressions > 0:
                assert f.ctr_percent == pytest.approx(
                    f.clicks / f.impressions * 100, abs=0.01
                )
            if f.clicks > 0:
                assert f.conversion_rate_percent == pytest.approx(
                    f.conversions / f.clicks * 100, abs=0.01
                )
                assert f.cost_per_click == pytest.approx(
                    f.spend / f.clicks, abs=0.01
                )
            if f.conversions > 0:
                assert f.cost_per_conversion == pytest.approx(
                    f.spend / f.conversions, abs=0.01
                )


# ── Explainable underperformance rule ───────────────────────────────────────

class TestUnderperformanceRule:
    def test_khan_fabrics_is_the_only_underperformer(self, db):
        facts = get_marketing_snapshot(db)
        assert facts.underperforming_campaign_names == ["Khan Fabrics Counter"]

    def test_khan_fabrics_reason_quotes_the_rule(self, db):
        f = _campaign(get_marketing_snapshot(db), "Khan Fabrics Counter")
        assert f.performance == "underperforming"
        assert "1.4%" in f.reason
        assert "3.4%" in f.reason            # benchmark
        assert "1.7%" in f.reason            # 50% floor
        assert "50%" in f.reason             # the rule itself is stated

    def test_underperformers_sorted_first(self, db):
        facts = get_marketing_snapshot(db)
        assert facts.campaigns[0].performance == "underperforming"
        assert facts.campaigns[0].name == "Khan Fabrics Counter"

    def test_outperforming_campaigns_detected(self, db):
        facts = get_marketing_snapshot(db)
        outperforming = {f.name for f in facts.campaigns if f.performance == "outperforming"}
        # 125% bar of 3.4% benchmark = 4.25%
        assert "Digital Lookbook" in outperforming
        assert "Eid Preview Teasers" in outperforming
        assert "Summer Lawn Push" not in outperforming  # 4.0% is in the acceptable band

    def test_best_campaign_is_digital_lookbook(self, db):
        facts = get_marketing_snapshot(db)
        assert facts.best_campaign_name == "Digital Lookbook"

    def test_reallocation_from_khan_to_digital_lookbook(self, db):
        facts = get_marketing_snapshot(db)
        r = facts.reallocation
        assert r is not None
        assert r.from_campaign == "Khan Fabrics Counter"
        assert r.from_campaign_spend == 30_000
        assert r.to_campaign == "Digital Lookbook"
        assert r.to_campaign_roas == pytest.approx(28.4, abs=0.01)
        assert r.to_campaign_cost_per_conversion == pytest.approx(176.06, abs=0.01)
        assert "Khan Fabrics Counter" in r.rationale
        assert "Digital Lookbook" in r.rationale

    def test_every_campaign_has_a_reason(self, db):
        facts = get_marketing_snapshot(db)
        for f in facts.campaigns:
            assert f.reason


# ── Product highlights (marketing-relevant product facts) ───────────────────

class TestProductHighlights:
    def test_top_performers_are_top_three_by_revenue(self, db):
        h = get_marketing_snapshot(db).product_highlights
        assert [p.name for p in h.top_performers] == [
            "Embroidered Kurti — White",
            "Bridal Wear — Red",
            "Formal Shalwar — Navy",
        ]

    def test_top_performer_note_flags_low_stock(self, db):
        h = get_marketing_snapshot(db).product_highlights
        top = h.top_performers[0]
        assert top.stock_qty == 5
        assert "5 units in stock" in top.note
        assert "restock" in top.note

    def test_declining_products_flagged(self, db):
        h = get_marketing_snapshot(db).product_highlights
        names = [p.name for p in h.declining]
        assert "Formal Shalwar — Navy" in names
        assert "Summer Pret — Floral" in names
        assert "Formal Shalwar — Grey" in names
        assert len(names) == 3  # only declining products above Rs 300,000
        assert all(p.trend == "down" for p in h.declining)

    def test_weak_sellers_flagged(self, db):
        h = get_marketing_snapshot(db).product_highlights
        assert len(h.weak_sellers) == 5
        assert all(p.units_sold < 20 for p in h.weak_sellers)
        assert h.weak_sellers[-1].name == "Kids Festive — Girls"  # weakest


# ── Malformed campaign data ─────────────────────────────────────────────────

class TestMalformedData:
    def test_conversions_exceeding_clicks_is_invalid(self):
        session = _make_db_with_campaigns(MarketingCampaign(
            name="Bad Campaign", channel="Instagram", spend=1000,
            impressions=1000, clicks=10, conversions=50,  # malformed
            revenue_generated=0, status="active",
        ))
        try:
            facts = get_marketing_snapshot(session)
            f = facts.campaigns[0]
            assert f.performance == "invalid_data"
            assert "conversions (50) exceed clicks (10)" in f.reason
            assert "Excluded from the benchmark" in f.reason
            assert facts.benchmark.invalid_campaign_count == 1
            assert facts.benchmark.valid_campaign_count == 0
        finally:
            session.close()

    def test_clicks_exceeding_impressions_is_invalid(self):
        session = _make_db_with_campaigns(MarketingCampaign(
            name="Clicky Campaign", channel="Facebook", spend=1000,
            impressions=100, clicks=500, conversions=10,  # malformed
            revenue_generated=0, status="active",
        ))
        try:
            facts = get_marketing_snapshot(session)
            assert facts.campaigns[0].performance == "invalid_data"
            assert facts.benchmark.invalid_campaign_count == 1
        finally:
            session.close()

    def test_negative_spend_is_invalid(self):
        session = _make_db_with_campaigns(MarketingCampaign(
            name="Negative Campaign", channel="Instagram", spend=-500,
            impressions=1000, clicks=100, conversions=10,
            revenue_generated=0, status="active",
        ))
        try:
            facts = get_marketing_snapshot(session)
            assert facts.campaigns[0].performance == "invalid_data"
            assert "negative spend" in facts.campaigns[0].reason
        finally:
            session.close()

    def test_missing_metrics_is_invalid(self):
        # Raw SQL is required to store true NULLs: the ORM column defaults
        # (default=0) would coerce None to 0 at insert time.
        from sqlalchemy import text
        session = _make_db_with_campaigns()
        try:
            session.execute(text(
                "INSERT INTO marketing_campaigns "
                "(business_id, name, channel, spend, impressions, clicks, "
                "conversions, revenue_generated, status) "
                "VALUES (1, 'Ghost Campaign', 'Facebook', 1000, NULL, NULL, "
                "NULL, NULL, 'active')"
            ))
            session.commit()
            facts = get_marketing_snapshot(session)
            assert facts.campaigns[0].performance == "invalid_data"
            assert "missing metric values" in facts.campaigns[0].reason
        finally:
            session.close()

    def test_invalid_campaign_excluded_from_benchmark(self):
        session = _make_db_with_campaigns(
            MarketingCampaign(
                name="Good Campaign", channel="Instagram", spend=10_000,
                impressions=50_000, clicks=1_000, conversions=50,
                revenue_generated=200_000, status="active",
            ),
            MarketingCampaign(
                name="Broken Campaign", channel="Facebook", spend=5_000,
                impressions=1_000, clicks=10, conversions=999,  # malformed
                revenue_generated=0, status="active",
            ),
        )
        try:
            b = get_marketing_snapshot(session).benchmark
            assert b.campaign_count == 2
            assert b.valid_campaign_count == 1
            assert b.total_spend == 10_000        # broken spend excluded
            assert b.total_clicks == 1_000
            assert b.total_conversions == 50
            assert b.conversion_rate_percent == pytest.approx(5.0, abs=0.01)
        finally:
            session.close()

    def test_zero_clicks_is_insufficient_data(self):
        session = _make_db_with_campaigns(MarketingCampaign(
            name="No Clicks Campaign", channel="Instagram", spend=1_000,
            impressions=10_000, clicks=0, conversions=0,
            revenue_generated=0, status="active",
        ))
        try:
            f = get_marketing_snapshot(session).campaigns[0]
            assert f.performance == "insufficient_data"
            assert "No clicks recorded" in f.reason
            assert f.conversion_rate_percent is None
        finally:
            session.close()

    def test_zero_conversions_with_clicks_is_underperforming(self):
        session = _make_db_with_campaigns(MarketingCampaign(
            name="Dead Campaign", channel="Facebook", spend=5_000,
            impressions=10_000, clicks=200, conversions=0,
            revenue_generated=0, status="active",
        ))
        try:
            facts = get_marketing_snapshot(session)
            f = facts.campaigns[0]
            assert f.performance == "underperforming"
            assert "No conversions recorded from 200 clicks" in f.reason
            assert f.cost_per_conversion is None
            # Benchmark with zero total conversions must not crash
            assert facts.benchmark.cost_per_conversion is None
        finally:
            session.close()


# ── Full agent response ─────────────────────────────────────────────────────

class TestMarketingAgent:
    def test_agent_registered(self):
        assert "marketing_agent" in AGENT_REGISTRY
        assert isinstance(AGENT_REGISTRY["marketing_agent"], MarketingAgent)

    def test_agent_metadata_intact(self):
        info = AGENT_REGISTRY["marketing_agent"].info()
        assert info.name == "Marketing Agent"
        assert info.status == "active"
        assert "Campaign performance analysis" in info.tasks

    def test_analyze_returns_valid_response(self, db):
        agent = AGENT_REGISTRY["marketing_agent"]
        response = agent.analyze(db)
        assert response.agent == "Marketing Agent"
        assert response.facts.benchmark.campaign_count == 4
        assert response.interpretation_source in ("llm", "fallback")
        assert len(response.interpretation) > 50
        assert response.generated_at

    def test_fallback_interpretation_uses_only_facts(self, db):
        """The deterministic fallback must quote the real computed numbers."""
        agent = AGENT_REGISTRY["marketing_agent"]
        facts = get_marketing_snapshot(db)
        text = agent._fallback_interpretation(facts)

        assert "180,000" in text          # total spend
        assert "757" in text              # total conversions
        assert "237.78" in text           # benchmark cost per conversion
        assert "Khan Fabrics Counter" in text
        assert "1.4%" in text            # its conversion rate
        assert "Digital Lookbook" in text
        assert "30,000" in text          # reallocation amount
        assert "Embroidered Kurti" in text
        assert "5 units in stock" in text  # product stock caveat

    def test_facts_json_serializable_for_ceo_agent(self, db):
        """The CEO Agent must be able to consume these facts as JSON."""
        facts = get_marketing_snapshot(db)
        data = facts.model_dump()
        assert data["business_name"] == "Ali Garments"
        assert data["underperforming_campaign_names"] == ["Khan Fabrics Counter"]
        assert data["reallocation"]["to_campaign"] == "Digital Lookbook"
        assert isinstance(data["campaigns"], list)

    def test_llm_not_configured_returns_none(self, db, monkeypatch):
        """With no API key the interpreter must short-circuit to None."""
        from app.config import settings
        from app.services import llm as llm_service

        facts = get_marketing_snapshot(db)
        monkeypatch.setattr(settings, "gemini_api_key", "")
        assert llm_service.is_llm_configured() is False
        assert llm_service.interpret_marketing_facts(facts) is None

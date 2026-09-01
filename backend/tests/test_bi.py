"""
BI Agent Business Health Score tests.

Two layers of testing:

1. CONTROLLED INPUTS — every sub-scorer and the composite formula are
   pure functions tested with synthetic facts objects. Every expected
   value below was hand-computed from the documented formula in
   app/services/bi.py:

       Finance seed-shaped: 100 - 0.5*16.38 - 1.5*3.2 - 5 = 82.01 -> 82
       Inventory seed-shaped: 100 - 15 - min(8*4, 24) = 61
       Marketing seed-shaped: 100 - 12 + 8 = 96
       Support seed-shaped: 100 - 25 - 7.67 - 8 = 59.33 -> 59
       Composite: .35*82 + .25*61 + .20*96 + .20*59 = 74.95 -> 75 (moderate)

2. SEED INTEGRATION — the full pipeline against the canonical Ali
   Garments data must reproduce the same numbers.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.business import Business
from app.schemas.finance import (
    ExpenseFacts,
    FinanceFacts,
    ProfitFacts,
    RevenueFacts,
)
from app.schemas.inventory import (
    InventoryFacts,
    InventoryRiskItem,
    InventorySummary,
)
from app.schemas.marketing import (
    CampaignPerformanceFact,
    MarketingBenchmark,
    MarketingFacts,
    ProductMarketingHighlights,
)
from app.schemas.support import (
    DeliveryFacts,
    SupportFacts,
    SupportSummary,
    SupportTrendFact,
)
from app.services.bi import (
    compute_health_score,
    finance_subscore,
    get_bi_snapshot,
    inventory_subscore,
    marketing_subscore,
    risk_level,
    support_subscore,
    BusinessNotFoundError,
    NoBIDataError,
)
from app.agents.bi import BIAgent
from app.agents.base import AGENT_REGISTRY


# ── Controlled-input builders ──────────────────────────────────────────────

def _finance(*, decline=-16.38, compression=3.2, trend="declining",
             mom_profit=4.71, current_revenue=4_850_000,
             peak_revenue=5_800_000, current_margin=18.35,
             peak_margin=21.55, peak_month="Apr") -> FinanceFacts:
    return FinanceFacts(
        business_name="Test Co", currency="PKR", months_analyzed=6,
        revenue=RevenueFacts(
            current_month="Aug", current_revenue=current_revenue,
            previous_month="Jul", previous_revenue=4_600_000,
            change_percent=5.43, peak_month=peak_month,
            peak_revenue=peak_revenue, decline_from_peak_percent=decline,
            series=[], trend=trend,
        ),
        expenses=ExpenseFacts(
            month="Aug", total=3_855_000, previous_total=3_855_000,
            change_percent=0.0, top_category="Rent",
            top_category_amount=650_000, categories=[],
        ),
        profit=ProfitFacts(
            current_month="Aug", current_profit=890_000,
            previous_profit=850_000, change_percent=mom_profit,
            current_margin_percent=current_margin,
            peak_margin_percent=peak_margin, peak_margin_month="Apr",
            margin_compression_pp=compression,
        ),
        top_revenue_products=[], weak_products=[], unusual_changes=[],
    )


def _inventory(*, risk_levels=()) -> InventoryFacts:
    risks = [
        InventoryRiskItem(sku=f"S{i}", product=f"P{i}", risk_level=lvl,
                          reason="r")
        for i, lvl in enumerate(risk_levels)
    ]
    return InventoryFacts(
        business_name="Test Co", currency="PKR", as_of_date="2026-08-31",
        velocity_window_days=30,
        summary=InventorySummary(
            total_active_products=15,
            at_risk_count=sum(
                1 for l in risk_levels
                if l in ("critical", "high", "medium", "out_of_stock")
            ),
            critical_count=risk_levels.count("critical"),
            overstock_count=risk_levels.count("overstock"),
            stagnant_count=risk_levels.count("stagnant"),
            total_stock_value_retail=1_000_000.0,
            recommended_reorder_units=66,
            recommended_reorder_cost=128_700.0,
            excess_stock_value_retail=1_980_000.0,
        ),
        products=[], risks=risks,
    )


def _marketing(*, perf=("underperforming", "acceptable", "outperforming",
                        "outperforming"), roas=19.97) -> MarketingFacts:
    campaigns = [
        CampaignPerformanceFact(
            name=f"C{i}", channel="Instagram", status="active",
            spend=1_000, impressions=1_000, clicks=100, conversions=10,
            revenue_generated=5_000, ctr_percent=10.0,
            conversion_rate_percent=10.0, cost_per_conversion=100.0,
            cost_per_click=10.0, roas=5.0, roi_percent=400.0,
            performance=p, reason="r",
        )
        for i, p in enumerate(perf)
    ]
    under = [c.name for c in campaigns if c.performance == "underperforming"]
    return MarketingFacts(
        business_name="Test Co", currency="PKR",
        benchmark=MarketingBenchmark(
            campaign_count=len(perf), valid_campaign_count=len(perf),
            invalid_campaign_count=0, total_spend=180_000.0,
            total_impressions=326_000, total_clicks=22_286,
            total_conversions=757, total_revenue_generated=3_595_000.0,
            conversion_rate_percent=3.4, cost_per_conversion=237.78,
            overall_ctr_percent=6.84, overall_roas=roas,
        ),
        campaigns=campaigns, underperforming_campaign_names=under,
        best_campaign_name=None, reallocation=None,
        product_highlights=ProductMarketingHighlights(
            top_performers=[], declining=[], weak_sellers=[]),
    )


def _support(*, negative=83.33, resolution=44.44, complaint_change=233.33,
             open_count=10, total=18) -> SupportFacts:
    return SupportFacts(
        business_name="Test Co", currency="PKR", as_of_date="2026-08-28",
        window_days=30,
        summary=SupportSummary(
            total_tickets=total, complaints=13, inquiries=3, returns=2,
            open=open_count, resolved=total - open_count,
            resolution_rate_percent=resolution,
            negative_count=15, neutral_count=3, positive_count=0,
            negative_feedback_percent=negative,
            sentiment_missing_count=0, llm_classified_count=0,
            heuristic_classified_count=0,
        ),
        themes=[], recurring_issues=[], top_theme=None,
        delivery=DeliveryFacts(
            total_tickets=8, share_percent=44.44, open_count=6,
            delay_reports=6, avg_reported_delay_days=5.83,
            max_reported_delay_days=10,
        ),
        trend=SupportTrendFact(
            recent_complaints=10, prior_complaints=3,
            complaints_change_percent=complaint_change,
            recent_delivery_issues=6, prior_delivery_issues=2,
            delivery_change_percent=200.0,
        ),
        tickets=[], sample_negative_feedback=[],
    )


def _seed_shaped():
    """The four domain facts in the exact shape the seed data produces."""
    return {
        "finance": _finance(),
        "inventory": _inventory(risk_levels=["critical"] + ["overstock"] * 8),
        "marketing": _marketing(),
        "support": _support(),
    }


# ── Finance sub-score (controlled inputs) ──────────────────────────────────

class TestFinanceSubscore:
    def test_healthy_business_scores_100(self):
        score, components, _ = finance_subscore(_finance(
            decline=0.0, compression=0.0, trend="growing", mom_profit=10.0,
        ))
        assert score == 100
        assert components == []

    def test_seed_shaped_scores_82(self):
        score, components, _ = finance_subscore(_finance())
        assert score == 82
        assert [(c.rule, c.points) for c in components] == [
            ("revenue_decline_from_peak", -8.19),
            ("margin_compression", -4.8),
            ("declining_trend", -5.0),
        ]
        # 100 - 8.19 - 4.8 - 5 = 82.01 -> 82 (half-up)
        assert 100 + sum(c.points for c in components) == pytest.approx(
            82.01, abs=0.001
        )

    def test_deduction_caps(self):
        score, components, _ = finance_subscore(_finance(
            decline=-60.0, compression=20.0, trend="declining",
            mom_profit=-50.0,
        ))
        assert [(c.rule, c.points) for c in components] == [
            ("revenue_decline_from_peak", -25.0),   # 0.5*60=30 capped at 25
            ("margin_compression", -15.0),          # 1.5*20=30 capped at 15
            ("declining_trend", -5.0),
            ("profit_drop_mom", -10.0),             # .25*50=12.5 capped at 10
        ]
        assert score == 45

    def test_small_profit_drop_deducts_quarter_point_per_pct(self):
        score, components, _ = finance_subscore(_finance(
            decline=0.0, compression=0.0, trend="stable", mom_profit=-4.0,
        ))
        assert score == 99
        assert components[0].rule == "profit_drop_mom"
        assert components[0].points == -1.0

    def test_round_half_up_boundaries(self):
        # 100 - 0.5*1 = 99.5 -> 100 (half-up)
        assert finance_subscore(_finance(
            decline=-1.0, compression=0.0, trend="stable", mom_profit=None,
        ))[0] == 100
        # 100 - 0.5*3 = 98.5 -> 99 (half-up)
        assert finance_subscore(_finance(
            decline=-3.0, compression=0.0, trend="stable", mom_profit=None,
        ))[0] == 99

    def test_positive_mom_profit_never_deducts(self):
        score, components, _ = finance_subscore(_finance(
            decline=0.0, compression=0.0, trend="growing", mom_profit=50.0,
        ))
        assert score == 100
        assert not any(c.rule == "profit_drop_mom" for c in components)

    def test_signals_quote_exact_numbers(self):
        _, _, signals = finance_subscore(_finance())
        by_label = {s.label: s for s in signals}
        assert by_label["Revenue vs peak"].value == "-16.38% from Apr peak"
        assert by_label["Revenue vs peak"].direction == "negative"
        assert by_label["Profit margin"].value == "18.35% (-3.20pp vs peak)"
        assert by_label["Profit margin"].direction == "negative"
        assert by_label["Revenue trend"].value == "declining"
        assert by_label["Revenue trend"].direction == "negative"


# ── Inventory sub-score (controlled inputs) ─────────────────────────────────

class TestInventorySubscore:
    def test_no_risks_scores_100(self):
        score, components, _ = inventory_subscore(_inventory())
        assert score == 100
        assert components == []

    def test_seed_shaped_scores_61(self):
        score, components, _ = inventory_subscore(_inventory(
            risk_levels=["critical"] + ["overstock"] * 8
        ))
        assert score == 61
        assert [(c.rule, c.points) for c in components] == [
            ("critical_stockout", -15.0),
            ("overstock", -24.0),      # 8*4=32 capped at 24
        ]

    def test_mixed_risk_levels(self):
        score, components, _ = inventory_subscore(_inventory(risk_levels=[
            "critical", "critical", "out_of_stock", "high",
            "medium", "medium", "medium",
            "overstock", "overstock", "overstock", "overstock",
            "stagnant", "stagnant",
        ]))
        assert [(c.rule, c.points) for c in components] == [
            ("critical_stockout", -30.0),   # 2*15, at cap
            ("out_of_stock", -15.0),
            ("high_risk", -8.0),
            ("medium_risk", -12.0),         # 3*4, at cap
            ("overstock", -16.0),
            ("stagnant", -6.0),
        ]
        assert score == 13

    def test_all_caps_floor_at_zero(self):
        score, _, _ = inventory_subscore(_inventory(risk_levels=(
            ["critical"] * 5 + ["out_of_stock"] * 5 + ["high"] * 3
            + ["medium"] * 5 + ["overstock"] * 10 + ["stagnant"] * 10
        )))
        assert score == 0   # deductions total 124, floored at 0


# ── Marketing sub-score (controlled inputs) ─────────────────────────────────

class TestMarketingSubscore:
    def test_all_acceptable_scores_100(self):
        score, components, _ = marketing_subscore(_marketing(
            perf=["acceptable"], roas=5.0,
        ))
        assert score == 100
        assert components == []

    def test_seed_shaped_scores_96(self):
        score, components, _ = marketing_subscore(_marketing())
        assert score == 96
        assert [(c.rule, c.points) for c in components] == [
            ("underperforming_campaign", -12.0),
            ("outperforming_campaign", 8.0),   # 2*4, at cap
        ]

    def test_bad_marketing(self):
        score, components, _ = marketing_subscore(_marketing(
            perf=["underperforming"] * 4, roas=1.5,
        ))
        assert [(c.rule, c.points) for c in components] == [
            ("underperforming_campaign", -48.0),   # at cap
            ("low_roas", -10.0),
        ]
        assert score == 42

    def test_caps(self):
        score, _, _ = marketing_subscore(_marketing(
            perf=["underperforming"] * 6 + ["outperforming"] * 5, roas=0.5,
        ))
        assert score == 50   # 100 - 48 + 8 - 10

    def test_unknown_roas_does_not_deduct(self):
        score, components, _ = marketing_subscore(_marketing(
            perf=["underperforming"], roas=None,
        ))
        assert score == 88
        assert not any(c.rule == "low_roas" for c in components)

    def test_roas_signal_directions(self):
        _, _, signals = marketing_subscore(_marketing())
        by_label = {s.label: s for s in signals}
        assert by_label["Overall ROAS"].value == "19.97"
        assert by_label["Overall ROAS"].direction == "positive"
        _, _, low = marketing_subscore(_marketing(
            perf=["acceptable"], roas=1.2,
        ))
        assert {
            s.label: s for s in low
        }["Overall ROAS"].direction == "negative"


# ── Support sub-score (controlled inputs) ───────────────────────────────────

class TestSupportSubscore:
    def test_healthy_support_scores_100(self):
        score, components, _ = support_subscore(_support(
            negative=10.0, resolution=95.0, complaint_change=-10.0,
        ))
        assert score == 100
        assert components == []

    def test_seed_shaped_scores_59(self):
        score, components, _ = support_subscore(_support())
        assert score == 59
        assert [(c.rule, c.points) for c in components] == [
            ("negative_feedback", -25.0),    # 0.5*53.33=26.67 capped at 25
            ("low_resolution", -7.67),       # 0.3*25.56=7.668 -> 7.67
            ("complaint_surge", -8.0),       # +233.33% more than doubled
        ]

    def test_deduction_caps(self):
        score, components, _ = support_subscore(_support(
            negative=100.0, resolution=0.0, complaint_change=1000.0,
        ))
        assert [(c.rule, c.points) for c in components] == [
            ("negative_feedback", -25.0),
            ("low_resolution", -10.0),
            ("complaint_surge", -8.0),
        ]
        assert score == 57

    @pytest.mark.parametrize("change,expected", [
        (150.0, 92),    # > +100% -> -8
        (60.0, 94),     # > +50%  -> -6
        (25.0, 97),     # > +20%  -> -3
        (10.0, 100),    # <= +20% -> no deduction
        (None, 100),    # no comparison possible -> no deduction
    ])
    def test_complaint_surge_bands(self, change, expected):
        score, _, _ = support_subscore(_support(
            negative=10.0, resolution=95.0, complaint_change=change,
        ))
        assert score == expected

    def test_baseline_boundaries_do_not_deduct(self):
        score, components, _ = support_subscore(_support(
            negative=30.0, resolution=70.0, complaint_change=None,
        ))
        assert score == 100
        assert components == []

    def test_signals_quote_exact_numbers(self):
        _, _, signals = support_subscore(_support())
        by_label = {s.label: s for s in signals}
        assert by_label["Negative feedback"].value == "83.33% of 18 tickets"
        assert by_label["Negative feedback"].direction == "negative"
        assert by_label["Complaint volume trend"].value == (
            "+233.33% vs prior period"
        )
        assert by_label["Open tickets"].value == "10 of 18 open"
        assert by_label["Open tickets"].direction == "negative"


# ── Composite formula (controlled inputs) ───────────────────────────────────

class TestComputeHealthScore:
    def test_seed_shaped_composite_is_75_moderate(self):
        score, level = compute_health_score(
            {"finance": 82, "inventory": 61, "marketing": 96, "support": 59}
        )
        assert score == 75       # .35*82+.25*61+.2*96+.2*59 = 74.95 -> 75
        assert level == "moderate"

    @pytest.mark.parametrize("subscore,expected_score,expected_level", [
        (100, 100, "low"),
        (80, 80, "low"),       # band boundary
        (79, 79, "moderate"),
        (60, 60, "moderate"),  # band boundary
        (59, 59, "high"),
        (40, 40, "high"),      # band boundary
        (39, 39, "critical"),
        (0, 0, "critical"),
    ])
    def test_risk_bands(self, subscore, expected_score, expected_level):
        score, level = compute_health_score({"finance": subscore})
        assert score == expected_score
        assert level == expected_level

    def test_missing_domain_renormalizes_weights(self):
        # marketing missing: weights 0.35/0.25/0.20 -> /0.80
        # .4375*82 + .3125*61 + .25*59 = 69.6875 -> 70
        score, level = compute_health_score(
            {"finance": 82, "inventory": 61, "support": 59}
        )
        assert score == 70
        assert level == "moderate"

    def test_empty_input_raises(self):
        with pytest.raises(NoBIDataError):
            compute_health_score({})

    def test_risk_level_function(self):
        assert risk_level(100) == "low"
        assert risk_level(80) == "low"
        assert risk_level(79) == "moderate"
        assert risk_level(60) == "moderate"
        assert risk_level(59) == "high"
        assert risk_level(40) == "high"
        assert risk_level(39) == "critical"
        assert risk_level(0) == "critical"


# ── Seed integration (full pipeline) ────────────────────────────────────────

class TestSeedIntegration:
    def test_health_score_matches_hand_computation(self, db):
        facts = get_bi_snapshot(db)
        hs = facts.health_score
        assert hs.score == 75
        assert hs.risk_level == "moderate"
        assert hs.weakest_domain == "support"
        assert hs.strongest_domain == "marketing"

    def test_domain_scores(self, db):
        hs = get_bi_snapshot(db).health_score
        scores = {ds.domain: ds.score for ds in hs.domain_scores}
        assert scores == {
            "finance": 82, "inventory": 61, "marketing": 96, "support": 59,
        }
        weights = {ds.domain: ds.weight for ds in hs.domain_scores}
        assert weights == {
            "finance": 0.35, "inventory": 0.25,
            "marketing": 0.2, "support": 0.2,
        }
        assert all(ds.data_available for ds in hs.domain_scores)

    def test_domain_components_quote_real_numbers(self, db):
        hs = get_bi_snapshot(db).health_score
        by_domain = {ds.domain: ds for ds in hs.domain_scores}
        fin = by_domain["finance"]
        assert fin.components[0].reason.startswith(
            "Revenue is -16.38% from the Apr peak"
        )
        sup = by_domain["support"]
        assert "83.33%" in sup.components[0].reason

    def test_formula_string(self, db):
        hs = get_bi_snapshot(db).health_score
        assert "35% Finance (82)" in hs.formula
        assert "25% Inventory (61)" in hs.formula
        assert "20% Marketing (96)" in hs.formula
        assert "20% Support (59)" in hs.formula
        assert "= 75 (moderate risk)" in hs.formula

    def test_coverage_and_signals(self, db):
        facts = get_bi_snapshot(db)
        assert facts.included_domains == [
            "finance", "inventory", "marketing", "support",
        ]
        assert facts.missing_domains == []
        assert facts.as_of_date == "2026-08-28"

        by_key = {(s.domain, s.label): s for s in facts.key_signals}
        assert len(facts.key_signals) == 12
        assert sum(1 for s in facts.key_signals if s.direction == "negative") == 9

        assert by_key[("finance", "Revenue vs peak")].value == (
            "-16.38% from Apr peak"
        )
        assert by_key[("inventory", "Critical stock-out risks")].value == (
            "1 product(s)"
        )
        assert by_key[("inventory", "Reorder recommendation")].value.startswith(
            "66 units"
        )
        assert by_key[("marketing", "Underperforming campaigns")].value == (
            "1: Khan Fabrics Counter"
        )
        assert by_key[("marketing", "Outperforming campaigns")].value == (
            "2: Eid Preview Teasers, Digital Lookbook"
        )
        assert by_key[("marketing", "Overall ROAS")].value == "19.97"
        assert by_key[("support", "Negative feedback")].value == (
            "83.33% of 18 tickets"
        )
        assert by_key[("support", "Complaint volume trend")].value == (
            "+233.33% vs prior period"
        )
        assert by_key[("support", "Open tickets")].value == "10 of 18 open"

    def test_nested_agent_facts_embedded_verbatim(self, db):
        """BI never re-derives raw facts — they come from the agents."""
        facts = get_bi_snapshot(db)
        assert facts.finance.revenue.current_revenue == 4_850_000.0
        assert facts.inventory.summary.critical_count == 1
        assert facts.marketing.underperforming_campaign_names == [
            "Khan Fabrics Counter"
        ]
        assert facts.support.summary.total_tickets == 18

    def test_score_is_reproducible(self, db):
        first = get_bi_snapshot(db).health_score
        second = get_bi_snapshot(db).health_score
        assert first.score == second.score == 75
        assert first.risk_level == second.risk_level

    def test_pure_formula_matches_pipeline(self, db):
        hs = get_bi_snapshot(db).health_score
        scores = {ds.domain: ds.score for ds in hs.domain_scores}
        assert compute_health_score(scores) == (hs.score, hs.risk_level)

    def test_facts_json_serializable_for_ceo_agent(self, db):
        data = get_bi_snapshot(db).model_dump()
        assert data["business_name"] == "Ali Garments"
        assert data["health_score"]["score"] == 75
        assert data["health_score"]["weakest_domain"] == "support"
        assert isinstance(data["key_signals"], list)
        assert data["finance"]["revenue"]["current_revenue"] == 4_850_000.0


# ── Missing-domain and failure handling ────────────────────────────────────

class TestMissingDomains:
    def test_marketing_unavailable_renormalizes(self, db, monkeypatch):
        import app.services.bi as bi_service
        from app.services.marketing import MarketingDataError

        def _raise(db_):
            raise MarketingDataError("no campaigns")

        monkeypatch.setitem(
            bi_service._LOADERS, "marketing",
            (_raise, MarketingDataError),
        )
        facts = get_bi_snapshot(db)
        assert facts.missing_domains == ["marketing"]
        assert facts.included_domains == [
            "finance", "inventory", "support",
        ]
        assert facts.marketing is None
        # .35/.8=.4375, .25/.8=.3125, .20/.8=.25 -> 70 (moderate)
        assert facts.health_score.score == 70
        assert facts.health_score.risk_level == "moderate"
        weights = {ds.domain: ds.weight for ds in facts.health_score.domain_scores}
        assert weights == {
            "finance": 0.4375, "inventory": 0.3125, "support": 0.25,
        }
        coverage = [s for s in facts.key_signals if s.domain == "bi"]
        assert len(coverage) == 1
        assert "marketing data unavailable" in coverage[0].value

    def test_all_domains_unavailable_raises(self, db, monkeypatch):
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
            get_bi_snapshot(db)

    def test_missing_business_raises(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            with pytest.raises(BusinessNotFoundError):
                get_bi_snapshot(session)
        finally:
            session.close()


# ── Full agent response ─────────────────────────────────────────────────────

class TestBIAgent:
    def test_agent_registered(self):
        assert "bi_agent" in AGENT_REGISTRY
        assert isinstance(AGENT_REGISTRY["bi_agent"], BIAgent)

    def test_agent_metadata_intact(self):
        info = AGENT_REGISTRY["bi_agent"].info()
        assert info.name == "BI Agent"
        assert info.status == "active"
        assert "Business Health Score computation" in info.tasks

    def test_analyze_returns_valid_response(self, db):
        agent = AGENT_REGISTRY["bi_agent"]
        response = agent.analyze(db)
        assert response.agent == "BI Agent"
        assert response.facts.health_score.score == 75
        assert response.interpretation_source in ("llm", "fallback")
        assert len(response.interpretation) > 50
        assert response.generated_at

    def test_fallback_interpretation_uses_only_computed_facts(self, db):
        """The deterministic fallback must quote the computed numbers."""
        agent = AGENT_REGISTRY["bi_agent"]
        facts = get_bi_snapshot(db)
        text = agent._fallback_interpretation(facts)

        assert "75/100" in text                    # computed score
        assert "moderate risk" in text             # computed risk level
        assert "Support (59/100)" in text          # weakest domain
        assert "Marketing (96/100)" in text        # strongest domain
        assert "83.33% of 18 tickets" in text      # real support signal
        assert "Khan Fabrics Counter" in text      # real marketing signal
        assert "-16.38%" in text                   # real finance signal
        assert "Most important action" in text
        assert "delivery complaints" in text       # action follows weakest

    def test_llm_not_configured_returns_none(self, db, monkeypatch):
        """With no API key the interpreter must short-circuit to None."""
        from app.config import settings
        from app.services import llm as llm_service

        facts = get_bi_snapshot(db)
        monkeypatch.setattr(settings, "gemini_api_key", "")
        assert llm_service.is_llm_configured() is False
        assert llm_service.interpret_bi_facts(facts) is None

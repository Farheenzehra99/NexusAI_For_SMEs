"""
Inventory Agent deterministic calculation tests.

Every expected value is derived from the canonical seed data in
backend/seed.py (Ali Garments demo):

    Products (15 active): stock, price, cost, reorder thresholds are fixed.
    Daily sales: Aug 1-31 2026, deterministic (random.Random(42)).

Key hand-verifiable expectations:
    - Embroidered Kurti — White (AG-KT-001): stock 5, threshold 20,
      ~218 sales over 6 months → the best seller with critical stock-out
      risk and a positive reorder recommendation.
    - Formal Shalwar — Navy (AG-SK-001): stock 480 vs slow velocity →
      overstock with excess units beyond the 180-day horizon.
    - Total stock retail value: Rs 9,114,100 (sum of stock x price).

Velocity expectations are computed from the database with the same window
the service uses, proving the formula (units sold / window days).
"""

import math
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.business import Business, Product, DailySale
from app.services.inventory import (
    get_inventory_snapshot,
    InvalidRangeError,
    BusinessNotFoundError,
    NoSalesDataError,
    CRITICAL_DAYS,
    TARGET_COVERAGE_DAYS,
    OVERSTOCK_DAYS,
)
from app.agents.inventory import InventoryAgent
from app.agents.base import AGENT_REGISTRY

EXPECTED_TOTAL_STOCK_VALUE = 9_114_100  # hand-computed from seed products


def _product_by_sku(facts, sku):
    return next(f for f in facts.products if f.sku == sku)


def _expected_velocity(db, sku, window_days):
    """Compute velocity the same way the service must: units sold in the
    trailing window divided by the window length."""
    prod = db.query(Product).filter(Product.sku == sku).first()
    as_of = db.query(func.max(DailySale.date)).scalar()
    first = db.query(func.min(DailySale.date)).scalar()
    effective = min(window_days, (as_of - first).days + 1)
    cutoff = as_of - timedelta(days=effective - 1)
    sold = (
        db.query(func.sum(DailySale.qty_sold))
        .filter(
            DailySale.product_id == prod.id,
            DailySale.date >= cutoff,
            DailySale.date <= as_of,
        )
        .scalar()
    ) or 0
    return sold / effective, effective


# ── Validation and failure handling ─────────────────────────────────────────

class TestValidation:
    def test_days_below_minimum_rejected(self, db):
        with pytest.raises(InvalidRangeError):
            get_inventory_snapshot(db, days=6)

    def test_days_above_maximum_rejected(self, db):
        with pytest.raises(InvalidRangeError):
            get_inventory_snapshot(db, days=91)

    def test_days_boundaries_accepted(self, db):
        assert get_inventory_snapshot(db, days=7) is not None
        assert get_inventory_snapshot(db, days=90) is not None

    def test_missing_business_raises(self):
        """An empty database must fail loudly, not return fake zeros."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            with pytest.raises(BusinessNotFoundError):
                get_inventory_snapshot(session, days=30)
        finally:
            session.close()

    def test_business_without_sales_data_raises(self):
        """A business with no daily sales cannot have velocity computed."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            session.add(Business(name="Empty Co", owner_name="X"))
            session.commit()
            with pytest.raises(NoSalesDataError):
                get_inventory_snapshot(session, days=30)
        finally:
            session.close()


# ── Snapshot basics ─────────────────────────────────────────────────────────

class TestSnapshotBasics:
    def test_all_active_products_present(self, db):
        facts = get_inventory_snapshot(db, days=30)
        assert facts.summary.total_active_products == 15
        assert len(facts.products) == 15

    def test_as_of_date_is_latest_daily_sale(self, db):
        facts = get_inventory_snapshot(db, days=30)
        assert facts.as_of_date == "2026-08-31"

    def test_window_shrinks_to_available_data(self, db):
        """Only 31 days of data exist — a 90-day request must use 31."""
        facts = get_inventory_snapshot(db, days=90)
        assert facts.velocity_window_days == 31

    def test_requested_window_used_when_data_sufficient(self, db):
        facts = get_inventory_snapshot(db, days=30)
        assert facts.velocity_window_days == 30

    def test_total_stock_value_matches_seed(self, db):
        facts = get_inventory_snapshot(db, days=30)
        assert facts.summary.total_stock_value_retail == pytest.approx(
            EXPECTED_TOTAL_STOCK_VALUE, abs=0.01
        )

    def test_stock_value_formula_per_product(self, db):
        facts = get_inventory_snapshot(db, days=30)
        for f in facts.products:
            assert f.stock_value_retail == pytest.approx(
                f.current_stock * f.price, abs=0.01
            )


# ── Velocity calculations ───────────────────────────────────────────────────

class TestVelocity:
    def test_kurti_white_velocity_matches_formula(self, db):
        facts = get_inventory_snapshot(db, days=30)
        expected_velocity, _ = _expected_velocity(db, "AG-KT-001", 30)
        fact = _product_by_sku(facts, "AG-KT-001")
        assert fact.velocity_units_per_day == pytest.approx(expected_velocity, abs=0.0001)

    def test_weekly_velocity_is_daily_times_seven(self, db):
        facts = get_inventory_snapshot(db, days=30)
        for f in facts.products:
            assert f.velocity_units_per_week == pytest.approx(
                f.velocity_units_per_day * 7, abs=0.01
            )

    def test_every_product_has_nonnegative_velocity(self, db):
        facts = get_inventory_snapshot(db, days=30)
        assert all(f.velocity_units_per_day >= 0 for f in facts.products)

    def test_formal_navy_velocity_matches_formula(self, db):
        facts = get_inventory_snapshot(db, days=30)
        expected_velocity, _ = _expected_velocity(db, "AG-SK-001", 30)
        fact = _product_by_sku(facts, "AG-SK-001")
        assert fact.velocity_units_per_day == pytest.approx(expected_velocity, abs=0.0001)


# ── Days of stock remaining ─────────────────────────────────────────────────

class TestDaysRemaining:
    def test_days_remaining_formula(self, db):
        facts = get_inventory_snapshot(db, days=30)
        for f in facts.products:
            if f.velocity_units_per_day > 0:
                assert f.days_of_stock_remaining == pytest.approx(
                    f.current_stock / f.velocity_units_per_day, abs=0.01
                )
            else:
                assert f.days_of_stock_remaining is None

    def test_kurti_white_stock_out_imminent(self, db):
        facts = get_inventory_snapshot(db, days=30)
        fact = _product_by_sku(facts, "AG-KT-001")
        assert fact.current_stock == 5
        assert fact.days_of_stock_remaining < CRITICAL_DAYS  # under a week


# ── Risk classification ─────────────────────────────────────────────────────

class TestRiskClassification:
    def test_kurti_white_is_critical(self, db):
        facts = get_inventory_snapshot(db, days=30)
        fact = _product_by_sku(facts, "AG-KT-001")
        assert fact.risk_level == "critical"
        assert fact.below_reorder_level is True  # 5 <= threshold 20

    def test_kurti_white_is_the_only_critical_product(self, db):
        facts = get_inventory_snapshot(db, days=30)
        assert facts.summary.critical_count == 1
        assert facts.summary.at_risk_count >= 1

    def test_formal_navy_is_overstock(self, db):
        facts = get_inventory_snapshot(db, days=30)
        fact = _product_by_sku(facts, "AG-SK-001")
        assert fact.risk_level == "overstock"
        assert fact.days_of_stock_remaining > OVERSTOCK_DAYS

    def test_overstock_excess_formula(self, db):
        facts = get_inventory_snapshot(db, days=30)
        fact = _product_by_sku(facts, "AG-SK-001")
        expected_excess = fact.current_stock - math.ceil(
            fact.velocity_units_per_day * OVERSTOCK_DAYS
        )
        assert fact.excess_stock_qty == max(expected_excess, 0)
        assert fact.excess_stock_qty > 0  # 480 units vs slow sales

    def test_products_sorted_by_severity(self, db):
        facts = get_inventory_snapshot(db, days=30)
        order = {
            "out_of_stock": 0, "critical": 1, "high": 2, "medium": 3,
            "overstock": 4, "stagnant": 5, "adequate": 6,
        }
        ranks = [order[f.risk_level] for f in facts.products]
        assert ranks == sorted(ranks)
        # The best seller with 5 units must lead the list
        assert facts.products[0].sku == "AG-KT-001"

    def test_risks_list_excludes_adequate(self, db):
        facts = get_inventory_snapshot(db, days=30)
        assert all(r.risk_level != "adequate" for r in facts.risks)
        assert len(facts.risks) == facts.summary.total_active_products - sum(
            1 for f in facts.products if f.risk_level == "adequate"
        )


# ── Reorder recommendations ─────────────────────────────────────────────────

class TestReorderRecommendations:
    def test_kurti_white_reorder_formula(self, db):
        facts = get_inventory_snapshot(db, days=30)
        fact = _product_by_sku(facts, "AG-KT-001")
        expected = max(
            math.ceil(fact.velocity_units_per_day * TARGET_COVERAGE_DAYS)
            - fact.current_stock,
            0,
        )
        assert fact.recommended_reorder_qty == expected
        assert fact.recommended_reorder_qty > 0  # must recommend restocking

    def test_adequate_products_need_no_reorder(self, db):
        facts = get_inventory_snapshot(db, days=30)
        for f in facts.products:
            if f.risk_level in ("adequate", "overstock", "stagnant"):
                assert f.recommended_reorder_qty == 0

    def test_summary_reorder_totals_are_consistent(self, db):
        facts = get_inventory_snapshot(db, days=30)
        s = facts.summary
        assert s.recommended_reorder_units == sum(
            f.recommended_reorder_qty for f in facts.products
        )
        assert s.recommended_reorder_cost == pytest.approx(
            sum(f.recommended_reorder_qty * f.cost for f in facts.products), abs=0.01
        )

    def test_excess_value_total_consistent(self, db):
        facts = get_inventory_snapshot(db, days=30)
        expected = sum(f.excess_stock_qty * f.price for f in facts.products)
        assert facts.summary.excess_stock_value_retail == pytest.approx(expected, abs=0.01)


# ── Risk reasons quote computed numbers ─────────────────────────────────────

class TestRiskReasons:
    def test_critical_reason_contains_stock_and_days(self, db):
        facts = get_inventory_snapshot(db, days=30)
        item = next(r for r in facts.risks if r.sku == "AG-KT-001")
        assert "5 units" in item.reason
        assert "days" in item.reason
        assert "20" in item.reason  # reorder threshold

    def test_overstock_reason_contains_excess_value(self, db):
        facts = get_inventory_snapshot(db, days=30)
        item = next(r for r in facts.risks if r.sku == "AG-SK-001")
        assert "480 units" in item.reason

    def test_all_risks_have_reasons(self, db):
        facts = get_inventory_snapshot(db, days=30)
        for r in facts.risks:
            assert r.reason


# ── Full agent response ─────────────────────────────────────────────────────

class TestInventoryAgent:
    def test_agent_registered(self):
        assert "inventory_agent" in AGENT_REGISTRY
        assert isinstance(AGENT_REGISTRY["inventory_agent"], InventoryAgent)

    def test_agent_metadata_intact(self):
        info = AGENT_REGISTRY["inventory_agent"].info()
        assert info.name == "Inventory Agent"
        assert info.status == "active"
        assert "Stock monitoring" in info.tasks

    def test_analyze_returns_valid_response(self, db):
        agent = AGENT_REGISTRY["inventory_agent"]
        response = agent.analyze(db, days=30)
        assert response.agent == "Inventory Agent"
        assert response.facts.summary.total_active_products == 15
        assert response.interpretation_source in ("llm", "fallback")
        assert len(response.interpretation) > 50
        assert response.generated_at

    def test_fallback_interpretation_uses_only_facts(self, db):
        """The deterministic fallback must quote the real computed numbers."""
        agent = AGENT_REGISTRY["inventory_agent"]
        facts = get_inventory_snapshot(db, days=30)
        text = agent._fallback_interpretation(facts)

        kurti = _product_by_sku(facts, "AG-KT-001")
        navy = _product_by_sku(facts, "AG-SK-001")
        assert "Embroidered Kurti" in text
        assert f"{kurti.recommended_reorder_qty} units" in text
        assert "Formal Shalwar" in text
        assert f"{facts.summary.total_stock_value_retail:,.0f}" in text
        assert f"{navy.excess_stock_qty}" in text

    def test_facts_json_serializable_for_ceo_agent(self, db):
        """The CEO Agent must be able to consume these facts as JSON."""
        facts = get_inventory_snapshot(db, days=30)
        data = facts.model_dump()
        assert data["business_name"] == "Ali Garments"
        assert data["as_of_date"] == "2026-08-31"
        assert isinstance(data["risks"], list)
        assert data["summary"]["total_active_products"] == 15

    def test_llm_not_configured_returns_none(self, db, monkeypatch):
        """With no API key the interpreter must short-circuit to None."""
        from app.config import settings
        from app.services import llm as llm_service

        facts = get_inventory_snapshot(db, days=30)
        monkeypatch.setattr(settings, "gemini_api_key", "")
        assert llm_service.is_llm_configured() is False
        assert llm_service.interpret_inventory_facts(facts) is None

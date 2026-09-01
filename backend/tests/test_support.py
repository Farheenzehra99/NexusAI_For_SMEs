"""
Customer Support Agent deterministic calculation tests.

Every expected value below was derived by hand from the canonical seed
data in backend/seed.py (Ali Garments demo, 18 tickets, Aug 3-28 2026):

    Type counts:   13 complaints, 3 inquiries, 2 returns        = 18 total
    Status:        10 open, 8 resolved → resolution rate 44.44 %
    Sentiment:     15 negative, 3 neutral, 0 positive
                   → negative feedback percentage 15/18 = 83.33 %

    Themes (priority: delivery → wrong item → quality → inquiry → other):
        delivery_problems       8 tickets  (44.44 %)  8 neg, 6 open
        product_quality         4 tickets  (22.22 %)  4 neg, 2 open
        general_inquiry         3 tickets  (16.67 %)  0 neg, 0 open
        wrong_item_fulfillment  3 tickets  (16.67 %)  3 neg, 2 open

    Delivery deep-dive:
        6 tickets quote an explicit "delayed by N days" figure:
        3, 5, 7, 10, 6, 4  →  avg 35/6 = 5.83, max 10

    Trend (recent half Aug 14-28 vs prior half, window 30 → half 15 days):
        complaints 3 → 10  = +233.33 %
        delivery   2 → 6   = +200.0 %
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.business import Business, SupportTicket
from app.services.support import (
    get_support_snapshot,
    BusinessNotFoundError,
    NoTicketDataError,
    InvalidRangeError,
)
from app.agents.customer_support import CustomerSupportAgent
from app.agents.base import AGENT_REGISTRY


def _ticket(description, **kwargs):
    defaults = dict(
        ticket_type="complaint",
        status="open",
        sentiment="negative",
        channel="phone",
        created_at=datetime(2026, 8, 20, 12, 0),
    )
    defaults.update(kwargs)
    return SupportTicket(description=description, **defaults)


def _make_db_with_tickets(*tickets):
    """In-memory database with one business and the given tickets."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(Business(name="Test Co", owner_name="Owner"))
    session.commit()
    for t in tickets:
        t.business_id = 1
        session.add(t)
    session.commit()
    return session


def _theme(facts, name):
    return next(t for t in facts.themes if t.theme == name)


# ── Validation and missing data ─────────────────────────────────────────────

class TestValidation:
    def test_missing_business_raises(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            with pytest.raises(BusinessNotFoundError):
                get_support_snapshot(session)
        finally:
            session.close()

    def test_business_without_tickets_raises(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            session.add(Business(name="Empty Co", owner_name="Owner"))
            session.commit()
            with pytest.raises(NoTicketDataError):
                get_support_snapshot(session)
        finally:
            session.close()

    def test_untimestamped_tickets_raise(self):
        """Tickets with NULL created_at cannot be windowed → data error."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            session.add(Business(name="No Dates Co", owner_name="Owner"))
            session.commit()
            session.execute(text(
                "INSERT INTO support_tickets (business_id, customer_name, "
                "ticket_type, status, sentiment, description, channel, "
                "created_at, resolved_at) VALUES "
                "(1, 'Ghost', 'complaint', 'open', 'negative', "
                "'No timestamp', 'phone', NULL, NULL)"
            ))
            session.commit()
            with pytest.raises(NoTicketDataError):
                get_support_snapshot(session)
        finally:
            session.close()

    @pytest.mark.parametrize("days", [6, 0, -1, 91, 365])
    def test_invalid_window_raises(self, db, days):
        with pytest.raises(InvalidRangeError):
            get_support_snapshot(db, days=days)


# ── Summary against the canonical seed data ────────────────────────────────

class TestSeedSummary:
    def test_summary_counts_match_seed(self, db):
        s = get_support_snapshot(db).summary
        assert s.total_tickets == 18
        assert s.complaints == 13
        assert s.inquiries == 3
        assert s.returns == 2
        assert s.open == 10
        assert s.resolved == 8

    def test_resolution_rate(self, db):
        s = get_support_snapshot(db).summary
        assert s.resolution_rate_percent == pytest.approx(8 / 18 * 100, abs=0.01)
        assert s.resolution_rate_percent == 44.44

    def test_negative_feedback_percentage(self, db):
        s = get_support_snapshot(db).summary
        assert s.negative_count == 15
        assert s.neutral_count == 3
        assert s.positive_count == 0
        assert s.negative_feedback_percent == pytest.approx(
            15 / 18 * 100, abs=0.01
        )
        assert s.negative_feedback_percent == 83.33

    def test_all_seed_sentiments_stored_no_classification_needed(self, db):
        s = get_support_snapshot(db).summary
        assert s.sentiment_missing_count == 0
        assert s.llm_classified_count == 0
        assert s.heuristic_classified_count == 0

    def test_window_metadata(self, db):
        facts = get_support_snapshot(db)
        assert facts.business_name == "Ali Garments"
        assert facts.currency == "PKR"
        assert facts.as_of_date == "2026-08-28"  # newest ticket date
        assert facts.window_days == 30


# ── Theme detection ─────────────────────────────────────────────────────────

class TestThemes:
    def test_theme_counts_and_order(self, db):
        facts = get_support_snapshot(db)
        assert [t.theme for t in facts.themes] == [
            "delivery_problems",
            "product_quality",
            "general_inquiry",
            "wrong_item_fulfillment",
        ]
        assert [t.count for t in facts.themes] == [8, 4, 3, 3]

    def test_theme_shares(self, db):
        facts = get_support_snapshot(db)
        assert _theme(facts, "delivery_problems").share_percent == 44.44
        assert _theme(facts, "product_quality").share_percent == 22.22
        assert _theme(facts, "general_inquiry").share_percent == 16.67
        assert _theme(facts, "wrong_item_fulfillment").share_percent == 16.67

    def test_theme_negative_and_open_counts(self, db):
        facts = get_support_snapshot(db)
        d = _theme(facts, "delivery_problems")
        assert d.negative_count == 8
        assert d.open_count == 6
        q = _theme(facts, "product_quality")
        assert q.negative_count == 4
        assert q.open_count == 2
        i = _theme(facts, "general_inquiry")
        assert i.negative_count == 0
        assert i.open_count == 0

    def test_recurring_issues_and_top_theme(self, db):
        facts = get_support_snapshot(db)
        assert facts.top_theme == "delivery_problems"
        # every seed theme has >= 2 tickets → all recurring
        assert [t.theme for t in facts.recurring_issues] == [
            "delivery_problems",
            "product_quality",
            "general_inquiry",
            "wrong_item_fulfillment",
        ]

    def test_delivery_example_is_newest_delivery_ticket(self, db):
        facts = get_support_snapshot(db)
        assert _theme(facts, "delivery_problems").example_description == (
            "Delivery delayed by 4 days — order #AG-4740"
        )

    def test_theme_priority_delivery_beats_wrong_item(self):
        session = _make_db_with_tickets(_ticket(
            "Wrong size delivered — delayed by 3 days too"
        ))
        try:
            facts = get_support_snapshot(session)
            assert _theme(facts, "delivery_problems").count == 1
            # wrong_item theme is absent entirely (0 tickets)
            assert not any(
                t.theme == "wrong_item_fulfillment" for t in facts.themes
            )
        finally:
            session.close()

    def test_theme_priority_wrong_item_beats_quality(self):
        session = _make_db_with_tickets(_ticket(
            "Wrong color delivered — fabric quality is also poor"
        ))
        try:
            facts = get_support_snapshot(session)
            assert _theme(facts, "wrong_item_fulfillment").count == 1
            assert not any(
                t.theme == "product_quality" for t in facts.themes
            )
        finally:
            session.close()

    def test_inquiry_theme_requires_inquiry_type(self):
        session = _make_db_with_tickets(_ticket(
            "Where is my order?", ticket_type="complaint"
        ))
        try:
            facts = get_support_snapshot(session)
            assert _theme(facts, "other").count == 1
        finally:
            session.close()


# ── Delivery deep-dive ──────────────────────────────────────────────────────

class TestDelivery:
    def test_delivery_facts_match_seed(self, db):
        d = get_support_snapshot(db).delivery
        assert d.total_tickets == 8
        assert d.share_percent == 44.44
        assert d.open_count == 6
        assert d.delay_reports == 6
        assert d.avg_reported_delay_days == pytest.approx(35 / 6, abs=0.01)
        assert d.avg_reported_delay_days == 5.83
        assert d.max_reported_delay_days == 10

    def test_no_delivery_tickets_gives_empty_facts(self):
        session = _make_db_with_tickets(_ticket(
            "Embroidery came loose", ticket_type="return"
        ))
        try:
            d = get_support_snapshot(session).delivery
            assert d.total_tickets == 0
            assert d.share_percent == 0.0
            assert d.delay_reports == 0
            assert d.avg_reported_delay_days is None
            assert d.max_reported_delay_days is None
        finally:
            session.close()


# ── Trend ───────────────────────────────────────────────────────────────────

class TestTrend:
    def test_trend_matches_seed(self, db):
        t = get_support_snapshot(db).trend
        assert t.recent_complaints == 10
        assert t.prior_complaints == 3
        assert t.complaints_change_percent == 233.33
        assert t.recent_delivery_issues == 6
        assert t.prior_delivery_issues == 2
        assert t.delivery_change_percent == 200.0

    def test_zero_prior_gives_none_change(self):
        session = _make_db_with_tickets(
            _ticket("Late", created_at=datetime(2026, 8, 20)),
            _ticket("Also late", created_at=datetime(2026, 8, 25)),
        )
        try:
            t = get_support_snapshot(session, days=30).trend
            assert t.prior_complaints == 0
            assert t.complaints_change_percent is None
            assert t.delivery_change_percent is None
        finally:
            session.close()


# ── Original feedback preservation (no fabrication) ────────────────────────

class TestVerbatimPreservation:
    def test_every_description_matches_database_exactly(self, db):
        """Facts must carry the ORIGINAL wording, character for character."""
        facts = get_support_snapshot(db)
        db_descriptions = {
            t.id: t.description
            for t in db.query(SupportTicket).filter_by(business_id=1).all()
        }
        assert len(facts.tickets) == 18
        for ticket_fact in facts.tickets:
            assert ticket_fact.description == db_descriptions[ticket_fact.id]

    def test_tickets_sorted_newest_first(self, db):
        facts = get_support_snapshot(db)
        dates = [t.created_at for t in facts.tickets]
        assert dates == sorted(dates, reverse=True)
        assert facts.tickets[0].id == 18  # Aug 28 stitching complaint

    def test_age_days_only_for_open_tickets(self, db):
        facts = get_support_snapshot(db)
        by_id = {t.id: t for t in facts.tickets}
        assert by_id[18].age_days == 0          # open, Aug 28 (as_of date)
        assert by_id[8].age_days == 9           # open since Aug 19
        assert by_id[1].age_days is None        # resolved tickets have no age
        assert by_id[1].resolved_at is not None

    def test_sample_negative_feedback_is_verbatim_and_capped(self, db):
        facts = get_support_snapshot(db)
        assert len(facts.sample_negative_feedback) == 5  # capped at 5
        assert facts.sample_negative_feedback[0] == (
            "Embroidery stitching is loose — Kurti White"
        )
        all_descriptions = {t.description for t in facts.tickets}
        for quote in facts.sample_negative_feedback:
            assert quote in all_descriptions  # nothing invented

    def test_quotes_are_never_neutral_messages(self, db):
        facts = get_support_snapshot(db)
        neutral = {t.id for t in facts.tickets if t.sentiment == "neutral"}
        for quote in facts.sample_negative_feedback:
            matching = [
                t for t in facts.tickets if t.description == quote
            ]
            assert all(t.id not in neutral for t in matching)


# ── Sentiment completion (LLM only where stored sentiment is missing) ──────

class TestSentimentCompletion:
    def test_llm_classifies_missing_sentiments_in_order(self, monkeypatch):
        # NOTE: sentiment="" (not None) — the ORM column default would
        # coerce an explicit None back to "negative" at INSERT time.
        session = _make_db_with_tickets(
            _ticket("Delivery delayed by 3 days", sentiment="",
                    ticket_type="complaint",
                    created_at=datetime(2026, 8, 10)),
            _ticket("When will my order arrive?", sentiment="",
                    ticket_type="inquiry",
                    created_at=datetime(2026, 8, 20)),
        )
        try:
            from app.services import llm as llm_service
            monkeypatch.setattr(
                llm_service, "classify_sentiments",
                lambda messages: ["positive", "negative"],
            )
            facts = get_support_snapshot(session)
            s = facts.summary
            assert s.sentiment_missing_count == 2
            assert s.llm_classified_count == 2
            assert s.heuristic_classified_count == 0
            assert s.negative_count == 1
            assert s.positive_count == 1
            # labels are applied newest-first, in the order given
            by_day = {t.created_at.day: t for t in facts.tickets}
            assert by_day[20].sentiment == "positive"
            assert by_day[20].sentiment_source == "llm"
            assert by_day[10].sentiment == "negative"
            assert by_day[10].sentiment_source == "llm"
        finally:
            session.close()

    def test_llm_failure_falls_back_to_heuristic(self, monkeypatch):
        session = _make_db_with_tickets(
            _ticket("Delivery delayed by 3 days", sentiment="unrated",
                    ticket_type="complaint",
                    created_at=datetime(2026, 8, 10)),
            _ticket("When will my order arrive?", sentiment="unrated",
                    ticket_type="inquiry",
                    created_at=datetime(2026, 8, 20)),
            _ticket("Color different from website", sentiment="unrated",
                    ticket_type="return",
                    created_at=datetime(2026, 8, 25)),
        )
        try:
            from app.services import llm as llm_service
            monkeypatch.setattr(
                llm_service, "classify_sentiments",
                lambda messages: None,  # total LLM failure
            )
            s = get_support_snapshot(session).summary
            assert s.sentiment_missing_count == 3
            assert s.llm_classified_count == 0
            assert s.heuristic_classified_count == 3
            # heuristic: inquiry → neutral, everything else → negative
            assert s.negative_count == 2
            assert s.neutral_count == 1
        finally:
            session.close()

    def test_null_sentiment_via_raw_sql_is_classified(self, monkeypatch):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            session.add(Business(name="Null Co", owner_name="Owner"))
            session.commit()
            session.execute(text(
                "INSERT INTO support_tickets (business_id, customer_name, "
                "ticket_type, status, sentiment, description, channel, "
                "created_at, resolved_at) VALUES "
                "(1, 'Ghost', 'complaint', 'open', NULL, "
                "'Package lost in transit', 'phone', "
                "'2026-08-22 10:00:00', NULL)"
            ))
            session.commit()
            from app.services import llm as llm_service
            monkeypatch.setattr(
                llm_service, "classify_sentiments",
                lambda messages: ["negative"],
            )
            s = get_support_snapshot(session).summary
            assert s.sentiment_missing_count == 1
            assert s.llm_classified_count == 1
            assert s.negative_count == 1
        finally:
            session.close()

    def test_llm_never_called_when_all_sentiments_stored(self, db, monkeypatch):
        from app.services import llm as llm_service

        def _boom(messages):
            raise AssertionError("LLM must not be called for stored sentiment")

        monkeypatch.setattr(llm_service, "classify_sentiments", _boom)
        s = get_support_snapshot(db).summary  # must not raise
        assert s.sentiment_missing_count == 0

    def test_stored_sentiment_never_overwritten(self, monkeypatch):
        session = _make_db_with_tickets(
            _ticket("Delivery delayed by 3 days", sentiment="neutral",
                    created_at=datetime(2026, 8, 10)),
        )
        try:
            from app.services import llm as llm_service
            monkeypatch.setattr(
                llm_service, "classify_sentiments",
                lambda messages: ["negative"],
            )
            facts = get_support_snapshot(session)
            assert facts.tickets[0].sentiment == "neutral"
            assert facts.tickets[0].sentiment_source == "stored"
        finally:
            session.close()


# ── classify_sentiments response parsing ────────────────────────────────────

class TestClassifySentimentsParsing:
    def _patch_chat(self, monkeypatch, reply):
        from app.services import llm as llm_service
        monkeypatch.setattr(llm_service, "_chat", lambda sp, uc: reply)

    def test_plain_json_array(self, monkeypatch):
        from app.services import llm as llm_service
        self._patch_chat(monkeypatch, '["negative", "neutral", "positive"]')
        assert llm_service.classify_sentiments(["a", "b", "c"]) == [
            "negative", "neutral", "positive"
        ]

    def test_markdown_fenced_json_array(self, monkeypatch):
        from app.services import llm as llm_service
        self._patch_chat(monkeypatch, '```json\n["negative", "neutral"]\n```')
        assert llm_service.classify_sentiments(["a", "b"]) == [
            "negative", "neutral"
        ]

    def test_labels_are_normalized_to_lowercase(self, monkeypatch):
        from app.services import llm as llm_service
        self._patch_chat(monkeypatch, '["NEGATIVE", " Neutral "]')
        assert llm_service.classify_sentiments(["a", "b"]) == [
            "negative", "neutral"
        ]

    def test_wrong_length_returns_none(self, monkeypatch):
        from app.services import llm as llm_service
        self._patch_chat(monkeypatch, '["negative"]')
        assert llm_service.classify_sentiments(["a", "b"]) is None

    def test_unknown_label_returns_none(self, monkeypatch):
        from app.services import llm as llm_service
        self._patch_chat(monkeypatch, '["angry", "neutral"]')
        assert llm_service.classify_sentiments(["a", "b"]) is None

    def test_non_json_returns_none(self, monkeypatch):
        from app.services import llm as llm_service
        self._patch_chat(monkeypatch, 'The messages are mostly negative.')
        assert llm_service.classify_sentiments(["a"]) is None

    def test_chat_failure_returns_none(self, monkeypatch):
        from app.services import llm as llm_service
        monkeypatch.setattr(llm_service, "_chat", lambda sp, uc: None)
        assert llm_service.classify_sentiments(["a"]) is None

    def test_empty_input_returns_empty_list(self):
        from app.services import llm as llm_service
        assert llm_service.classify_sentiments([]) == []

    def test_not_configured_returns_none(self, monkeypatch):
        from app.config import settings
        from app.services import llm as llm_service
        monkeypatch.setattr(settings, "gemini_api_key", "")
        assert llm_service.classify_sentiments(["a"]) is None


# ── Full agent response ─────────────────────────────────────────────────────

class TestSupportAgent:
    def test_agent_registered(self):
        assert "customer_support_agent" in AGENT_REGISTRY
        assert isinstance(
            AGENT_REGISTRY["customer_support_agent"], CustomerSupportAgent
        )

    def test_agent_metadata_intact(self):
        info = AGENT_REGISTRY["customer_support_agent"].info()
        assert info.name == "Customer Support Agent"
        assert info.status == "active"
        assert "Delivery problem analysis" in info.tasks

    def test_analyze_returns_valid_response(self, db):
        agent = AGENT_REGISTRY["customer_support_agent"]
        response = agent.analyze(db)
        assert response.agent == "Customer Support Agent"
        assert response.facts.summary.total_tickets == 18
        assert response.interpretation_source in ("llm", "fallback")
        assert len(response.interpretation) > 50
        assert response.generated_at

    def test_fallback_interpretation_uses_only_facts(self, db):
        """The deterministic fallback must quote the real computed numbers."""
        agent = AGENT_REGISTRY["customer_support_agent"]
        facts = get_support_snapshot(db)
        text = agent._fallback_interpretation(facts)

        assert "18 tickets" in text            # total tickets
        assert "83.33%" in text               # negative feedback percentage
        assert "10 still open" in text         # open count
        assert "Delivery problems account for 8 tickets" in text
        assert "44.44%" in text               # delivery share
        assert "5.83" in text                 # avg reported delay
        assert "longest 10 days" in text      # max reported delay
        assert "One customer wrote:" in text   # verbatim quote intro
        assert "Delivery delayed by 4 days — order #AG-4740" in text
        assert "Most important action" in text

    def test_facts_json_serializable_for_ceo_agent(self, db):
        """The CEO and BI agents must be able to consume these facts."""
        facts = get_support_snapshot(db)
        data = facts.model_dump()
        assert data["business_name"] == "Ali Garments"
        assert data["top_theme"] == "delivery_problems"
        assert data["summary"]["negative_feedback_percent"] == 83.33
        assert data["trend"]["delivery_change_percent"] == 200.0
        assert isinstance(data["tickets"], list)
        assert len(data["sample_negative_feedback"]) == 5

    def test_llm_not_configured_returns_none(self, db, monkeypatch):
        """With no API key the interpreter must short-circuit to None."""
        from app.config import settings
        from app.services import llm as llm_service

        facts = get_support_snapshot(db)
        monkeypatch.setattr(settings, "gemini_api_key", "")
        assert llm_service.is_llm_configured() is False
        assert llm_service.interpret_support_facts(facts) is None

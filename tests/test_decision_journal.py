"""Tests for the Decision Journal subsystem."""

from datetime import datetime, timezone

from titan.decision.journal import (
    DecisionJournal,
    DecisionJournalEntry,
    DecisionRepository,
)
from titan.decision.models import (
    TradeDecision,
    DecisionAction,
    InstrumentType,
    DecisionExplanation,
)
from titan.trading.models import TradeDirection
from titan.core.evidence import (
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
    Confidence,
)


class TestDecisionRepository:
    def test_save_and_get_latest(self) -> None:
        repo = DecisionRepository()

        entry1 = DecisionJournalEntry(
            id="1",
            timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            symbol="TCS",
            decision="buy",
            trade_direction="long",
            instrument_type="underlying",
            trade_score=8.5,
            confidence=0.8,
            institutional_grade=True,
            evidence_snapshot=None,
            reasons=(),
            explanation_summary="",
            risk_summary="",
            raw_decision=TradeDecision(
                symbol="TCS",
                decision=DecisionAction.BUY,
                trade_direction=TradeDirection.LONG,
                instrument_type=InstrumentType.UNDERLYING,
            ),
        )

        entry2 = DecisionJournalEntry(
            id="2",
            timestamp=datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc),
            symbol="INFY",
            decision="sell",
            trade_direction="short",
            instrument_type="underlying",
            trade_score=9.0,
            confidence=0.9,
            institutional_grade=True,
            evidence_snapshot=None,
            reasons=(),
            explanation_summary="",
            risk_summary="",
            raw_decision=TradeDecision(
                symbol="INFY",
                decision=DecisionAction.SELL,
                trade_direction=TradeDirection.SHORT,
                instrument_type=InstrumentType.UNDERLYING,
            ),
        )

        repo.save(entry1)
        repo.save(entry2)

        latest = repo.get_latest()
        assert len(latest) == 2
        assert latest[0].id == "2"
        assert latest[1].id == "1"

    def test_get_by_symbol(self) -> None:
        repo = DecisionRepository()
        entry = DecisionJournalEntry(
            id="1",
            timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            symbol="TCS",
            decision="buy",
            trade_direction="long",
            instrument_type="underlying",
            trade_score=8.5,
            confidence=0.8,
            institutional_grade=True,
            evidence_snapshot=None,
            reasons=(),
            explanation_summary="",
            risk_summary="",
            raw_decision=TradeDecision(
                symbol="TCS",
                decision=DecisionAction.BUY,
                trade_direction=TradeDirection.LONG,
                instrument_type=InstrumentType.UNDERLYING,
            ),
        )
        repo.save(entry)

        assert len(repo.get_by_symbol("TCS")) == 1
        assert len(repo.get_by_symbol("INFY")) == 0

    def test_clear(self) -> None:
        repo = DecisionRepository()
        entry = DecisionJournalEntry(
            id="1",
            timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            symbol="TCS",
            decision="buy",
            trade_direction="long",
            instrument_type="underlying",
            trade_score=8.5,
            confidence=0.8,
            institutional_grade=True,
            evidence_snapshot=None,
            reasons=(),
            explanation_summary="",
            risk_summary="",
            raw_decision=TradeDecision(
                symbol="TCS",
                decision=DecisionAction.BUY,
                trade_direction=TradeDirection.LONG,
                instrument_type=InstrumentType.UNDERLYING,
            ),
        )
        repo.save(entry)
        repo.clear()
        assert len(repo.get_latest()) == 0


class TestDecisionJournal:
    def test_record_decision_no_evidence(self) -> None:
        journal = DecisionJournal()
        decision = TradeDecision(
            symbol="RELIANCE",
            decision=DecisionAction.BUY,
            trade_direction=TradeDirection.LONG,
            instrument_type=InstrumentType.UNDERLYING,
            trade_score=7.0,
            confidence=0.6,
            institutional_grade=False,
            warnings=("Low volume",),
        )

        entry = journal.record_decision(decision)

        assert entry.symbol == "RELIANCE"
        assert entry.decision == "buy"
        assert entry.evidence_snapshot is None
        assert len(entry.reasons) == 1
        assert entry.reasons[0].reason_type == "warning"
        assert entry.reasons[0].description == "Low volume"

        assert len(journal.repository.get_latest()) == 1

    def test_record_decision_with_evidence_and_explanation(self) -> None:
        journal = DecisionJournal()

        evidence = Evidence(
            source="MarketEngine",
            category=EvidenceCategory.MARKET_STRUCTURE,
            signal=EvidenceSignal.BULLISH,
            score=Score(9.0),
            confidence=Confidence(0.9),
            weight=1.5,
            reasons=("Uptrend confirmed",),
        )

        explanation = DecisionExplanation(
            decision_summary="Strong setup",
            why_this_trade="Clear breakout",
            why_alternatives_rejected="Other setups had lower R:R",
            risk_summary="Stop loss below support",
        )

        decision = TradeDecision(
            symbol="TCS",
            decision=DecisionAction.BUY,
            trade_direction=TradeDirection.LONG,
            instrument_type=InstrumentType.UNDERLYING,
            trade_score=9.5,
            confidence=0.9,
            institutional_grade=True,
            evidence=evidence,
            explanation=explanation,
        )

        entry = journal.record_decision(decision)

        assert entry.symbol == "TCS"
        assert entry.evidence_snapshot is not None
        assert entry.evidence_snapshot.source == "MarketEngine"
        assert entry.evidence_snapshot.signal == "bullish"

        assert entry.explanation_summary == "Strong setup"
        assert entry.risk_summary == "Stop loss below support"

        # Reasons should include rejection and rationale
        assert len(entry.reasons) == 2
        types = [r.reason_type for r in entry.reasons]
        assert "rejection" in types
        assert "rationale" in types

"""Tests for the Decision Journal TUI screen."""

from __future__ import annotations

import json
from dataclasses import asdict
from unittest.mock import MagicMock

import pytest

from titan.tui.models import (
    DecisionEvidenceInfo,
    DecisionJournalEntry,
    DecisionQualificationInfo,
    DecisionReasonEntry,
    DecisionRiskInfo,
    DecisionScreenState,
    DecisionSummaryInfo,
    DecisionTimelineEntry,
)
from titan.tui.widgets.decision import (
    DecisionHistoryWidget,
    DecisionReasonsWidget,
    DecisionSummaryWidget,
    EvidenceWidget,
    QualificationWidget,
    RiskWidget,
    TimelineWidget,
)

# ─── Model tests ────────────────────────────────────────────────


class TestDecisionSummaryInfo:
    def test_defaults(self) -> None:
        info = DecisionSummaryInfo()
        assert info.decision_id == "None"
        assert info.symbol == "None"
        assert info.decision == "NO_TRADE"
        assert info.trade_direction == "None"
        assert info.instrument_type == "None"
        assert info.confidence == 0.0
        assert info.trade_score == 0.0
        assert info.institutional_grade is False
        assert info.timestamp_str == "Never"

    def test_custom(self) -> None:
        info = DecisionSummaryInfo(
            decision_id="123",
            symbol="RELIANCE",
            decision="BUY",
            trade_direction="Long",
            instrument_type="Option",
            confidence=0.85,
            trade_score=9.5,
            institutional_grade=True,
            timestamp_str="10:00:00",
        )
        assert info.symbol == "RELIANCE"
        assert info.decision == "BUY"
        assert info.trade_score == 9.5
        assert info.institutional_grade is True

    def test_frozen(self) -> None:
        info = DecisionSummaryInfo()
        with pytest.raises(AttributeError):
            info.symbol = "TCS"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = DecisionSummaryInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = DecisionSummaryInfo(decision_id="123", symbol="TCS")
        data = asdict(info)
        serialized = json.dumps(data)
        assert "TCS" in serialized


class TestDecisionEvidenceInfo:
    def test_defaults(self) -> None:
        info = DecisionEvidenceInfo()
        assert info.source == "Unknown"
        assert info.category == "Unknown"
        assert info.signal == "Unknown"
        assert info.score == 0.0
        assert info.confidence == 0.0
        assert info.weight == 0.0
        assert info.reasons == ()

    def test_custom(self) -> None:
        info = DecisionEvidenceInfo(
            source="VolatilityEngine",
            category="volatility",
            signal="bullish",
            score=0.9,
            confidence=0.8,
            weight=1.5,
            reasons=("Implied volatility drop",),
        )
        assert info.source == "VolatilityEngine"
        assert info.signal == "bullish"
        assert len(info.reasons) == 1

    def test_frozen(self) -> None:
        info = DecisionEvidenceInfo()
        with pytest.raises(AttributeError):
            info.source = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = DecisionEvidenceInfo()
        assert not hasattr(info, "__dict__")


class TestDecisionRiskInfo:
    def test_defaults(self) -> None:
        info = DecisionRiskInfo()
        assert info.risk_summary == "No risk data available."

    def test_custom(self) -> None:
        info = DecisionRiskInfo(risk_summary="High volatility, tight stops.")
        assert info.risk_summary == "High volatility, tight stops."

    def test_frozen(self) -> None:
        info = DecisionRiskInfo()
        with pytest.raises(AttributeError):
            info.risk_summary = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = DecisionRiskInfo()
        assert not hasattr(info, "__dict__")


class TestDecisionQualificationInfo:
    def test_defaults(self) -> None:
        info = DecisionQualificationInfo()
        assert info.explanation_summary == "No explanation available."

    def test_custom(self) -> None:
        info = DecisionQualificationInfo(explanation_summary="All checks passed.")
        assert info.explanation_summary == "All checks passed."

    def test_frozen(self) -> None:
        info = DecisionQualificationInfo()
        with pytest.raises(AttributeError):
            info.explanation_summary = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = DecisionQualificationInfo()
        assert not hasattr(info, "__dict__")


class TestDecisionReasonEntry:
    def test_defaults(self) -> None:
        entry = DecisionReasonEntry()
        assert entry.reason_type == ""
        assert entry.description == ""
        assert entry.severity == "info"

    def test_custom(self) -> None:
        entry = DecisionReasonEntry(
            reason_type="risk_check",
            description="Exceeded max drawdown.",
            severity="critical",
        )
        assert entry.reason_type == "risk_check"
        assert entry.severity == "critical"

    def test_frozen(self) -> None:
        entry = DecisionReasonEntry()
        with pytest.raises(AttributeError):
            entry.reason_type = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = DecisionReasonEntry()
        assert not hasattr(entry, "__dict__")


class TestDecisionTimelineEntry:
    def test_defaults(self) -> None:
        entry = DecisionTimelineEntry()
        assert entry.step == ""
        assert entry.status == ""
        assert entry.timestamp_str == ""

    def test_custom(self) -> None:
        entry = DecisionTimelineEntry(
            step="Risk Validation",
            status="Passed",
            timestamp_str="10:05:00",
        )
        assert entry.step == "Risk Validation"
        assert entry.status == "Passed"

    def test_frozen(self) -> None:
        entry = DecisionTimelineEntry()
        with pytest.raises(AttributeError):
            entry.step = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = DecisionTimelineEntry()
        assert not hasattr(entry, "__dict__")


class TestDecisionJournalEntry:
    def test_defaults(self) -> None:
        entry = DecisionJournalEntry()
        assert entry.decision_id == ""
        assert entry.symbol == ""
        assert entry.decision == ""
        assert entry.timestamp_str == ""

    def test_custom(self) -> None:
        entry = DecisionJournalEntry(
            decision_id="d1",
            symbol="INFY",
            decision="sell",
            timestamp_str="10:10:00",
        )
        assert entry.symbol == "INFY"
        assert entry.decision == "sell"

    def test_frozen(self) -> None:
        entry = DecisionJournalEntry()
        with pytest.raises(AttributeError):
            entry.symbol = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = DecisionJournalEntry()
        assert not hasattr(entry, "__dict__")


class TestDecisionScreenState:
    def test_defaults(self) -> None:
        state = DecisionScreenState()
        assert isinstance(state.summary, DecisionSummaryInfo)
        assert isinstance(state.evidence, DecisionEvidenceInfo)
        assert isinstance(state.risk, DecisionRiskInfo)
        assert isinstance(state.qualification, DecisionQualificationInfo)
        assert state.reasons == ()
        assert state.timeline == ()
        assert state.history == ()
        assert state.last_refresh == ""

    def test_custom(self) -> None:
        state = DecisionScreenState(last_refresh="12:00:00")
        assert state.last_refresh == "12:00:00"

    def test_frozen(self) -> None:
        state = DecisionScreenState()
        with pytest.raises(AttributeError):
            state.last_refresh = "10:00"  # type: ignore[misc]

    def test_slots(self) -> None:
        state = DecisionScreenState()
        assert not hasattr(state, "__dict__")


# ─── Widget tests ───────────────────────────────────────────────


class TestDecisionSummaryWidget:
    def test_initial_state(self) -> None:
        widget = DecisionSummaryWidget()
        assert widget._info.decision == "NO_TRADE"

    def test_update_data_buy(self) -> None:
        widget = DecisionSummaryWidget()
        widget._title = MagicMock()
        widget._status = MagicMock()
        widget._confidence = MagicMock()
        widget._score = MagicMock()
        widget._direction = MagicMock()
        widget._type = MagicMock()
        info = DecisionSummaryInfo(
            decision="BUY", symbol="TCS", trade_score=10.0, institutional_grade=True
        )
        widget.update_data(info)
        assert widget._info.decision == "BUY"

    def test_update_data_sell(self) -> None:
        widget = DecisionSummaryWidget()
        widget._title = MagicMock()
        widget._status = MagicMock()
        widget._confidence = MagicMock()
        widget._score = MagicMock()
        widget._direction = MagicMock()
        widget._type = MagicMock()
        info = DecisionSummaryInfo(decision="SELL", symbol="RELIANCE")
        widget.update_data(info)
        assert widget._info.decision == "SELL"


class TestEvidenceWidget:
    def test_initial_state(self) -> None:
        widget = EvidenceWidget()
        assert widget._info.source == "Unknown"

    def test_update_data(self) -> None:
        widget = EvidenceWidget()
        widget._title = MagicMock()
        widget._source = MagicMock()
        widget._category = MagicMock()
        widget._signal = MagicMock()
        widget._metrics = MagicMock()
        info = DecisionEvidenceInfo(source="NewsEngine", signal="bullish")
        widget.update_data(info)
        assert widget._info.source == "NewsEngine"


class TestRiskWidget:
    def test_initial_state(self) -> None:
        widget = RiskWidget()
        assert widget._info.risk_summary == "No risk data available."

    def test_update_data(self) -> None:
        widget = RiskWidget()
        widget._title = MagicMock()
        widget._summary = MagicMock()
        info = DecisionRiskInfo(risk_summary="High Risk")
        widget.update_data(info)
        assert widget._info.risk_summary == "High Risk"


class TestQualificationWidget:
    def test_initial_state(self) -> None:
        widget = QualificationWidget()
        assert widget._info.explanation_summary == "No explanation available."

    def test_update_data(self) -> None:
        widget = QualificationWidget()
        widget._title = MagicMock()
        widget._summary = MagicMock()
        info = DecisionQualificationInfo(explanation_summary="Validated")
        widget.update_data(info)
        assert widget._info.explanation_summary == "Validated"


class TestDecisionReasonsWidget:
    def test_initial_state(self) -> None:
        widget = DecisionReasonsWidget()
        assert widget._reasons == ()

    def test_update_data_empty(self) -> None:
        widget = DecisionReasonsWidget()
        widget._title = MagicMock()
        widget.mount = MagicMock()
        widget._rows = []
        widget.update_data(())
        assert len(widget._rows) == 1

    def test_update_data_items(self) -> None:
        widget = DecisionReasonsWidget()
        widget._title = MagicMock()
        widget.mount = MagicMock()
        widget._rows = []
        reasons = (
            DecisionReasonEntry(
                reason_type="risk",
                description="Stop loss too wide",
                severity="critical",
            ),
            DecisionReasonEntry(
                reason_type="liquidity", description="Thin book", severity="warning"
            ),
        )
        widget.update_data(reasons)
        assert len(widget._rows) == 2


class TestTimelineWidget:
    def test_initial_state(self) -> None:
        widget = TimelineWidget()
        assert widget._timeline == ()

    def test_update_data_empty(self) -> None:
        widget = TimelineWidget()
        widget._title = MagicMock()
        widget.mount = MagicMock()
        widget._rows = []
        widget.update_data(())
        assert len(widget._rows) == 1

    def test_update_data_items(self) -> None:
        widget = TimelineWidget()
        widget._title = MagicMock()
        widget.mount = MagicMock()
        widget._rows = []
        timeline = (
            DecisionTimelineEntry(
                step="Start", status="done", timestamp_str="10:00:00"
            ),
        )
        widget.update_data(timeline)
        assert len(widget._rows) == 1


class TestDecisionHistoryWidget:
    def test_initial_state(self) -> None:
        widget = DecisionHistoryWidget()
        assert widget._history == ()

    def test_update_data_empty(self) -> None:
        widget = DecisionHistoryWidget()
        widget._title = MagicMock()
        widget.mount = MagicMock()
        widget._rows = []
        widget.update_data(())
        assert len(widget._rows) == 1

    def test_update_data_items(self) -> None:
        widget = DecisionHistoryWidget()
        widget._title = MagicMock()
        widget.mount = MagicMock()
        widget._rows = []
        history = (
            DecisionJournalEntry(
                decision="buy", symbol="TCS", timestamp_str="10:00:00"
            ),
            DecisionJournalEntry(
                decision="sell", symbol="INFY", timestamp_str="10:05:00"
            ),
            DecisionJournalEntry(
                decision="none", symbol="WIPRO", timestamp_str="10:10:00"
            ),
        )
        widget.update_data(history)
        assert len(widget._rows) == 3

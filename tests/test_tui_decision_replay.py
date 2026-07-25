"""Tests for the Decision Replay TUI screen and widgets."""

from titan.tui.models import (
    ReplayEvidenceInfo,
    ReplayMetadataInfo,
    ReplayQualificationInfo,
    ReplayReasonEntry,
    ReplayRiskInfo,
    ReplayScreenState,
    ReplaySummaryInfo,
    ReplayTimelineEntry,
)
from titan.tui.screens.decision_replay import DecisionReplayScreen
from titan.tui.widgets.decision_replay import (
    ReplayEvidenceWidget,
    ReplayMetadataWidget,
    ReplayQualificationWidget,
    ReplayReasonsWidget,
    ReplayRiskWidget,
    ReplaySummaryWidget,
    ReplayTimelineWidget,
)


def test_replay_summary_widget():
    widget = ReplaySummaryWidget()
    info = ReplaySummaryInfo(
        decision="BUY",
        symbol="AAPL",
        trade_direction="LONG",
        instrument_type="UNDERLYING",
        confidence=0.9,
        trade_score=95.0,
        institutional_grade=True,
    )

    # Must compose before updating to avoid MountError in real environment,
    # but the widget handles _has_composed internally or ignores updates before mount.
    # We simulate a manual compose tree structure for testing.
    class DummyStatic:
        def update(self, *args, **kwargs):
            pass

    widget._decision = DummyStatic()
    widget._symbol = DummyStatic()
    widget._details = DummyStatic()
    widget._metrics = DummyStatic()

    widget.update_data(info)
    assert widget._info.symbol == "AAPL"


def test_replay_evidence_widget():
    widget = ReplayEvidenceWidget()
    info = ReplayEvidenceInfo(
        source="Test",
        category="TestCat",
        signal="bullish",
        score=10.0,
        confidence=0.5,
        weight=1.0,
    )

    class DummyStatic:
        def update(self, *args, **kwargs):
            pass

    widget._source = DummyStatic()
    widget._signal = DummyStatic()
    widget._metrics = DummyStatic()

    widget.update_data(info)
    assert widget._info.source == "Test"


def test_replay_risk_widget():
    widget = ReplayRiskWidget()
    info = ReplayRiskInfo(risk_summary="Low risk")

    class DummyStatic:
        def update(self, *args, **kwargs):
            pass

    widget._summary = DummyStatic()
    widget.update_data(info)
    assert widget._info.risk_summary == "Low risk"


def test_replay_qualification_widget():
    widget = ReplayQualificationWidget()
    info = ReplayQualificationInfo(explanation_summary="Valid setup")

    class DummyStatic:
        def update(self, *args, **kwargs):
            pass

    widget._summary = DummyStatic()
    widget.update_data(info)
    assert widget._info.explanation_summary == "Valid setup"


def test_replay_reasons_widget():
    widget = ReplayReasonsWidget()
    reasons = (
        ReplayReasonEntry(reason_type="trend", description="up", severity="info"),
    )

    # Needs to be mounted or hasattr check to pass.
    # ReplayReasonsWidget uses _has_composed which checks for _title
    widget._title = "Mock"

    # Overriding mount for test
    def mock_mount(self, *args, **kwargs):
        pass

    widget.mount = mock_mount.__get__(widget, ReplayReasonsWidget)

    widget.update_data(reasons)
    assert len(widget._reasons) == 1
    assert len(widget._rows) == 1


def test_replay_timeline_widget():
    widget = ReplayTimelineWidget()
    timeline = (
        ReplayTimelineEntry(step="Start", status="Completed", timestamp_str="12:00:00"),
    )

    widget._title = "Mock"

    def mock_mount(self, *args, **kwargs):
        pass

    widget.mount = mock_mount.__get__(widget, ReplayTimelineWidget)

    widget.update_data(timeline)
    assert len(widget._timeline) == 1
    assert len(widget._rows) == 1


def test_replay_metadata_widget():
    widget = ReplayMetadataWidget()
    info = ReplayMetadataInfo(
        has_previous=True,
        has_next=False,
        current_index=5,
        total_decisions=10,
    )

    class DummyStatic:
        def update(self, *args, **kwargs):
            pass

    widget._status = DummyStatic()
    widget.update_data(info)
    assert widget._info.current_index == 5


def test_decision_replay_screen_refresh():
    screen = DecisionReplayScreen()

    called = False

    def mock_builder(entry_id: str | None = None) -> ReplayScreenState:
        nonlocal called
        called = True
        return ReplayScreenState(
            summary=ReplaySummaryInfo(decision_id="123", symbol="TEST")
        )

    screen.set_state_builder(mock_builder)

    # Trigger refresh
    screen._refresh_state()
    assert called is True
    assert screen._state.summary.symbol == "TEST"
    assert screen._current_entry_id == "123"


def test_decision_replay_screen_navigation():
    screen = DecisionReplayScreen()

    states = {
        "1": ReplayScreenState(
            summary=ReplaySummaryInfo(decision_id="1"),
            metadata=ReplayMetadataInfo(has_next=True, next_id="2", has_previous=False),
        ),
        "2": ReplayScreenState(
            summary=ReplaySummaryInfo(decision_id="2"),
            metadata=ReplayMetadataInfo(
                has_next=False, has_previous=True, previous_id="1"
            ),
        ),
    }

    def mock_builder(entry_id: str | None = None) -> ReplayScreenState:
        if not entry_id:
            return states["1"]
        return states.get(entry_id, ReplayScreenState())

    screen.set_state_builder(mock_builder)
    screen._refresh_state()

    assert screen._current_entry_id == "1"

    # Try next
    screen.action_next()
    assert screen._current_entry_id == "2"

    # Try next again (has_next=False)
    screen.action_next()
    assert screen._current_entry_id == "2"

    # Try previous
    screen.action_previous()
    assert screen._current_entry_id == "1"

    # Try previous again (has_previous=False)
    screen.action_previous()
    assert screen._current_entry_id == "1"

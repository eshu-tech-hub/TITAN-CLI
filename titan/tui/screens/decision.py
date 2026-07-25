"""Decision Journal screen — read-only visualization of trade decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from titan.tui.models import DecisionScreenState
from titan.tui.widgets.decision import (
    DecisionHistoryWidget,
    DecisionReasonsWidget,
    DecisionSummaryWidget,
    EvidenceWidget,
    QualificationWidget,
    RiskWidget,
    TimelineWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class DecisionScreen(Screen):
    """Decision Journal Explainability screen with operational widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from the runtime DecisionJournal.
    """

    DEFAULT_CSS = """
    DecisionScreen {
        layout: vertical;
        padding: 1 2;
    }
    #decision-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }
    #refresh-indicator {
        text-align: right;
        height: 1;
        color: $text-muted;
        dock: top;
    }
    #widgets-container {
        height: 1fr;
    }
    #decision-row-1 {
        height: auto;
    }
    #decision-row-1 > * {
        width: 1fr;
    }
    #decision-row-2 {
        height: auto;
    }
    #decision-row-2 > * {
        width: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
        ("up", "scroll_up_line", "Scroll Up"),
        ("down", "scroll_down_line", "Scroll Down"),
        ("page_up", "scroll_up", "Scroll Up"),
        ("page_down", "scroll_down", "Scroll Down"),
        ("home", "scroll_top", "Scroll Top"),
        ("end", "scroll_bottom", "Scroll Bottom"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = DecisionScreenState()
        self._state_builder: Callable[[], DecisionScreenState] | None = None
        self._summary_widget: DecisionSummaryWidget | None = None
        self._evidence_widget: EvidenceWidget | None = None
        self._risk_widget: RiskWidget | None = None
        self._qualification_widget: QualificationWidget | None = None
        self._reasons_widget: DecisionReasonsWidget | None = None
        self._timeline_widget: TimelineWidget | None = None
        self._history_widget: DecisionHistoryWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Decision Journal & Explainability", id="decision-title")
        yield Static("", id="refresh-indicator")

        with VerticalScroll(id="widgets-container"):
            with Horizontal(id="decision-row-1"):
                self._summary_widget = DecisionSummaryWidget(id="decision-summary")
                self._evidence_widget = EvidenceWidget(id="decision-evidence")
                yield self._summary_widget
                yield self._evidence_widget

            with Horizontal(id="decision-row-2"):
                self._risk_widget = RiskWidget(id="decision-risk")
                self._qualification_widget = QualificationWidget(
                    id="decision-qualification"
                )
                yield self._risk_widget
                yield self._qualification_widget

            self._reasons_widget = DecisionReasonsWidget(id="decision-reasons")
            yield self._reasons_widget

            self._timeline_widget = TimelineWidget(id="decision-timeline")
            yield self._timeline_widget

            self._history_widget = DecisionHistoryWidget(id="decision-history")
            yield self._history_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], DecisionScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = DecisionScreenState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        if self._summary_widget is not None:
            self._summary_widget.update_data(self._state.summary)
        if self._evidence_widget is not None:
            self._evidence_widget.update_data(self._state.evidence)
        if self._risk_widget is not None:
            self._risk_widget.update_data(self._state.risk)
        if self._qualification_widget is not None:
            self._qualification_widget.update_data(self._state.qualification)
        if self._reasons_widget is not None:
            self._reasons_widget.update_data(self._state.reasons)
        if self._timeline_widget is not None:
            self._timeline_widget.update_data(self._state.timeline)
        if self._history_widget is not None:
            self._history_widget.update_data(self._state.history)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            indicator.update(f"Last refresh: {now}")
        except Exception:
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_scroll_up_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_up(animate=False)
        except Exception:
            pass

    def action_scroll_down_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_down(animate=False)
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def action_scroll_top(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:
            pass

    def action_scroll_bottom(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:
            pass

    @property
    def state(self) -> DecisionScreenState:
        return self._state

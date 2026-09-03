"""Decision Replay screen — read-only Explainability Explorer."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

from titan.tui.models import ReplayScreenState
from titan.tui.widgets.decision_replay import (
    ReplayEvidenceWidget,
    ReplayMetadataWidget,
    ReplayQualificationWidget,
    ReplayReasonsWidget,
    ReplayRiskWidget,
    ReplaySummaryWidget,
    ReplayTimelineWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class DecisionReplayScreen(VerticalScroll):
    """Explainability Explorer view for replaying historical decisions.

    Navigates through the DecisionJournal immutably.
    Does not auto-refresh. State is updated on navigation.
    """

    DEFAULT_CSS: ClassVar[str] = """
    DecisionReplayScreen {
        layout: vertical;
        padding: 1 2;
    }
    #replay-title {
        text-style: bold;
        color: $secondary;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }
    #replay-indicator {
        text-align: right;
        height: 1;
        color: $text-muted;
        dock: top;
    }
    #replay-widgets-container {
        height: 1fr;
    }
    #replay-row-1 {
        height: auto;
    }
    #replay-row-1 > * {
        width: 1fr;
    }
    #replay-row-2 {
        height: auto;
    }
    #replay-row-2 > * {
        width: 1fr;
    }
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
        ("r", "refresh", "Refresh"),
        ("[", "previous", "Previous Decision"),
        ("p", "previous", "Previous Decision"),
        ("]", "next", "Next Decision"),
        ("n", "next", "Next Decision"),
        ("up", "scroll_up_line", "Scroll Up"),
        ("down", "scroll_down_line", "Scroll Down"),
        ("page_up", "scroll_up", "Scroll Up"),
        ("page_down", "scroll_down", "Scroll Down"),
        ("home", "scroll_top", "Scroll Top"),
        ("end", "scroll_bottom", "Scroll Bottom"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = ReplayScreenState()
        self._state_builder: Callable[[str | None], ReplayScreenState] | None = None
        self._current_entry_id: str | None = None

        self._summary_widget: ReplaySummaryWidget | None = None
        self._evidence_widget: ReplayEvidenceWidget | None = None
        self._risk_widget: ReplayRiskWidget | None = None
        self._qualification_widget: ReplayQualificationWidget | None = None
        self._reasons_widget: ReplayReasonsWidget | None = None
        self._timeline_widget: ReplayTimelineWidget | None = None
        self._metadata_widget: ReplayMetadataWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Decision Replay & Explainability Explorer", id="replay-title")
        yield Static("", id="replay-indicator")

        with VerticalScroll(id="replay-widgets-container"):
            self._metadata_widget = ReplayMetadataWidget(id="replay-metadata")
            yield self._metadata_widget

            with Horizontal(id="replay-row-1"):
                self._summary_widget = ReplaySummaryWidget(id="replay-summary")
                self._evidence_widget = ReplayEvidenceWidget(id="replay-evidence")
                yield self._summary_widget
                yield self._evidence_widget

            with Horizontal(id="replay-row-2"):
                self._risk_widget = ReplayRiskWidget(id="replay-risk")
                self._qualification_widget = ReplayQualificationWidget(
                    id="replay-qualification"
                )
                yield self._risk_widget
                yield self._qualification_widget

            self._reasons_widget = ReplayReasonsWidget(id="replay-reasons")
            yield self._reasons_widget

            self._timeline_widget = ReplayTimelineWidget(id="replay-timeline")
            yield self._timeline_widget

    def on_mount(self) -> None:
        self._refresh_state()

    def set_state_builder(
        self, builder: Callable[[str | None], ReplayScreenState]
    ) -> None:
        self._state_builder = builder

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder(self._current_entry_id)
                # Keep current_entry_id synced with whatever state builder loaded
                if self._state.summary.decision_id != "None":
                    self._current_entry_id = self._state.summary.decision_id
            except Exception:  # noqa: BLE001
                self._state = ReplayScreenState()
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
        if self._metadata_widget is not None:
            self._metadata_widget.update_data(self._state.metadata)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#replay-indicator", Static)
            now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display
            indicator.update(f"Replay loaded at: {now}")
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        """Return to the previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_previous(self) -> None:
        if self._state.metadata.has_previous and self._state.metadata.previous_id:
            self._current_entry_id = self._state.metadata.previous_id
            self._refresh_state()

    def action_next(self) -> None:
        if self._state.metadata.has_next and self._state.metadata.next_id:
            self._current_entry_id = self._state.metadata.next_id
            self._refresh_state()

    def action_scroll_up_line(self) -> None:
        try:
            container = self.query_one("#replay-widgets-container", VerticalScroll)
            container.scroll_up(animate=False)
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_scroll_down_line(self) -> None:
        try:
            container = self.query_one("#replay-widgets-container", VerticalScroll)
            container.scroll_down(animate=False)
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_scroll_up(self) -> None:
        try:
            container = self.query_one("#replay-widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_down(self) -> None:
        try:
            container = self.query_one("#replay-widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_top(self) -> None:
        try:
            container = self.query_one("#replay-widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_bottom(self) -> None:
        try:
            container = self.query_one("#replay-widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001
            pass

    @property
    def state(self) -> ReplayScreenState:
        return self._state

"""Trade Journal screen — read-only visualization of trade outcomes and performance."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import VerticalScroll
from textual.widgets import Static

from titan.tui.models import TradeJournalScreenState
from titan.tui.widgets.trade_journal import (
    TradeHistoryWidget,
    TradeSummaryWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class TradeJournalScreen(VerticalScroll):
    """Trade Journal & Performance Analytics view.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from the runtime TradeJournal.
    """

    DEFAULT_CSS: ClassVar[str] = """
    TradeJournalScreen {
        layout: vertical;
        padding: 1 2;
    }
    #trade-journal-title {
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
    """

    BINDINGS: ClassVar[list] = [
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
        self._state = TradeJournalScreenState()
        self._state_builder: Callable[[], TradeJournalScreenState] | None = None
        self._summary_widget: TradeSummaryWidget | None = None
        self._history_widget: TradeHistoryWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Trade Journal & Performance Analytics", id="trade-journal-title")
        yield Static("", id="refresh-indicator")

        with VerticalScroll(id="widgets-container"):
            self._summary_widget = TradeSummaryWidget(id="trade-summary")
            yield self._summary_widget

            self._history_widget = TradeHistoryWidget(id="trade-history")
            yield self._history_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], TradeJournalScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:  # noqa: BLE001
                self._state = TradeJournalScreenState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        if self._summary_widget is not None:
            self._summary_widget.update_data(self._state.summary)
        if self._history_widget is not None:
            self._history_widget.update_data(self._state.history)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display
            indicator.update(f"Last refresh: {now}")
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        """Return to the previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_up_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_up(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_down_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_down(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_up(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_down(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_top(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_bottom(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    @property
    def state(self) -> TradeJournalScreenState:
        return self._state

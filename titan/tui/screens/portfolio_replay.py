"""Portfolio Replay Dashboard screen."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from textual.containers import VerticalScroll, Horizontal
from textual.screen import Screen
from textual.widgets import Static

from titan.tui.widgets.portfolio_replay import (
    HistoricalAnalyticsWidget,
    ReplayTimelineWidget,
)

if TYPE_CHECKING:
    from titan.portfolio.replay import PortfolioReplayService


class PortfolioReplayScreen(Screen):
    """Portfolio historical replay dashboard."""

    DEFAULT_CSS = """
    PortfolioReplayScreen {
        layout: vertical;
        padding: 1 2;
    }
    #replay-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }
    #replay-scroll {
        height: 1fr;
    }
    .widget-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }
    .widget-container {
        padding: 1;
        border: solid $border;
        height: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._replay_service: PortfolioReplayService | None = None

        # Widgets
        self._timeline_widget = ReplayTimelineWidget(classes="widget-container")
        self._analytics_widget = HistoricalAnalyticsWidget(classes="widget-container")
        self._target_time: datetime | None = None

    def compose(self) -> Any:
        yield Static("TITAN Portfolio Historical Replay", id="replay-title")
        yield Static(id="replay-time-display")

        with VerticalScroll(id="replay-scroll"):
            with Horizontal():
                yield self._timeline_widget
                yield self._analytics_widget

    def set_service(self, service: PortfolioReplayService) -> None:
        """Inject the replay service."""
        self._replay_service = service

    def load_time(
        self, target_time: datetime, starting_capital: float = 100000.0
    ) -> None:
        """Load the replay at the specified timestamp."""
        if not self._replay_service:
            return

        self._target_time = target_time
        time_str = target_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        self.query_one("#replay-time-display", Static).update(
            f"Viewing State At: {time_str}"
        )

        try:
            result = self._replay_service.replay_to_timestamp(
                target_time, starting_capital
            )
            self._timeline_widget.replay = result
            self._analytics_widget.replay = result
        except Exception:
            pass

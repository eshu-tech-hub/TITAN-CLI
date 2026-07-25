"""Dashboard screen — default screen with auto-refreshing status cards."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from titan.tui.models import DashboardState
from titan.tui.widgets.health_card import HealthCard
from titan.tui.widgets.market_card import MarketCard
from titan.tui.widgets.runtime_card import RuntimeCard
from titan.tui.widgets.system_card import SystemCard
from titan.tui.widgets.trading_card import TradingCard

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0  # seconds


class DashboardScreen(Screen):
    """Main dashboard screen with five status cards.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS = """
    DashboardScreen {
        layout: vertical;
        padding: 1 2;
    }
    #dashboard-title {
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
    #cards-container {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = DashboardState()
        self._state_builder: Callable[[], DashboardState] | None = None
        self._runtime_card: RuntimeCard | None = None
        self._market_card: MarketCard | None = None
        self._trading_card: TradingCard | None = None
        self._health_card: HealthCard | None = None
        self._system_card: SystemCard | None = None

    def compose(self):  # type: ignore[override]
        yield Static("TITAN Dashboard", id="dashboard-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="cards-container"):
            self._runtime_card = RuntimeCard(id="runtime-card")
            self._market_card = MarketCard(id="market-card")
            self._trading_card = TradingCard(id="trading-card")
            self._health_card = HealthCard(id="health-card")
            self._system_card = SystemCard(id="system-card")
            yield self._runtime_card
            yield self._market_card
            yield self._trading_card
            yield self._health_card
            yield self._system_card

    def on_mount(self) -> None:
        """Start the refresh timer when the screen is mounted."""
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], DashboardState]) -> None:
        """Set the function that builds DashboardState from managers."""
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        """Called by the timer every REFRESH_INTERVAL seconds."""
        self._refresh_state()

    def _refresh_state(self) -> None:
        """Collect state from managers and update all widgets."""
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = DashboardState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        """Push current state to all card widgets."""
        if self._runtime_card is not None:
            self._runtime_card.update_data(self._state.runtime)
        if self._market_card is not None:
            self._market_card.update_data(self._state.market)
        if self._trading_card is not None:
            self._trading_card.update_data(self._state.trading)
        if self._health_card is not None:
            self._health_card.update_data(self._state.health)
        if self._system_card is not None:
            self._system_card.update_data(self._state.system)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            indicator.update(f"Last refresh: {now}")
        except Exception:
            pass

    def action_refresh(self) -> None:
        """Manual refresh triggered by keybinding."""
        self._refresh_state()

    @property
    def state(self) -> DashboardState:
        """Current dashboard state (for testing)."""
        return self._state

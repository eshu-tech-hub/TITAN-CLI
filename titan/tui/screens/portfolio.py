"""Portfolio Analytics Dashboard screen."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

from titan.tui.models import PortfolioScreenState
from titan.tui.widgets.portfolio import (
    AllocationWidget,
    DiversificationWidget,
    DrawdownWidget,
    ExposureWidget,
    PerformanceWidget,
    PortfolioSummaryWidget,
    SectorExposureWidget,
    StrategyPerformanceWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from titan.portfolio.analytics import PortfolioAnalytics

REFRESH_INTERVAL = 1.0  # seconds


class PortfolioDashboardScreen(VerticalScroll):
    """Portfolio analytics dashboard view with read-only metrics."""

    DEFAULT_CSS: ClassVar[str] = """
    PortfolioDashboardScreen {
        layout: vertical;
        padding: 1 2;
    }
    #portfolio-title {
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
    #dashboard-scroll {
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

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._analytics_engine: PortfolioAnalytics | None = None
        self._state_builder: Callable[[], PortfolioScreenState] | None = None
        self.state = PortfolioScreenState()

        # Widgets
        self._summary_widget = PortfolioSummaryWidget(classes="widget-container")
        self._exposure_widget = ExposureWidget(classes="widget-container")
        self._allocation_widget = AllocationWidget(classes="widget-container")
        self._diversification_widget = DiversificationWidget(classes="widget-container")
        self._drawdown_widget = DrawdownWidget(classes="widget-container")
        self._performance_widget = PerformanceWidget(classes="widget-container")
        self._sector_widget = SectorExposureWidget(classes="widget-container")
        self._strategy_widget = StrategyPerformanceWidget(classes="widget-container")

    def compose(self) -> Any:
        yield Static("TITAN Portfolio Analytics Dashboard", id="portfolio-title")
        yield Static("", id="refresh-indicator")

        with VerticalScroll(id="dashboard-scroll"):
            with Horizontal():
                yield self._summary_widget
                yield self._performance_widget
            with Horizontal():
                yield self._exposure_widget
                yield self._drawdown_widget
            with Horizontal():
                yield self._allocation_widget
                yield self._diversification_widget
            with Horizontal():
                yield self._sector_widget
                yield self._strategy_widget

    def on_mount(self) -> None:
        """Start the refresh timer."""
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_engine(self, engine: PortfolioAnalytics) -> None:
        """Inject the analytics engine."""
        self._analytics_engine = engine

    def set_state_builder(self, builder: Callable[[], PortfolioScreenState]) -> None:
        """Set the function that builds PortfolioScreenState."""
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is None:
            return

        try:
            self.state = self._state_builder()

            # Push to widgets
            self._summary_widget.snapshot = self.state.snapshot
            self._exposure_widget.exposure = self.state.exposure
            self._allocation_widget.allocation = self.state.allocation
            self._diversification_widget.diversification = self.state.diversification
            self._drawdown_widget.drawdown = self.state.drawdown
            self._performance_widget.performance = self.state.performance
            self._sector_widget.allocation = self.state.allocation
            self._strategy_widget.allocation = self.state.allocation

        except Exception:  # noqa: BLE001
            pass

        self._update_refresh_indicator()

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display
            indicator.update(f"Last refresh: {now}")
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

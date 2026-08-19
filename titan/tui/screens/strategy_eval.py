"""Strategy Intelligence Dashboard screen."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Static

from titan.tui.models import StrategyEvalScreenState

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class StrategyScorecardWidget(Static):
    """Displays a single strategy's performance and regime breakdown."""

    def compose(self) -> Any:
        yield Static("", id="strat-title", classes="widget-title")
        yield DataTable(id="strat-metrics")
        yield Static("Regime Breakdown", classes="widget-subtitle")
        yield DataTable(id="strat-regimes")

    def on_mount(self) -> None:
        metrics = self.query_one("#strat-metrics", DataTable)
        metrics.add_columns("Metric", "Value")

        regimes = self.query_one("#strat-regimes", DataTable)
        regimes.add_columns("Regime", "Trades", "Win Rate", "PF", "Net PnL")

    def update_data(self, scorecard: Any) -> None:
        title = self.query_one("#strat-title", Static)
        title.update(f"Strategy: {scorecard.strategy_name}")

        metrics = self.query_one("#strat-metrics", DataTable)
        metrics.clear()
        metrics.add_rows(
            [
                ("Total Trades", str(scorecard.total_trades)),
                ("Win Rate", scorecard.win_rate),
                ("Profit Factor", scorecard.profit_factor),
                ("Expectancy", scorecard.expectancy),
                ("Net PnL", scorecard.net_pnl),
                ("Max Drawdown", scorecard.max_drawdown),
            ]
        )

        regimes = self.query_one("#strat-regimes", DataTable)
        regimes.clear()
        for r in scorecard.regimes:
            regimes.add_row(
                r.regime, str(r.trades), r.win_rate, r.profit_factor, r.net_pnl
            )


class StrategyEvalScreen(Screen):
    """Strategy Intelligence Dashboard."""

    DEFAULT_CSS: ClassVar[str] = """
    StrategyEvalScreen {
        layout: vertical;
        padding: 1 2;
    }
    #strategy-title {
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
    .widget-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }
    .widget-subtitle {
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }
    .scorecard-container {
        padding: 1;
        border: solid $border;
        height: auto;
        margin-bottom: 1;
    }
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = StrategyEvalScreenState()
        self._state_builder: Callable[[], StrategyEvalScreenState] | None = None

    def compose(self) -> Any:
        yield Static("TITAN Strategy Intelligence Dashboard", id="strategy-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="scorecards-container"):
            pass  # Widgets are added dynamically

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], StrategyEvalScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = StrategyEvalScreenState()

        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        try:
            container = self.query_one("#scorecards-container", VerticalScroll)
        except Exception:
            return

        current_widgets = container.query(StrategyScorecardWidget)

        # Rebuild dynamically if the number of strategies changes
        if len(current_widgets) != len(self._state.scorecards):
            for w in current_widgets:
                w.remove()
            for _ in self._state.scorecards:
                container.mount(StrategyScorecardWidget(classes="scorecard-container"))

        for widget, scorecard in zip(
            container.query(StrategyScorecardWidget), self._state.scorecards
        ):
            widget.update_data(scorecard)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            best_str = (
                f" | Best Strategy: {self._state.best_strategy}"
                if self._state.best_strategy
                else ""
            )
            indicator.update(f"Last refresh: {self._state.last_refresh}{best_str}")
        except Exception:
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        self.app.pop_screen()

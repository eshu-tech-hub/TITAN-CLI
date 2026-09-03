"""Trading status card widget."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import TradingInfo
from titan.tui.widgets import markup_color


class TradingCard(Widget):
    """Displays trading mode status (live, paper, backtest)."""

    DEFAULT_CSS = """
    TradingCard {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    TradingCard .card-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    TradingCard .card-row {
        height: 1;
    }
    TradingCard .value-active {
        color: $success;
    }
    TradingCard .value-inactive {
        color: $text-muted;
    }
    TradingCard .value-default {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = TradingInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Trading", classes="card-title")
        self._live = Static("", classes="card-row")
        self._paper = Static("", classes="card-row")
        self._backtests = Static("", classes="card-row")
        yield self._title
        yield self._live
        yield self._paper
        yield self._backtests

    def update_data(self, info: TradingInfo) -> None:
        """Update card with new trading info."""
        self._info = info
        live_cls = _trading_status_class(info.live_status)
        paper_cls = _trading_status_class(info.paper_status)
        self._live.update(
            f"[bold]Live:[/bold] [{markup_color(live_cls)}]{info.live_status}[/]"
        )
        self._paper.update(
            f"[bold]Paper:[/bold] [{markup_color(paper_cls)}]{info.paper_status}[/]"
        )
        self._backtests.update(f"[bold]Backtests Today:[/bold] {info.backtests_today}")

    def render(self) -> str:  # type: ignore[override]
        return ""


def _trading_status_class(status: str) -> str:
    lower = status.lower()
    if lower in ("running", "connected", "active"):
        return "value-active"
    if lower in ("stopped", "inactive", "none"):
        return "value-inactive"
    return "value-default"

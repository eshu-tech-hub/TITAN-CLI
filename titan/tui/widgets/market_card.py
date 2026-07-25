"""Market connectivity card widget."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import MarketInfo


class MarketCard(Widget):
    """Displays broker/stream connectivity and symbol count."""

    DEFAULT_CSS = """
    MarketCard {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    MarketCard .card-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    MarketCard .card-row {
        height: 1;
    }
    MarketCard .value-connected {
        color: $success;
    }
    MarketCard .value-disconnected {
        color: $error;
    }
    MarketCard .value-default {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = MarketInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Market", classes="card-title")
        self._broker = Static("", classes="card-row")
        self._stream = Static("", classes="card-row")
        self._symbols = Static("", classes="card-row")
        yield self._title
        yield self._broker
        yield self._stream
        yield self._symbols

    def update_data(self, info: MarketInfo) -> None:
        """Update card with new market info."""
        self._info = info
        broker_cls = (
            "value-connected" if info.broker_connected else "value-disconnected"
        )
        broker_status = "Connected" if info.broker_connected else "Disconnected"
        self._broker.update(
            f'[bold]Broker:[/bold] <span class="{broker_cls}">{broker_status}</span>'
            f" ({info.broker_provider})"
        )
        stream_cls = (
            "value-connected" if info.stream_connected else "value-disconnected"
        )
        stream_status = "Connected" if info.stream_connected else "Disconnected"
        self._stream.update(
            f'[bold]Stream:[/bold] <span class="{stream_cls}">{stream_status}</span>'
        )
        self._symbols.update(f"[bold]Symbols:[/bold] {info.symbols_tracked}")

    def render(self) -> str:  # type: ignore[override]
        return ""

"""Reusable widgets for the Paper Trading screen."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import (
    PaperAccountInfo,
    PaperOrderEntry,
    PaperPerformanceInfo,
    PaperPortfolioInfo,
    PaperPositionEntry,
    PaperSessionInfo,
    PaperTradeEntry,
)
from titan.tui.widgets import markup_color


class PaperSessionWidget(Widget):
    """Displays paper trading session status, start time, and duration."""

    DEFAULT_CSS = """
    PaperSessionWidget {
        height: auto;
        min-height: 5;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    PaperSessionWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    PaperSessionWidget .card-row {
        height: 1;
    }
    PaperSessionWidget .value-running {
        color: $success;
    }
    PaperSessionWidget .value-stopped {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = PaperSessionInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Session", classes="section-title")
        self._status = Static("", classes="card-row")
        self._started = Static("", classes="card-row")
        self._duration = Static("", classes="card-row")
        yield self._title
        yield self._status
        yield self._started
        yield self._duration

    def update_data(self, info: PaperSessionInfo) -> None:
        self._info = info
        if not hasattr(self, "_status"):
            return
        lower = info.status.lower()
        if lower in ("running", "connected"):
            cls = "value-running"
        else:
            cls = "value-stopped"
        self._status.update(
            f"[bold]Status:[/bold] [{markup_color(cls)}]{info.status}[/]"
        )
        self._started.update(f"[bold]Started:[/bold] {info.started}")
        self._duration.update(f"[bold]Duration:[/bold] {info.duration}")

    def render(self) -> str:
        return ""


class AccountSummaryWidget(Widget):
    """Displays paper account funds and margin state."""

    DEFAULT_CSS = """
    AccountSummaryWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    AccountSummaryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    AccountSummaryWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = PaperAccountInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Account Summary", classes="section-title")
        self._cash = Static("", classes="card-row")
        self._used = Static("", classes="card-row")
        self._available = Static("", classes="card-row")
        self._payin = Static("", classes="card-row")
        self._payout = Static("", classes="card-row")
        yield self._title
        yield self._cash
        yield self._used
        yield self._available
        yield self._payin
        yield self._payout

    def update_data(self, info: PaperAccountInfo) -> None:
        self._info = info
        if not hasattr(self, "_cash"):
            return
        self._cash.update(f"[bold]Available Cash:[/bold] {info.available_cash}")
        self._used.update(f"[bold]Used Margin:[/bold] {info.used_margin}")
        self._available.update(
            f"[bold]Available Margin:[/bold] {info.available_margin}"
        )
        self._payin.update(f"[bold]Payin:[/bold] {info.payin}")
        self._payout.update(f"[bold]Payout:[/bold] {info.payout}")

    def render(self) -> str:
        return ""


class ActiveOrdersWidget(Widget):
    """Displays active (pending/open) orders as a dynamic list."""

    DEFAULT_CSS = """
    ActiveOrdersWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ActiveOrdersWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ActiveOrdersWidget .card-row {
        height: 1;
    }
    ActiveOrdersWidget .value-buy {
        color: $success;
    }
    ActiveOrdersWidget .value-sell {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._orders: tuple[PaperOrderEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Active Orders", classes="section-title")
        yield self._title

    def update_data(self, orders: tuple[PaperOrderEntry, ...]) -> None:
        self._orders = orders
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not orders:
            empty = Static("  No active orders", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for o in orders:
                side_cls = "value-buy" if o.side.lower() == "buy" else "value-sell"
                row = Static(
                    f"  [{markup_color(side_cls)}]{o.side.upper()}[/]"
                    f" {o.symbol} | {o.order_type} | Qty {o.quantity}"
                    f" | Filled {o.filled_quantity} | {o.price} | {o.status}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class PortfolioWidget(Widget):
    """Displays paper portfolio cash, equity, and P&L."""

    DEFAULT_CSS = """
    PortfolioWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    PortfolioWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    PortfolioWidget .card-row {
        height: 1;
    }
    PortfolioWidget .value-positive {
        color: $success;
    }
    PortfolioWidget .value-negative {
        color: $error;
    }
    PortfolioWidget .value-neutral {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = PaperPortfolioInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Portfolio", classes="section-title")
        self._cash = Static("", classes="card-row")
        self._equity = Static("", classes="card-row")
        self._unrealized = Static("", classes="card-row")
        self._realized = Static("", classes="card-row")
        yield self._title
        yield self._cash
        yield self._equity
        yield self._unrealized
        yield self._realized

    def update_data(self, info: PaperPortfolioInfo) -> None:
        self._info = info
        if not hasattr(self, "_cash"):
            return
        self._cash.update(f"[bold]Cash:[/bold] {info.cash}")
        self._equity.update(f"[bold]Equity:[/bold] {info.equity}")
        u_cls = _pnl_class(info.unrealized_pnl)
        self._unrealized.update(
            f"[bold]Unrealized P&L:[/bold] [{markup_color(u_cls)}]{info.unrealized_pnl}[/]"
        )
        r_cls = _pnl_class(info.realized_pnl)
        self._realized.update(
            f"[bold]Realized P&L:[/bold] [{markup_color(r_cls)}]{info.realized_pnl}[/]"
        )

    def render(self) -> str:
        return ""


class PerformanceWidget(Widget):
    """Displays paper trading performance metrics."""

    DEFAULT_CSS = """
    PerformanceWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    PerformanceWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    PerformanceWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = PaperPerformanceInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Performance", classes="section-title")
        self._trades = Static("", classes="card-row")
        self._win_rate = Static("", classes="card-row")
        self._pf = Static("", classes="card-row")
        self._expectancy = Static("", classes="card-row")
        self._drawdown = Static("", classes="card-row")
        yield self._title
        yield self._trades
        yield self._win_rate
        yield self._pf
        yield self._expectancy
        yield self._drawdown

    def update_data(self, info: PaperPerformanceInfo) -> None:
        self._info = info
        if not hasattr(self, "_trades"):
            return
        self._trades.update(f"[bold]Trades:[/bold] {info.total_trades}")
        self._win_rate.update(f"[bold]Win Rate:[/bold] {info.win_rate}")
        self._pf.update(f"[bold]Profit Factor:[/bold] {info.profit_factor}")
        self._expectancy.update(f"[bold]Expectancy:[/bold] {info.expectancy}")
        self._drawdown.update(f"[bold]Max Drawdown:[/bold] {info.max_drawdown}")

    def render(self) -> str:
        return ""


class PositionWidget(Widget):
    """Displays open positions as a dynamic list."""

    DEFAULT_CSS = """
    PositionWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    PositionWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    PositionWidget .card-row {
        height: 1;
    }
    PositionWidget .value-positive {
        color: $success;
    }
    PositionWidget .value-negative {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._positions: tuple[PaperPositionEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Positions", classes="section-title")
        yield self._title

    def update_data(self, positions: tuple[PaperPositionEntry, ...]) -> None:
        self._positions = positions
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not positions:
            empty = Static("  No open positions", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for pos in positions:
                pnl_cls = _pnl_class(pos.unrealized_pnl)
                row = Static(
                    f"  {pos.symbol} | Qty {pos.quantity} | "
                    f"Avg {pos.avg_price} | LTP {pos.current_price} | "
                    f"[{markup_color(pnl_cls)}]{pos.unrealized_pnl}[/]",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class TradeHistoryWidget(Widget):
    """Displays recent trades as a dynamic list."""

    DEFAULT_CSS = """
    TradeHistoryWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    TradeHistoryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    TradeHistoryWidget .card-row {
        height: 1;
    }
    TradeHistoryWidget .value-buy {
        color: $success;
    }
    TradeHistoryWidget .value-sell {
        color: $error;
    }
    TradeHistoryWidget .value-positive {
        color: $success;
    }
    TradeHistoryWidget .value-negative {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._trades: tuple[PaperTradeEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Recent Trades", classes="section-title")
        yield self._title

    def update_data(self, trades: tuple[PaperTradeEntry, ...]) -> None:
        self._trades = trades
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not trades:
            empty = Static("  No recent trades", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for t in trades:
                side_cls = "value-buy" if t.side.lower() == "buy" else "value-sell"
                pnl_cls = _pnl_class(t.pnl)
                row = Static(
                    f"  [{markup_color(side_cls)}]{t.side.upper()}[/]"
                    f" {t.symbol} | Qty {t.quantity} @ {t.price} | "
                    f"[{markup_color(pnl_cls)}]{t.pnl}[/] | {t.time}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


def _pnl_class(value: str) -> str:
    """Map a P&L string to a CSS class."""
    stripped = value.strip()
    if stripped.startswith(("-", "−")):
        return "value-negative"
    if stripped.startswith("+"):
        return "value-positive"
    cleaned = stripped.replace("₹", "").replace("INR", "").replace(",", "").strip()
    if cleaned:
        try:
            if float(cleaned) > 0:
                return "value-positive"
        except ValueError:
            pass
    return "value-neutral"

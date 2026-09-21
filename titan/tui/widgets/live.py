"""Reusable widgets for the Live Trading screen."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import (
    AccountInfo,
    BrokerStatusInfo,
    ExecutionEntry,
    ExposureInfo,
    LiveOrderEntry,
    LivePositionEntry,
    LiveStatusInfo,
)
from titan.tui.widgets import markup_color


class LiveStatusWidget(Widget):
    """Displays live trading engine status, uptime, and connectivity."""

    DEFAULT_CSS = """
    LiveStatusWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    LiveStatusWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    LiveStatusWidget .card-row {
        height: 1;
    }
    LiveStatusWidget .value-running {
        color: $success;
    }
    LiveStatusWidget .value-stopped {
        color: $error;
    }
    LiveStatusWidget .value-connected {
        color: $success;
    }
    LiveStatusWidget .value-disconnected {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = LiveStatusInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Live Status", classes="section-title")
        self._status = Static("", classes="card-row")
        self._uptime = Static("", classes="card-row")
        self._broker = Static("", classes="card-row")
        self._stream = Static("", classes="card-row")
        self._pipeline = Static("", classes="card-row")
        yield self._title
        yield self._status
        yield self._uptime
        yield self._broker
        yield self._stream
        yield self._pipeline

    def update_data(self, info: LiveStatusInfo) -> None:
        self._info = info
        if not hasattr(self, "_status"):
            return
        status_cls = _live_status_class(info.status)
        self._status.update(
            f"[bold]Status:[/bold] [{markup_color(status_cls)}]{info.status}[/]"
        )
        self._uptime.update(f"[bold]Uptime:[/bold] {info.uptime}")
        broker_cls = (
            "value-connected" if info.broker_connected else "value-disconnected"
        )
        broker_text = "Connected" if info.broker_connected else "Disconnected"
        self._broker.update(
            f"[bold]Broker:[/bold] [{markup_color(broker_cls)}]{broker_text}[/]"
        )
        stream_cls = (
            "value-connected" if info.stream_connected else "value-disconnected"
        )
        stream_text = "Connected" if info.stream_connected else "Disconnected"
        self._stream.update(
            f"[bold]Stream:[/bold] [{markup_color(stream_cls)}]{stream_text}[/]"
        )
        self._pipeline.update(
            f"[bold]Pipeline:[/bold] {info.pipeline_executions} executions"
        )

    def render(self) -> str:
        return ""


class BrokerStatusWidget(Widget):
    """Displays broker provider, connection status, and account info."""

    DEFAULT_CSS = """
    BrokerStatusWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    BrokerStatusWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    BrokerStatusWidget .card-row {
        height: 1;
    }
    BrokerStatusWidget .value-connected {
        color: $success;
    }
    BrokerStatusWidget .value-disconnected {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = BrokerStatusInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Broker", classes="section-title")
        self._provider = Static("", classes="card-row")
        self._connection = Static("", classes="card-row")
        self._exchange = Static("", classes="card-row")
        self._account = Static("", classes="card-row")
        yield self._title
        yield self._provider
        yield self._connection
        yield self._exchange
        yield self._account

    def update_data(self, info: BrokerStatusInfo) -> None:
        self._info = info
        if not hasattr(self, "_provider"):
            return
        self._provider.update(f"[bold]Provider:[/bold] {info.provider}")
        conn_cls = "value-connected" if info.is_connected else "value-disconnected"
        self._connection.update(
            f"[bold]Status:[/bold] [{markup_color(conn_cls)}]{info.connection_status}[/]"
        )
        self._exchange.update(f"[bold]Exchange:[/bold] {info.exchange or '--'}")
        self._account.update(f"[bold]Account:[/bold] {info.account_id or '--'}")

    def render(self) -> str:
        return ""


class AccountWidget(Widget):
    """Displays live account funds and margin state."""

    DEFAULT_CSS = """
    AccountWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    AccountWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    AccountWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = AccountInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Account", classes="section-title")
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

    def update_data(self, info: AccountInfo) -> None:
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


class ExposureWidget(Widget):
    """Displays portfolio exposure metrics."""

    DEFAULT_CSS = """
    ExposureWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ExposureWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ExposureWidget .card-row {
        height: 1;
    }
    ExposureWidget .value-positive {
        color: $success;
    }
    ExposureWidget .value-negative {
        color: $error;
    }
    ExposureWidget .value-neutral {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ExposureInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Exposure", classes="section-title")
        self._total = Static("", classes="card-row")
        self._long = Static("", classes="card-row")
        self._short = Static("", classes="card-row")
        self._gross = Static("", classes="card-row")
        self._net = Static("", classes="card-row")
        self._pnl = Static("", classes="card-row")
        yield self._title
        yield self._total
        yield self._long
        yield self._short
        yield self._gross
        yield self._net
        yield self._pnl

    def update_data(self, info: ExposureInfo) -> None:
        self._info = info
        if not hasattr(self, "_total"):
            return
        self._total.update(f"[bold]Total Positions:[/bold] {info.total_positions}")
        self._long.update(f"[bold]Long:[/bold] {info.long_positions}")
        self._short.update(f"[bold]Short:[/bold] {info.short_positions}")
        self._gross.update(f"[bold]Gross Exposure:[/bold] {info.gross_exposure}")
        self._net.update(f"[bold]Net Exposure:[/bold] {info.net_exposure}")
        pnl_cls = _pnl_class(info.unrealized_pnl)
        self._pnl.update(
            f"[bold]Unrealized P&L:[/bold] [{markup_color(pnl_cls)}]{info.unrealized_pnl}[/]"
        )

    def render(self) -> str:
        return ""


class LiveHealthWidget(Widget):
    """Displays live trading health: monitoring, alerts, recovery."""

    DEFAULT_CSS = """
    LiveHealthWidget {
        height: auto;
        min-height: 5;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    LiveHealthWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    LiveHealthWidget .card-row {
        height: 1;
    }
    LiveHealthWidget .value-healthy {
        color: $success;
    }
    LiveHealthWidget .value-degraded {
        color: $warning;
    }
    LiveHealthWidget .value-unhealthy {
        color: $error;
    }
    LiveHealthWidget .value-unknown {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._monitoring_status: str = "Unknown"
        self._critical_alerts: int = 0
        self._total_alerts: int = 0
        self._recovery_status: str = "Idle"
        self._recovery_attempts: int = 0

    def compose(self):  # type: ignore[override]
        self._title = Static("Health", classes="section-title")
        self._monitoring = Static("", classes="card-row")
        self._alerts = Static("", classes="card-row")
        self._recovery = Static("", classes="card-row")
        yield self._title
        yield self._monitoring
        yield self._alerts
        yield self._recovery

    def update_data(
        self,
        monitoring_status: str,
        critical_alerts: int,
        total_alerts: int,
        recovery_status: str,
        recovery_attempts: int,
    ) -> None:
        self._monitoring_status = monitoring_status
        self._critical_alerts = critical_alerts
        self._total_alerts = total_alerts
        self._recovery_status = recovery_status
        self._recovery_attempts = recovery_attempts
        if not hasattr(self, "_monitoring"):
            return
        mon_cls = _health_class(monitoring_status)
        self._monitoring.update(
            f"[bold]Monitoring:[/bold] [{markup_color(mon_cls)}]{monitoring_status}[/]"
        )
        alert_level = (
            "event-error"
            if critical_alerts > 0
            else ("event-warning" if total_alerts > 0 else "event-info")
        )
        self._alerts.update(
            f"[bold]Alerts:[/bold] [{markup_color(alert_level)}]{critical_alerts}C / {total_alerts}T[/]"
        )
        self._recovery.update(
            f"[bold]Recovery:[/bold] {recovery_status} ({recovery_attempts} attempts)"
        )

    def render(self) -> str:
        return ""


class LivePositionsWidget(Widget):
    """Displays open live positions as a dynamic list."""

    DEFAULT_CSS = """
    LivePositionsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    LivePositionsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    LivePositionsWidget .card-row {
        height: 1;
    }
    LivePositionsWidget .value-positive {
        color: $success;
    }
    LivePositionsWidget .value-negative {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._positions: tuple[LivePositionEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Open Positions", classes="section-title")
        yield self._title

    def update_data(self, positions: tuple[LivePositionEntry, ...]) -> None:
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
                pnl_cls = _pnl_class(pos.pnl)
                row = Static(
                    f"  {pos.symbol} ({pos.exchange}) | Qty {pos.quantity} | "
                    f"Avg {pos.avg_price} | LTP {pos.current_price} | "
                    f"[{markup_color(pnl_cls)}]{pos.pnl}[/]",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class LiveOrdersWidget(Widget):
    """Displays active live orders as a dynamic list."""

    DEFAULT_CSS = """
    LiveOrdersWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    LiveOrdersWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    LiveOrdersWidget .card-row {
        height: 1;
    }
    LiveOrdersWidget .value-buy {
        color: $success;
    }
    LiveOrdersWidget .value-sell {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._orders: tuple[LiveOrderEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Active Orders", classes="section-title")
        yield self._title

    def update_data(self, orders: tuple[LiveOrderEntry, ...]) -> None:
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


class ExecutionsWidget(Widget):
    """Displays recent trade executions as a dynamic list."""

    DEFAULT_CSS = """
    ExecutionsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ExecutionsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ExecutionsWidget .card-row {
        height: 1;
    }
    ExecutionsWidget .value-buy {
        color: $success;
    }
    ExecutionsWidget .value-sell {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._executions: tuple[ExecutionEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Recent Executions", classes="section-title")
        yield self._title

    def update_data(self, executions: tuple[ExecutionEntry, ...]) -> None:
        self._executions = executions
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not executions:
            empty = Static("  No recent executions", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for ex in executions:
                side_cls = "value-buy" if ex.side.lower() == "buy" else "value-sell"
                row = Static(
                    f"  [{markup_color(side_cls)}]{ex.side.upper()}[/]"
                    f" {ex.symbol} | Qty {ex.quantity} @ {ex.price}"
                    f" | {ex.trade_id} | {ex.time}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


def _live_status_class(status: str) -> str:
    """Map a live status string to a CSS class."""
    lower = status.lower()
    if lower in ("running", "connected", "active"):
        return "value-running"
    if lower in ("stopped", "error", "disconnected"):
        return "value-stopped"
    return "value-stopped"


def _pnl_class(value: str) -> str:
    """Map a P&L string to a CSS class."""
    stripped = value.strip()
    if stripped.startswith(("-", "\u2212")):
        return "value-negative"
    if stripped.startswith("+"):
        return "value-positive"
    cleaned = stripped.replace("\u20b9", "").replace("INR", "").replace(",", "").strip()
    if cleaned:
        try:
            if float(cleaned) > 0:
                return "value-positive"
        except ValueError:
            pass
    return "value-neutral"


def _health_class(status: str) -> str:
    """Map a health status string to a CSS class."""
    lower = status.lower()
    if lower in ("healthy", "ok"):
        return "value-healthy"
    if lower in ("degraded", "warning"):
        return "value-degraded"
    if lower in ("unhealthy", "error", "critical"):
        return "value-unhealthy"
    return "value-unknown"

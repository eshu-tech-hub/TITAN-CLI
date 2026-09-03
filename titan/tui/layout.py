"""TITAN TUI application layout.

The main Textual App that manages screens and navigation.
Dashboard is the default screen.
"""

from __future__ import annotations

import concurrent.futures
import sys
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App, ComposeResult
from textual.widgets import ContentSwitcher

_ipc_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

if TYPE_CHECKING:
    from titan.tui.models import AIScreenState, StrategyEvalScreenState

from titan.tui.models import (
    AccountInfo,
    BrokerStatusInfo,
    DashboardState,
    ExecutionEntry,
    ExposureInfo,
    HealthInfo,
    LiveOrderEntry,
    LivePositionEntry,
    LiveScreenState,
    LiveStatusInfo,
    MarketInfo,
    MarketScreenState,
    MarketStatusInfo,
    MonitoringScreenState,
    PaperAccountInfo,
    PaperOrderEntry,
    PaperPerformanceInfo,
    PaperPortfolioInfo,
    PaperPositionEntry,
    PaperScreenState,
    PaperSessionInfo,
    PaperTradeEntry,
    PortfolioScreenState,
    RuntimeComponentInfo,
    RuntimeEngineInfo,
    RuntimeEventBusInfo,
    RuntimeEventEntry,
    RuntimeInfo,
    RuntimePipelineInfo,
    RuntimeScreenState,
    RuntimeStreamInfo,
    SystemInfo,
    TradingInfo,
)
from titan.tui.screens.dashboard import DashboardScreen
from titan.tui.screens.paper import PaperScreen
from titan.tui.screens.runtime import RuntimeScreen

if TYPE_CHECKING:
    from collections.abc import Callable

    from titan.tui.models import (
        AlertEntry,
        AlertHistoryEntry,
        AlertSummaryInfo,
        AuditEntry,
        AuditScreenState,
        AuditSummaryInfo,
        BackupInfo,
        BackupStatusInfo,
        CheckpointInfo,
        CircuitBreakerInfo,
        ConfigurationInfo,
        ConfigurationScreenState,
        DecisionEvidenceInfo,
        DecisionJournalEntry,
        DecisionQualificationInfo,
        DecisionReasonEntry,
        DecisionRiskInfo,
        DecisionScreenState,
        DecisionSummaryInfo,
        DecisionTimelineEntry,
        DeploymentHistoryEntry,
        DeploymentInfo,
        EnvironmentInfo,
        EvidenceSummaryInfo,
        GreeksSummaryInfo,
        LiquidityInfo,
        LogEntry,
        LogSummaryInfo,
        MarketEventEntry,
        MarketScreenState,
        MarketStatusInfo,
        MonitoringEventEntry,
        MonitoringScreenState,
        OpenInterestSummaryInfo,
        OptionChainSummaryInfo,
        RecoveryHistoryEntry,
        RecoveryStatusInfo,
        RegimeInfo,
        ReplayScreenState,
        ResourceMetricsInfo,
        ServiceStatusEntry,
        SystemHealthInfo,
        TelemetryInfo,
        TradeJournalScreenState,
        VersionInfo,
        VolatilityInfo,
    )


class TITANApp(App):
    """Main TITAN TUI application.

    Manages mounted views via ContentSwitcher and keyboard navigation.
    Dashboard is the default view.
    """

    CSS = """
    Screen {
        background: $surface;
    }
    #app-content {
        width: 1fr;
        height: 1fr;
    }
    #app-content > * {
        width: 1fr;
        height: 1fr;
    }
    """

    TITLE = "TITAN"
    SUB_TITLE = "Trading Intelligence & Tactical Analysis Network"

    BINDINGS: ClassVar[list] = [
        ("up", "focus_previous", "Focus Up"),
        ("down", "focus_next", "Focus Down"),
        ("enter", "select", "Select"),
        ("q", "quit", "Quit"),
        ("f1", "show_dashboard", "Dashboard"),
        ("f2", "show_runtime", "Runtime"),
        ("f3", "show_paper", "Paper"),
        ("f10", "show_decision_replay", "Replay"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state_builder: Callable[[], DashboardState] | None = None
        self._runtime_state_builder: Callable[[], RuntimeScreenState] | None = None
        self._paper_state_builder: Callable[[], PaperScreenState] | None = None
        self._replay_state_builder: Callable[[str | None], ReplayScreenState] | None = (
            None
        )
        self._views: dict[str, Any] = {}
        self._content_switcher: ContentSwitcher | None = None
        self._history: deque[str] = deque()

    def compose(self) -> ComposeResult:
        """Mount the four built-in views into a ContentSwitcher."""
        from titan.tui.screens.decision_replay import DecisionReplayScreen

        self._views = {
            "dashboard": DashboardScreen(),
            "runtime": RuntimeScreen(),
            "paper": PaperScreen(),
            "decision_replay": DecisionReplayScreen(),
        }
        self._content_switcher = ContentSwitcher(
            id="app-content", initial="view-dashboard"
        )
        with self._content_switcher:
            for name, view in self._views.items():
                view.id = f"view-{name}"
                yield view

    def on_mount(self) -> None:
        """Apply state builders and show the default dashboard view."""
        for name, view in self._views.items():
            builder: Callable[..., Any] | None = {
                "dashboard": self._state_builder,
                "runtime": self._runtime_state_builder,
                "paper": self._paper_state_builder,
                "decision_replay": self._replay_state_builder,
            }.get(name)
            if builder is not None:
                view.set_state_builder(builder)
        assert self._content_switcher is not None
        self._content_switcher.current = "view-dashboard"
        self.query_one("#view-dashboard").focus()

    def set_state_builder(self, builder: Callable[[], DashboardState]) -> None:
        """Set the function that builds DashboardState from managers."""
        self._state_builder = builder

    def set_runtime_state_builder(
        self, builder: Callable[[], RuntimeScreenState]
    ) -> None:
        """Set the function that builds RuntimeScreenState from managers."""
        self._runtime_state_builder = builder

    def set_paper_state_builder(self, builder: Callable[[], PaperScreenState]) -> None:
        """Set the function that builds PaperScreenState from managers."""
        self._paper_state_builder = builder

    def set_replay_state_builder(
        self, builder: Callable[[str | None], ReplayScreenState]
    ) -> None:
        """Set the function that builds ReplayScreenState."""
        self._replay_state_builder = builder

    def _show(self, name: str) -> None:
        """Switch the ContentSwitcher to the named view and focus it."""
        if self._content_switcher is None:
            return
        target = f"view-{name}"
        if self._content_switcher.current == target:
            return
        current = self._content_switcher.current
        if current:
            self._history.append(current.removeprefix("view-"))
        self._content_switcher.current = target
        self.query_one(f"#{target}").focus()

    def action_show_dashboard(self) -> None:
        """Navigate to the Dashboard view."""
        self._show("dashboard")

    def action_show_runtime(self) -> None:
        """Navigate to the Runtime view."""
        self._show("runtime")

    def action_show_paper(self) -> None:
        """Navigate to the Paper Trading view."""
        self._show("paper")

    def action_show_decision_replay(self) -> None:
        """Navigate to the Decision Replay view."""
        self._show("decision_replay")

    def action_go_back(self) -> None:
        """Navigate back to the previous view."""
        if self._content_switcher is None or not self._history:
            return
        prev = self._history.pop()
        self._content_switcher.current = f"view-{prev}"
        self.query_one(f"#view-{prev}").focus()

    def action_focus_previous(self) -> None:
        """Move focus to the previous widget."""
        self.screen.focus_previous()

    def action_focus_next(self) -> None:
        """Move focus to the next widget."""
        self.screen.focus_next()

    def action_select(self) -> None:
        """Select/focused widget action (placeholder for future pages)."""


def build_portfolio_state() -> PortfolioScreenState:
    """Build PortfolioScreenState with a fallback if managers are missing."""
    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display
    return PortfolioScreenState(last_refresh=now)


def build_dashboard_state() -> DashboardState:
    """Build DashboardState by reading all managers (read-only).

    This is the state builder function that gets injected into the TUI.
    All manager access is try/except guarded for resilience.
    """
    runtime = _read_runtime()
    market = _read_market()
    trading = _read_trading()
    health = _read_health()
    system = _read_system()

    from datetime import datetime

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    return DashboardState(
        runtime=runtime,
        market=market,
        trading=trading,
        health=health,
        system=system,
        last_refresh=now,
    )


def _read_runtime() -> RuntimeInfo:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        report = engine.generate_report()
        return RuntimeInfo(
            status=report.runtime_status.name,
            uptime=_format_uptime(report.performance.uptime_seconds),
            is_running=engine.is_running,
            pipeline_executions=report.scheduler.pipeline_executions,
            broker_status=report.broker.connection,
            stream_status=report.market.stream_status,
        )
    except Exception:  # noqa: BLE001
        return RuntimeInfo()


def _read_market() -> MarketInfo:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        report = engine.generate_report()
        connected = report.broker.connection.lower() == "connected"
        return MarketInfo(
            broker_connected=connected,
            broker_provider="Paper",
            stream_connected=report.market.stream_status.lower() == "connected",
            symbols_tracked=report.market.active_subscriptions,
            last_quote_time=(
                report.market.last_quote_time.strftime("%H:%M:%S")
                if report.market.last_quote_time
                else "Never"
            ),
        )
    except Exception:  # noqa: BLE001
        return MarketInfo()


def _read_trading() -> TradingInfo:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        live_status = "Running" if engine.is_running else "Stopped"
        return TradingInfo(live_status=live_status)
    except Exception:  # noqa: BLE001
        return TradingInfo()


def _read_health() -> HealthInfo:
    try:
        from titan.cli.common import get_monitoring_manager

        mon = get_monitoring_manager()
        mon_report = mon.generate_report()
        monitoring_status = (
            str(mon_report.system_health) if mon_report.system_health else "Unknown"
        )
    except Exception:  # noqa: BLE001
        monitoring_status = "Unknown"

    try:
        from titan.cli.common import get_alert_manager

        al = get_alert_manager()
        al_report = al.generate_report()
        critical = al_report.critical_alerts
        total = al_report.total_alerts
    except Exception:  # noqa: BLE001
        critical = 0
        total = 0

    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        rm_report = rm.generate_report()
        recovery_status = (
            rm_report.status.value
            if hasattr(rm_report.status, "value")
            else str(rm_report.status)
        )
        recovery_attempts = rm_report.total_attempts
    except Exception:  # noqa: BLE001
        recovery_status = "Idle"
        recovery_attempts = 0

    return HealthInfo(
        monitoring_status=monitoring_status,
        critical_alerts=critical,
        total_alerts=total,
        recovery_status=recovery_status,
        recovery_attempts=recovery_attempts,
    )


def _read_system() -> SystemInfo:
    try:
        from titan.cli.common import get_deployment_manager

        dm = get_deployment_manager()
        report = dm.generate_report()
        return SystemInfo(
            version=report.version.version,
            environment=report.environment.value,
            deployment_status=report.status.value,
            uptime=_format_uptime(report.uptime_seconds),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    except Exception:  # noqa: BLE001
        return SystemInfo(
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )


def _format_uptime(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_relative_time(dt: datetime | None) -> str:
    """Format a datetime as a relative time string."""
    if dt is None:
        return "Never"
    now = datetime.now()  # noqa: DTZ005 - local time for display
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    delta = (now - dt).total_seconds()
    if delta <= 0.1:
        return "Just now"
    if delta < 1:
        return "< 1 sec ago"
    if delta < 60:
        return f"{delta:.1f} sec ago"
    if delta < 3600:
        mins = int(delta // 60)
        return f"{mins} min ago"
    hours = int(delta // 3600)
    return f"{hours} hr ago"


def build_runtime_state() -> RuntimeScreenState:
    """Build RuntimeScreenState by reading all managers (read-only).

    All manager access is try/except guarded for resilience.
    """
    engine_info = _read_runtime_engine()
    stream_info = _read_runtime_stream()
    pipeline_info = _read_runtime_pipeline()
    event_bus_info = _read_runtime_event_bus()
    components = _read_runtime_components()
    events = _read_runtime_events()

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    return RuntimeScreenState(
        engine=engine_info,
        stream=stream_info,
        pipeline=pipeline_info,
        event_bus=event_bus_info,
        components=components,
        events=events,
        last_refresh=now,
    )


def _read_runtime_engine() -> RuntimeEngineInfo:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        status = engine.status.name
        is_running = engine.is_running
        
        uptime = "00:00:00"
        scheduler_active = False
        try:
            report = engine.generate_report()
            uptime = _format_uptime(report.performance.uptime_seconds)
            scheduler_active = report.scheduler.active
        except Exception:
            pass

        return RuntimeEngineInfo(
            status=status,
            uptime=uptime,
            is_running=is_running,
            scheduler_active=scheduler_active,
        )
    except Exception:  # noqa: BLE001
        return RuntimeEngineInfo()


def _read_runtime_stream() -> RuntimeStreamInfo:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        report = engine.generate_report()
        return RuntimeStreamInfo(
            connected=report.market.stream_status.lower() == "connected",
            symbols_tracked=report.market.active_subscriptions,
            tick_rate="N/A",
        )
    except Exception:  # noqa: BLE001
        return RuntimeStreamInfo()


def _read_runtime_pipeline() -> RuntimePipelineInfo:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        report = engine.generate_report()
        return RuntimePipelineInfo(
            executions=report.scheduler.pipeline_executions,
            avg_runtime="N/A",
            last_run=_format_relative_time(report.scheduler.last_pipeline_time),
        )
    except Exception:  # noqa: BLE001
        return RuntimePipelineInfo()


def _read_runtime_event_bus() -> RuntimeEventBusInfo:
    try:
        from titan.cli.common import get_runtime_engine
        from titan.runtime.models import RuntimeEventType

        engine = get_runtime_engine()
        bus = engine.event_bus
        total_subscribers = 0
        for event_type in RuntimeEventType:
            total_subscribers += bus.listener_count(event_type)
        return RuntimeEventBusInfo(
            published=0,
            subscribers=total_subscribers,
        )
    except Exception:  # noqa: BLE001
        return RuntimeEventBusInfo()


def _read_runtime_components() -> tuple[RuntimeComponentInfo, ...]:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        report = engine.generate_report()
        return tuple(
            RuntimeComponentInfo(
                name=comp.component_name,
                status=comp.status.value,
            )
            for comp in report.health.component_health
        )
    except Exception:  # noqa: BLE001
        return ()


def _read_runtime_events() -> tuple[RuntimeEventEntry, ...]:
    entries: list[RuntimeEventEntry] = []
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        report = engine.generate_report()
        for warning in report.health.warnings:
            entries.append(
                RuntimeEventEntry(level="warning", source="runtime", message=warning)
            )
        for error in report.health.errors:
            entries.append(
                RuntimeEventEntry(level="error", source="runtime", message=error)
            )
    except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
        pass
    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        history = rm.get_recovery_history()
        for recovery in history[-10:]:
            entries.append(
                RuntimeEventEntry(
                    level="info",
                    source=str(recovery.component.value),
                    message=(
                        f"Recovery {recovery.status.value}: {recovery.failure_reason}"
                        if recovery.failure_reason
                        else f"Recovery {recovery.status.value}"
                    ),
                )
            )
    except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
        pass
    return tuple(entries[-20:])


# ─── Paper Trading state builder ─────────────────────────────


def build_paper_state() -> PaperScreenState:
    """Build PaperScreenState by reading paper managers (read-only).

    All manager access is try/except guarded for resilience.
    """
    data = _get_paper_data()

    session = _read_paper_session(data)
    account = _read_paper_accounts(data)
    portfolio = _read_paper_portfolio(data)
    performance = _read_paper_performance(data)
    positions = _read_paper_positions(data)
    orders = _read_paper_orders(data)
    trades = _read_paper_trades(data)

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    return PaperScreenState(
        session=session,
        account=account,
        portfolio=portfolio,
        performance=performance,
        positions=positions,
        orders=orders,
        trades=trades,
        last_refresh=now,
    )


def _get_paper_data() -> dict[str, Any]:
    from titan.cli.common import get_runtime_engine

    def _fetch_paper_ipc():
        import gc
        import socket

        from titan.runtime.local_transport import LocalTransport

        # Bypass Textual's Windows IPv6 localhost hijacking
        _orig_getaddrinfo = socket.getaddrinfo

        def _ipv4_override(*args, **kwargs):
            if args and args[0] == "localhost":
                args = ("127.0.0.1",) + args[1:]
            return _orig_getaddrinfo(*args, **kwargs)

        socket.getaddrinfo = _ipv4_override
        try:
            client = LocalTransport()
            # Redundancy overrides
            if hasattr(client, "host"):
                client.host = "127.0.0.1"
            if hasattr(client, "_host"):
                client._host = "127.0.0.1"
            if hasattr(client, "base_url"):
                client.base_url = client.base_url.replace("localhost", "127.0.0.1")

            return client.paper_status()
        finally:
            socket.getaddrinfo = _orig_getaddrinfo
            if hasattr(client, "close"):
                client.close()
            elif hasattr(client, "disconnect"):
                client.disconnect()
            elif hasattr(client, "_session") and hasattr(client._session, "close"):
                client._session.close()
            del client
            gc.collect()

    # 1. Primary: Thread-isolated IPC using a persistent executor and socket
    try:
        transport_data = _ipc_executor.submit(_fetch_paper_ipc).result(timeout=1.0)
        if transport_data and transport_data.get("running") is True:
            return transport_data
    except Exception as e:
        # Log the invisible killer so we are never blind again
        with open("tui_ipc_debug.log", "a") as f:
            f.write(f"Paper IPC Error: {type(e).__name__}: {e}\n")

    # 2. Fallback: (Keep your existing fallback logic here)
    try:
        engine = get_runtime_engine()
        if engine.status.name in ("RUNNING", "STARTING") and hasattr(engine, "broker"):
            if getattr(engine.broker, "__class__", type(engine.broker)).__name__ == "PaperBroker":
                if engine.broker.is_connected():
                    return {"_in_process_broker": engine.broker, "running": True}
    except Exception:
        pass

    return {}


def _read_paper_session(data: dict[str, Any]) -> PaperSessionInfo:
    try:
        if not data or not data.get("running"):
            return PaperSessionInfo()

        # Branch A: In-Process Fallback
        if "_in_process_broker" in data:
            from titan.cli.commands.paper import _paper_start_time
            uptime = 0.0
            started_str = "--:--"
            if _paper_start_time is not None:
                uptime = (datetime.now() - _paper_start_time).total_seconds()  # noqa: DTZ005
                started_str = _paper_start_time.strftime("%H:%M")
            return PaperSessionInfo(
                status="Running",
                started=started_str,
                duration=_format_uptime(uptime),
            )

        # Branch B: IPC Flat Dictionary (From LocalTransport)
        uptime = data.get("session_uptime_seconds", 0.0)
        start_time_iso = data.get("start_time")
        started_str = "--:--"
        if start_time_iso:
            try:
                dt = datetime.fromisoformat(start_time_iso)
                started_str = dt.strftime("%H:%M")
            except ValueError:
                pass
                
        return PaperSessionInfo(
            status="Running",
            started=started_str,
            duration=_format_uptime(uptime),
        )
    except Exception:  # noqa: BLE001
        return PaperSessionInfo()


def _read_paper_accounts(data: dict[str, Any]) -> PaperAccountInfo:
    try:
        if not data or not data.get("running"):
            return PaperAccountInfo()

        # Branch A: In-Process Fallback
        if "_in_process_broker" in data:
            broker = data["_in_process_broker"]
            funds = getattr(broker, "funds", lambda: None)()
            margin = getattr(broker, "margin", lambda: None)()
            return PaperAccountInfo(
                available_cash=_format_inr(getattr(funds, "available_cash", 0.0)),
                used_margin=_format_inr(getattr(margin, "used_margin", 0.0)),
                available_margin=_format_inr(getattr(margin, "available_margin", getattr(funds, "buying_power", 0.0))),
                payin=_format_inr(getattr(funds, "payin", getattr(broker, "_initial_cash", 100000.0))),
                payout=_format_inr(getattr(funds, "payout", 0.0)),
            )

        # Branch B: IPC Flat Dictionary (From LocalTransport)
        initial = float(data.get("initial_cash", 0.0))
        buying_power = float(data.get("buying_power", data.get("available_margin", 0.0)))
        used_margin = float(data.get("used_margin", data.get("exposure", 0.0)))
        
        # If used_margin is reported as 0 but buying_power is less than initial cash
        if used_margin == 0.0 and initial > buying_power:
            used_margin = initial - buying_power

        return PaperAccountInfo(
            available_cash=_format_inr(data.get("cash_balance", data.get("available_cash", 0.0))),
            used_margin=_format_inr(used_margin),
            available_margin=_format_inr(buying_power),
            payin=_format_inr(initial),
            payout=_format_inr(data.get("payout", 0.0)),
        )
    except Exception:  # noqa: BLE001
        return PaperAccountInfo()


def _read_paper_portfolio(data: dict[str, Any]) -> PaperPortfolioInfo:
    try:
        if not data or not data.get("running"):
            return PaperPortfolioInfo()

        # Branch A: In-Process Fallback
        if "_in_process_broker" in data:
            broker = data["_in_process_broker"]
            positions = getattr(broker.position_engine, "open_positions", list)()
            ps = getattr(broker.portfolio, "compute_state", lambda p: None)(positions)
            if ps:
                realized = sum(
                    (getattr(p, "realized_pnl", 0) for p in getattr(broker.position_engine, "all_positions", list)()),
                    __import__("decimal").Decimal("0"),
                )
                unrealized = ps.total_pnl - realized
                return PaperPortfolioInfo(
                    cash=f"INR {getattr(ps, 'cash', 0):,.0f}",
                    equity=f"INR {getattr(ps, 'equity', 0):,.0f}",
                    unrealized_pnl=_format_pnl(unrealized),
                    realized_pnl=_format_pnl(realized),
                )

        # Branch B: IPC Flat Dictionary (From LocalTransport)
        cash = float(data.get("cash_balance", 0.0))
        equity = float(data.get("portfolio_value", 0.0))

        return PaperPortfolioInfo(
            cash=f"INR {cash:,.0f}",
            equity=f"INR {equity:,.0f}",
            unrealized_pnl=_format_pnl(data.get("unrealized_pnl", 0.0)),
            realized_pnl=_format_pnl(data.get("realized_pnl", 0.0)),
        )
    except Exception:  # noqa: BLE001
        return PaperPortfolioInfo()


def _read_paper_performance(data: dict[str, Any]) -> PaperPerformanceInfo:
    try:
        if not data or not data.get("running"):
            return PaperPerformanceInfo()

        # Branch A: In-Process Fallback
        if "_in_process_broker" in data:
            broker = data["_in_process_broker"]
            positions = getattr(broker.position_engine, "open_positions", list)()
            ps = getattr(broker.portfolio, "compute_state", lambda p: None)(positions)
            if ps:
                perf = getattr(broker.performance, "compute", lambda p: None)(ps)
                if perf:
                    exp_val = float(getattr(perf, "expectancy", 0))
                    return PaperPerformanceInfo(
                        total_trades=getattr(perf, "total_trades", 0),
                        win_rate=f"{getattr(perf, 'win_rate', 0) * 100:.0f}%",
                        profit_factor=f"{getattr(perf, 'profit_factor', 0):.2f}",
                        expectancy=f"{'+' if exp_val >= 0 else ''}{exp_val:.2f}R",
                        max_drawdown=f"{float(getattr(perf, 'max_drawdown', 0)) * 100:.1f}%",
                    )

        # Branch B: IPC Flat Dictionary (From LocalTransport)
        exp_val = float(data.get("expectancy", 0.0))
        win_rate = float(data.get("win_rate", 0.0))
        drawdown = float(data.get("max_drawdown", 0.0))
        
        return PaperPerformanceInfo(
            total_trades=data.get("total_trades", 0),
            win_rate=f"{win_rate * 100:.0f}%",
            profit_factor=f"{float(data.get('profit_factor', 0.0)):.2f}",
            expectancy=f"{'+' if exp_val >= 0 else ''}{exp_val:.2f}R",
            max_drawdown=f"{drawdown * 100:.1f}%",
        )
    except Exception:  # noqa: BLE001
        return PaperPerformanceInfo()


def _read_paper_positions(data: dict[str, Any]) -> tuple[PaperPositionEntry, ...]:
    try:
        if not data or not data.get("running"):
            return ()

        # Branch A: In-Process Fallback
        if "_in_process_broker" in data:
            broker = data["_in_process_broker"]
            open_pos = getattr(broker.position_engine, "open_positions", list)()
            return tuple(
                PaperPositionEntry(
                    symbol=getattr(p, "symbol", ""),
                    quantity=getattr(p, "quantity", 0),
                    avg_price=f"INR {p.average_price}" if getattr(p, "average_price", None) else "0",
                    current_price=f"INR {p.current_price}" if getattr(p, "current_price", None) else "0",
                    unrealized_pnl=_format_pnl(getattr(p, "unrealized_pnl", 0)),
                )
                for p in open_pos
            )

        # Branch B: IPC Flat Dictionary (From LocalTransport)
        positions = data.get("positions", [])
        return tuple(
            PaperPositionEntry(
                symbol=str(p.get("symbol", "")),
                quantity=int(p.get("quantity", 0)),
                avg_price=f"INR {p.get('average_price', 0.0)}",
                current_price=f"INR {p.get('current_price', 0.0)}",
                unrealized_pnl=_format_pnl(p.get("unrealized_pnl", 0.0)),
            )
            for p in positions
        )
    except Exception:  # noqa: BLE001
        return ()


def _read_paper_trades(data: dict[str, Any]) -> tuple[PaperTradeEntry, ...]:
    try:
        if not data or not data.get("running"):
            return ()

        # Branch A: In-Process Fallback
        if "_in_process_broker" in data:
            broker = data["_in_process_broker"]
            fills = getattr(broker.journal, "to_broker_trades", list)()
            entries: list[PaperTradeEntry] = []
            for trade in fills[-20:]:
                side_val = getattr(trade.side, "value", str(getattr(trade, "side", ""))) if hasattr(trade, "side") else ""
                entries.append(
                    PaperTradeEntry(
                        symbol=getattr(trade, "symbol", ""),
                        side=side_val,
                        quantity=getattr(trade, "quantity", 0),
                        price=f"INR {getattr(trade, 'price', 0)}",
                        pnl=_format_pnl(getattr(trade, 'pnl', 0)),
                        time=(
                            trade.timestamp.strftime("%H:%M")
                            if hasattr(trade, "timestamp") and getattr(trade, "timestamp", None)
                            else ""
                        ),
                    )
                )
            return tuple(entries)

        # Branch B: IPC Flat Dictionary (From LocalTransport)
        trades = data.get("trades", [])
        entries = []
        for t in trades[-20:]:
            time_str = ""
            ts = t.get("timestamp")
            if ts:
                try:
                    time_str = datetime.fromisoformat(ts).strftime("%H:%M")
                except ValueError:
                    pass
            entries.append(
                PaperTradeEntry(
                    symbol=str(t.get("symbol", "")),
                    side=str(t.get("side", "")),
                    quantity=int(t.get("quantity", 0)),
                    price=f"INR {t.get('price', 0.0)}",
                    pnl=_format_pnl(t.get("pnl", 0.0)),
                    time=time_str,
                )
            )
        return tuple(entries)
    except Exception:  # noqa: BLE001
        return ()


def _read_paper_orders(data: dict[str, Any]) -> tuple[PaperOrderEntry, ...]:
    try:
        if not data or not data.get("running"):
            return ()

        # Branch A: In-Process Fallback
        if "_in_process_broker" in data:
            broker = data["_in_process_broker"]
            all_orders = getattr(broker, "orders", list)()
            active: list[PaperOrderEntry] = []
            for o in all_orders:
                status_str = getattr(o.status, "value", str(getattr(o, "status", ""))) if hasattr(o, "status") else ""
                if status_str not in ("pending", "open", "partially_filled"):
                    continue
                side_val = getattr(o.side, "value", str(getattr(o, "side", ""))) if hasattr(o, "side") else ""
                ot_val = getattr(o.order_type, "value", str(getattr(o, "order_type", ""))) if hasattr(o, "order_type") else ""
                price_str = _format_inr(getattr(o, "average_price", getattr(o, "price", 0)))
                placed_str = ""
                if getattr(o, "placed_at", None):
                    placed_str = o.placed_at.strftime("%H:%M")
                active.append(
                    PaperOrderEntry(
                        order_id=getattr(o, "broker_order_id", ""),
                        symbol=getattr(o, "symbol", ""),
                        side=side_val,
                        order_type=ot_val,
                        quantity=getattr(o, "quantity", 0),
                        filled_quantity=getattr(o, "filled_quantity", 0),
                        price=price_str,
                        status=status_str,
                        placed_at=placed_str,
                    )
                )
            return tuple(active)

        # Branch B: IPC Flat Dictionary (From LocalTransport)
        orders = data.get("orders", [])
        active = []
        for o in orders:
            status = str(o.get("status", ""))
            if status not in ("pending", "open", "partially_filled"):
                continue
                
            placed_str = ""
            ts = o.get("placed_at")
            if ts:
                try:
                    placed_str = datetime.fromisoformat(ts).strftime("%H:%M")
                except ValueError:
                    pass
                    
            active.append(
                PaperOrderEntry(
                    order_id=str(o.get("order_id", o.get("broker_order_id", ""))),
                    symbol=str(o.get("symbol", "")),
                    side=str(o.get("side", "")),
                    order_type=str(o.get("type", o.get("order_type", ""))),
                    quantity=int(o.get("quantity", 0)),
                    filled_quantity=int(o.get("filled_quantity", 0)),
                    price=_format_inr(o.get("price", o.get("average_price", 0))),
                    status=status,
                    placed_at=placed_str,
                )
            )
        return tuple(active)
    except Exception:  # noqa: BLE001
        return ()


from decimal import Decimal


def _format_inr(value: Any) -> str:
    """Safely format numeric values to INR currency string."""
    if value is None:
        return "INR 0"
    try:
        dec_val = Decimal(str(value))
        if dec_val < 0:
            return f"-INR {abs(dec_val):,.0f}"
        return f"INR {dec_val:,.0f}"
    except Exception:  # noqa: BLE001
        return "INR 0"


def _format_pnl(value: Any) -> str:
    """Safely format PnL values with + / - signs."""
    if value is None:
        return "+INR 0"
    try:
        dec_val = Decimal(str(value))
        if dec_val < 0:
            return f"-INR {abs(dec_val):,.0f}"
        return f"+INR {abs(dec_val):,.0f}"
    except Exception:  # noqa: BLE001
        return "+INR 0"


def _format_pct(value: object) -> str:
    """Format a float as a percentage string."""
    try:
        return f"{float(str(value)) * 100:.0f}%"
    except Exception:  # noqa: BLE001
        return "0%"


def _format_float(value: object, decimals: int = 2) -> str:
    """Format a float with fixed decimals."""
    try:
        return f"{float(str(value)):.{decimals}f}"
    except Exception:  # noqa: BLE001
        return "0"


def _format_volume(value: object) -> str:
    """Format volume with K/M suffix."""
    try:
        v = float(str(value))
        if v >= 1_000_000:
            return f"{v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v / 1_000:.1f}K"
        return f"{v:.0f}"
    except Exception:  # noqa: BLE001
        return "0"


# ─── Live Trading state builder ─────────────────────────────


def build_live_state() -> LiveScreenState:
    """Build LiveScreenState by reading all managers (read-only).

    All manager access is try/except guarded for resilience.
    """
    live_status = _read_live_status()
    broker_status = _read_broker_status()
    account = _read_live_account()
    exposure = _read_live_exposure()
    positions = _read_live_positions()
    orders = _read_live_orders()
    executions = _read_recent_executions()

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    return LiveScreenState(
        live_status=live_status,
        broker_status=broker_status,
        account=account,
        exposure=exposure,
        positions=positions,
        orders=orders,
        executions=executions,
        last_refresh=now,
    )


def _get_live_data() -> dict[str, Any]:
    """Query the live runtime state."""

    # Primary check: Inspect get_runtime_engine()
    try:
        from titan.cli.common import get_runtime_engine
        engine = get_runtime_engine()
        if engine.status.name in ("RUNNING", "STARTING"):
            broker = engine.broker
            if getattr(broker, "__class__", type(broker)).__name__ != "PaperBroker":
                if broker.is_connected():
                    return {"_in_process_broker": broker, "running": True}
    except Exception:
        pass

    # Secondary fallback: Thread-isolated IPC to bypass Textual's active asyncio loop
    try:
        def _fetch_live_ipc():
            import gc
            import socket

            from titan.runtime.local_transport import LocalTransport

            # Bypass Textual's Windows IPv6 localhost hijacking
            _orig_getaddrinfo = socket.getaddrinfo

            def _ipv4_override(*args, **kwargs):
                if args and args[0] == "localhost":
                    args = ("127.0.0.1",) + args[1:]
                return _orig_getaddrinfo(*args, **kwargs)

            socket.getaddrinfo = _ipv4_override
            try:
                client = LocalTransport()
                # Redundancy overrides
                if hasattr(client, "host"):
                    client.host = "127.0.0.1"
                if hasattr(client, "_host"):
                    client._host = "127.0.0.1"
                if hasattr(client, "base_url"):
                    client.base_url = client.base_url.replace("localhost", "127.0.0.1")

                return client.live_status()
            finally:
                socket.getaddrinfo = _orig_getaddrinfo
                if hasattr(client, "close"):
                    client.close()
                elif hasattr(client, "disconnect"):
                    client.disconnect()
                elif hasattr(client, "_session") and hasattr(client._session, "close"):
                    client._session.close()
                del client
                gc.collect()
            
        transport_data = _ipc_executor.submit(_fetch_live_ipc).result(timeout=1.0)
        if transport_data:
            return transport_data
    except Exception as e:
        # Log the invisible killer so we are never blind again
        with open("tui_ipc_debug.log", "a") as f:
            f.write(f"Live IPC Error: {type(e).__name__}: {e}\n")

    # Tertiary fallback: Empty default DTO
    return {"running": False}

def _read_live_status() -> LiveStatusInfo:
    try:
        
        try:
            transport = LocalTransport()
            report = transport.status()
            return LiveStatusInfo(
                status=report.runtime_status.name,
                uptime=_format_uptime(report.performance.uptime_seconds),
                is_running=report.runtime_status.name in ("RUNNING", "STARTING"),
                broker_connected=report.broker.connection.value.lower() == "connected",
                stream_connected=report.market.stream_status.lower() == "connected",
                pipeline_executions=report.scheduler.pipeline_executions,
            )
        except Exception:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
            return LiveStatusInfo(
                status=report.runtime_status.name,
                uptime=_format_uptime(report.performance.uptime_seconds),
                is_running=engine.is_running,
                broker_connected=report.broker.connection.value.lower() == "connected",
                stream_connected=report.market.stream_status.lower() == "connected",
                pipeline_executions=report.scheduler.pipeline_executions,
            )
    except Exception:  # noqa: BLE001
        return LiveStatusInfo()


def _read_broker_status() -> BrokerStatusInfo:
    try:

        try:
            transport = LocalTransport()
            report = transport.status()
            # If IPC succeeds, pull provider from live_status data
            data = transport.live_status()
            provider = data.get("provider", "Unknown")
            is_connected = data.get("is_connected", False)
            
            return BrokerStatusInfo(
                provider=provider,
                connection_status=report.broker.connection.value,
                is_connected=is_connected,
                exchange="",
                account_id="",
            )
        except Exception:
            from titan.cli.common import get_runtime_engine
            engine = get_runtime_engine()
            report = engine.generate_report()
            broker = engine.broker
            is_connected = broker.is_connected()
            provider = type(broker).__name__
            return BrokerStatusInfo(
                provider=provider,
                connection_status=report.broker.connection.value,
                is_connected=is_connected,
                exchange="",
                account_id="",
            )
    except Exception:  # noqa: BLE001
        return BrokerStatusInfo()


def _read_live_account() -> AccountInfo:
    try:
        data = _get_live_data()
        if data.get("running"):
            funds = data.get("funds", {})
            margin = data.get("margin", {})
            return AccountInfo(
                available_cash=_format_inr(funds.get("available_cash", 0.0)),
                used_margin=_format_inr(margin.get("used_margin", 0.0)),
                available_margin=_format_inr(margin.get("available_margin", 0.0)),
                payin=_format_inr(funds.get("payin", 0.0)),
                payout=_format_inr(funds.get("payout", 0.0)),
            )

        from titan.cli.common import get_runtime_engine
        engine = get_runtime_engine()
        broker = engine.broker
        funds_obj = broker.funds()
        margin_obj = broker.margin()
        return AccountInfo(
            available_cash=_format_inr(funds_obj.available_cash),
            used_margin=_format_inr(margin_obj.used_margin),
            available_margin=_format_inr(margin_obj.available_margin),
            payin=_format_inr(funds_obj.payin),
            payout=_format_inr(funds_obj.payout),
        )
    except Exception:  # noqa: BLE001
        return AccountInfo()


def _read_live_exposure() -> ExposureInfo:
    try:
        data = _get_live_data()
        if data.get("running"):
            positions = data.get("positions", [])
            long_count = sum(1 for p in positions if p.get("quantity", 0) > 0)
            short_count = sum(1 for p in positions if p.get("quantity", 0) < 0)
            gross = sum(abs(p.get("quantity", 0)) * float(p.get("current_price", 0.0)) for p in positions)
            net = sum(p.get("quantity", 0) * float(p.get("current_price", 0.0)) for p in positions)
            total_pnl = sum(float(p.get("pnl", 0.0)) for p in positions)
            return ExposureInfo(
                total_positions=len(positions),
                long_positions=long_count,
                short_positions=short_count,
                gross_exposure=_format_inr(gross),
                net_exposure=_format_inr(net),
                unrealized_pnl=_format_pnl(total_pnl),
            )

        from titan.cli.common import get_runtime_engine
        engine = get_runtime_engine()
        broker = engine.broker
        positions_obj = broker.positions()
        long_count = sum(1 for p in positions_obj if p.quantity > 0)
        short_count = sum(1 for p in positions_obj if p.quantity < 0)
        gross = sum(abs(p.quantity) * float(p.current_price or 0) for p in positions_obj)
        net = sum(p.quantity * float(p.current_price or 0) for p in positions_obj)
        total_pnl = sum(float(p.pnl or 0) for p in positions_obj)
        return ExposureInfo(
            total_positions=len(positions_obj),
            long_positions=long_count,
            short_positions=short_count,
            gross_exposure=_format_inr(gross),
            net_exposure=_format_inr(net),
            unrealized_pnl=_format_pnl(total_pnl),
        )
    except Exception:  # noqa: BLE001
        return ExposureInfo()


def _read_live_positions() -> tuple[LivePositionEntry, ...]:
    try:
        data = _get_live_data()
        if data.get("running"):
            return tuple(
                LivePositionEntry(
                    symbol=p.get("symbol", ""),
                    exchange=p.get("exchange", ""),
                    product=p.get("product", ""),
                    quantity=p.get("quantity", 0),
                    buy_qty=p.get("buy_qty", 0),
                    sell_qty=p.get("sell_qty", 0),
                    avg_price=_format_inr(p.get("avg_price", 0.0)),
                    current_price=_format_inr(p.get("current_price", 0.0)),
                    pnl=_format_pnl(p.get("pnl", 0.0)),
                    realised_pnl=_format_pnl(p.get("realised_pnl", 0.0)),
                )
                for p in data.get("positions", [])
            )

        from titan.cli.common import get_runtime_engine
        engine = get_runtime_engine()
        broker = engine.broker
        positions = broker.positions()
        return tuple(
            LivePositionEntry(
                symbol=p.symbol,
                exchange=(
                    p.exchange.value
                    if hasattr(p.exchange, "value")
                    else str(p.exchange)
                ),
                product=(
                    p.product.value if hasattr(p.product, "value") else str(p.product)
                ),
                quantity=p.quantity,
                buy_qty=p.buy_quantity,
                sell_qty=p.sell_quantity,
                avg_price=_format_inr(p.buy_price or 0),
                current_price=_format_inr(p.current_price or 0),
                pnl=_format_pnl(p.pnl or 0),
                realised_pnl=_format_pnl(p.realised_pnl or 0),
            )
            for p in positions
        )
    except Exception:  # noqa: BLE001
        return ()


def _read_live_orders() -> tuple[LiveOrderEntry, ...]:
    try:
        data = _get_live_data()
        if data.get("running"):
            active = []
            for o in data.get("orders", []):
                status_str = o.get("status", "")
                if status_str not in ("pending", "open", "partially_filled"):
                    continue
                active.append(
                    LiveOrderEntry(
                        order_id=o.get("order_id", ""),
                        symbol=o.get("symbol", ""),
                        side=o.get("side", ""),
                        order_type=o.get("type", ""),
                        quantity=o.get("quantity", 0),
                        filled_quantity=o.get("filled_quantity", 0),
                        price=_format_inr(o.get("average_price") or o.get("price") or 0),
                        status=status_str,
                        placed_at="",
                    )
                )
            return tuple(active)

        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        broker = engine.broker
        all_orders = broker.orders()
        active_list: list[LiveOrderEntry] = []
        for o in all_orders:
            status_str = o.status.value if hasattr(o.status, "value") else str(o.status)
            if status_str not in ("pending", "open", "partially_filled"):
                continue
            side_val = o.side.value if hasattr(o.side, "value") else str(o.side)
            ot_val = (
                o.order_type.value
                if hasattr(o.order_type, "value")
                else str(o.order_type)
            )
            price_str = _format_inr(o.average_price or o.price or 0)
            placed_str = ""
            if o.placed_at:
                placed_str = o.placed_at.strftime("%H:%M")
            active_list.append(
                LiveOrderEntry(
                    order_id=o.broker_order_id,
                    symbol=o.symbol,
                    side=side_val,
                    order_type=ot_val,
                    quantity=o.quantity,
                    filled_quantity=o.filled_quantity,
                    price=price_str,
                    status=status_str,
                    placed_at=placed_str,
                )
            )
        return tuple(active_list)
    except Exception:  # noqa: BLE001
        return ()


def _read_recent_executions() -> tuple[ExecutionEntry, ...]:
    try:
        from titan.cli.common import get_runtime_engine

        engine = get_runtime_engine()
        broker = engine.broker
        trades = broker.trades()
        entries: list[ExecutionEntry] = []
        for t in trades[-20:]:
            side_val = t.side.value if hasattr(t.side, "value") else str(t.side)
            time_str = ""
            if t.trade_time:
                time_str = t.trade_time.strftime("%H:%M")
            entries.append(
                ExecutionEntry(
                    trade_id=t.trade_id,
                    order_id=t.broker_order_id,
                    symbol=t.symbol,
                    side=side_val,
                    quantity=t.quantity,
                    price=_format_inr(t.price),
                    time=time_str,
                )
            )
        return tuple(entries)
    except Exception:  # noqa: BLE001
        return ()


# ─── Monitoring & Alerting state builder ─────────────────────────────


def build_monitoring_state() -> MonitoringScreenState:
    """Build MonitoringScreenState by reading monitoring, alerting, and recovery managers.

    All manager access is try/except guarded for resilience.
    """
    from titan.tui.models import MonitoringScreenState

    system_health = _read_monitoring_system_health()
    telemetry = _read_monitoring_telemetry()
    resource_metrics = _read_monitoring_resource_metrics()
    alert_summary = _read_monitoring_alert_summary()
    active_alerts = _read_monitoring_active_alerts()
    alert_history = _read_monitoring_alert_history()
    recovery_status = _read_monitoring_recovery_status()
    monitoring_events = _read_monitoring_events()

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    return MonitoringScreenState(
        system_health=system_health,
        telemetry=telemetry,
        resource_metrics=resource_metrics,
        alert_summary=alert_summary,
        active_alerts=active_alerts,
        alert_history=alert_history,
        recovery_status=recovery_status,
        monitoring_events=monitoring_events,
        last_refresh=now,
    )


def _read_monitoring_system_health() -> SystemHealthInfo:
    from titan.tui.models import SubsystemHealthEntry, SystemHealthInfo

    try:
        from titan.cli.common import get_monitoring_manager

        mon = get_monitoring_manager()
        health = mon.health.evaluate()
        subsystems = tuple(
            SubsystemHealthEntry(
                name=sub.subsystem.value,
                status=sub.status.value,
                message=sub.message,
                latency_ms=f"{sub.latency_ms:.1f}",
                failures=sub.failures,
            )
            for sub in health.subsystems
        )
        return SystemHealthInfo(
            overall_status=health.overall.value,
            healthy_count=health.healthy_count,
            warning_count=health.warning_count,
            critical_count=health.critical_count,
            offline_count=health.offline_count,
            subsystems=subsystems,
        )
    except Exception:  # noqa: BLE001
        return SystemHealthInfo()


def _read_monitoring_telemetry() -> TelemetryInfo:
    from titan.tui.models import TelemetryInfo

    try:
        from titan.cli.common import get_monitoring_manager

        mon = get_monitoring_manager()
        status = mon.dashboard_status()
        return TelemetryInfo(
            total_metrics=len(mon.metrics.metric_names()),
            active_collectors=status.active_collectors,
            failed_collections=status.failed_collections,
            total_collections=status.total_collections,
            uptime=_format_uptime(status.uptime_seconds),
        )
    except Exception:  # noqa: BLE001
        return TelemetryInfo()


def _read_monitoring_resource_metrics() -> ResourceMetricsInfo:
    from titan.tui.models import ResourceMetricEntry, ResourceMetricsInfo

    try:
        from titan.cli.common import get_monitoring_manager

        mon = get_monitoring_manager()
        status = mon.dashboard_status()
        metrics = tuple(
            ResourceMetricEntry(
                name=summary.name,
                value=_format_float(summary.current),
                unit=summary.unit.value,
                trend=summary.trend,
            )
            for summary in status.metric_summaries
        )
        return ResourceMetricsInfo(metrics=metrics)
    except Exception:  # noqa: BLE001
        return ResourceMetricsInfo()


def _read_monitoring_alert_summary() -> AlertSummaryInfo:
    from titan.tui.models import AlertSummaryInfo

    try:
        from titan.cli.common import get_alert_manager

        al = get_alert_manager()
        report = al.generate_report()
        return AlertSummaryInfo(
            total=report.total_alerts,
            active=report.active_alerts,
            critical=report.critical_alerts,
            acknowledged=report.acknowledged_alerts,
            resolved=report.resolved_alerts,
            escalated=report.escalated_alerts,
        )
    except Exception:  # noqa: BLE001
        return AlertSummaryInfo()


def _read_monitoring_active_alerts() -> tuple[AlertEntry, ...]:
    from titan.tui.models import AlertEntry

    try:
        from titan.cli.common import get_alert_manager

        al = get_alert_manager()
        alerts = al.get_active_alerts()
        return tuple(
            AlertEntry(
                alert_id=alert.alert_id,
                level=alert.level.value,
                source=alert.source.value,
                title=alert.title,
                message=alert.message,
                status=alert.status.value,
                timestamp_str=alert.timestamp.strftime("%H:%M:%S"),
            )
            for alert in alerts[-20:]
        )
    except Exception:  # noqa: BLE001
        return ()


def _read_monitoring_alert_history() -> tuple[AlertHistoryEntry, ...]:
    from titan.tui.models import AlertHistoryEntry

    try:
        from titan.cli.common import get_alert_manager

        al = get_alert_manager()
        entries = al.history.all_entries()
        result: list[AlertHistoryEntry] = []
        for entry in entries[-20:]:
            duration = ""
            if entry.alert.acknowledged_at and entry.alert.timestamp:
                delta = (
                    entry.alert.acknowledged_at - entry.alert.timestamp
                ).total_seconds()
                duration = _format_uptime(delta)
            elif entry.alert.resolved_at and entry.alert.timestamp:
                delta = (
                    entry.alert.resolved_at - entry.alert.timestamp
                ).total_seconds()
                duration = _format_uptime(delta)
            result.append(
                AlertHistoryEntry(
                    alert_id=entry.alert.alert_id,
                    level=entry.alert.level.value,
                    source=entry.alert.source.value,
                    title=entry.alert.title,
                    status=entry.alert.status.value,
                    timestamp_str=entry.alert.timestamp.strftime("%H:%M:%S"),
                    duration=duration,
                )
            )
        return tuple(result)
    except Exception:  # noqa: BLE001
        return ()


def _read_monitoring_recovery_status() -> RecoveryStatusInfo:
    from titan.tui.models import RecoveryStatusInfo

    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        report = rm.generate_report()
        history = rm.get_recovery_history()
        last_strategy = ""
        if history:
            last = history[-1]
            last_strategy = (
                last.strategy.value
                if hasattr(last.strategy, "value")
                else str(last.strategy)
            )
        recovered = (
            ", ".join(report.recovered_components[:3])
            if report.recovered_components
            else ""
        )
        return RecoveryStatusInfo(
            status=(
                report.status.value
                if hasattr(report.status, "value")
                else str(report.status)
            ),
            total_attempts=report.total_attempts,
            successful=report.successful_attempts,
            failed=report.failed_attempts,
            last_strategy=last_strategy,
            recovered_components=recovered,
        )
    except Exception:  # noqa: BLE001
        return RecoveryStatusInfo()


def _read_monitoring_events() -> tuple[MonitoringEventEntry, ...]:
    from titan.tui.models import MonitoringEventEntry

    entries: list[MonitoringEventEntry] = []
    try:
        from titan.cli.common import get_monitoring_manager

        mon = get_monitoring_manager()
        report = mon.generate_report()
        for warning in report.warnings:
            entries.append(
                MonitoringEventEntry(
                    level="warning",
                    source="monitoring",
                    message=warning,
                    timestamp_str=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
                )
            )
        for rec in report.recommendations:
            entries.append(
                MonitoringEventEntry(
                    level="info",
                    source="monitoring",
                    message=rec,
                    timestamp_str=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
                )
            )
    except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
        pass
    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        history = rm.get_recovery_history()
        for recovery in history[-10:]:
            entries.append(
                MonitoringEventEntry(
                    level="info",
                    source="recovery",
                    message=(
                        f"Recovery {recovery.status.value}: {recovery.failure_reason}"
                        if recovery.failure_reason
                        else f"Recovery {recovery.status.value}"
                    ),
                    timestamp_str=(
                        recovery.timestamp.strftime("%H:%M:%S")
                        if hasattr(recovery, "timestamp") and recovery.timestamp
                        else ""
                    ),
                )
            )
    except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
        pass
    try:
        from titan.cli.common import get_alert_manager

        al = get_alert_manager()
        al_report = al.generate_report()
        for w in al_report.warnings:
            entries.append(
                MonitoringEventEntry(
                    level="warning",
                    source="alerting",
                    message=w,
                    timestamp_str=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
                )
            )
    except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
        pass
    return tuple(entries[-30:])


# ─── Audit, Logs & Recovery state builder ─────────────────────────


def build_audit_state() -> AuditScreenState:
    """Build AuditScreenState by reading audit, logging, and recovery managers.

    All manager access is try/except guarded for resilience.
    """
    from titan.tui.models import AuditScreenState

    audit_summary = _read_audit_summary()
    recent_audit = _read_recent_audit()
    log_summary = _read_log_summary()
    recent_logs = _read_recent_logs()
    recovery_history = _read_recovery_history_entries()
    circuit_breakers = _read_circuit_breakers()
    checkpoints = _read_checkpoints()
    backup_status = _read_backup_status()

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    return AuditScreenState(
        audit_summary=audit_summary,
        recent_audit=recent_audit,
        log_summary=log_summary,
        recent_logs=recent_logs,
        recovery_history=recovery_history,
        circuit_breakers=circuit_breakers,
        checkpoints=checkpoints,
        backup_status=backup_status,
        last_refresh=now,
    )


def _read_audit_summary() -> AuditSummaryInfo:
    from titan.tui.models import AuditSummaryInfo

    try:
        from titan.cli.common import get_audit_manager

        am = get_audit_manager()
        report = am.generate_report()
        by_source = ", ".join(
            f"{k}:{v}" for k, v in list(report.events_by_source.items())[:5]
        )
        by_severity = ", ".join(
            f"{k}:{v}" for k, v in list(report.events_by_severity.items())[:5]
        )
        first = ""
        if report.first_event_time:
            first = report.first_event_time.strftime("%H:%M:%S")
        last = ""
        if report.last_event_time:
            last = report.last_event_time.strftime("%H:%M:%S")
        return AuditSummaryInfo(
            total_events=report.total_events,
            events_by_source=by_source,
            events_by_severity=by_severity,
            integrity_status=report.integrity_status,
            verification_failures=report.verification_failures,
            first_event_time=first,
            last_event_time=last,
        )
    except Exception:  # noqa: BLE001
        return AuditSummaryInfo()


def _read_recent_audit() -> tuple[AuditEntry, ...]:
    from titan.tui.models import AuditEntry

    try:
        from titan.cli.common import get_audit_manager

        am = get_audit_manager()
        from titan.audit.query import AuditQuery

        query = AuditQuery()
        events = am.search(query)
        entries: list[AuditEntry] = []
        for ev in events[-20:]:
            entries.append(
                AuditEntry(
                    event_id=ev.event_id,
                    sequence=ev.sequence_number,
                    source=(
                        ev.source.value
                        if hasattr(ev.source, "value")
                        else str(ev.source)
                    ),
                    category=(
                        ev.category.value
                        if hasattr(ev.category, "value")
                        else str(ev.category)
                    ),
                    severity=(
                        ev.severity.value
                        if hasattr(ev.severity, "value")
                        else str(ev.severity)
                    ),
                    action=ev.action,
                    result=(
                        ev.result.value
                        if hasattr(ev.result, "value")
                        else str(ev.result)
                    ),
                    timestamp_str=ev.timestamp.strftime("%H:%M:%S"),
                )
            )
        return tuple(entries)
    except Exception:  # noqa: BLE001
        return ()


def _read_log_summary() -> LogSummaryInfo:
    from titan.tui.models import LogSummaryInfo

    try:
        from titan.logging.manager import LoggerManager

        lm = LoggerManager.instance()
        report = lm.generate_report()
        handler_count = len(report.handlers)
        return LogSummaryInfo(
            level=(
                report.level.value
                if hasattr(report.level, "value")
                else str(report.level)
            ),
            handler_count=handler_count,
            component_count=report.component_count,
            dropped_messages=report.dropped_messages,
            warning_count=len(report.warnings),
            error_count=len(report.errors),
        )
    except Exception:  # noqa: BLE001
        return LogSummaryInfo()


def _read_recent_logs() -> tuple[LogEntry, ...]:
    from titan.tui.models import LogEntry

    try:
        from pathlib import Path

        log_file = Path("logs/titan.log")
        if not log_file.exists():
            return ()
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        entries: list[LogEntry] = []
        for line in lines[-20:]:
            if not line.strip():
                continue
            parts = line.strip().split(" ", 4)
            ts = parts[0] if len(parts) > 0 else ""
            level = parts[1] if len(parts) > 1 else ""
            module_comp = parts[2] if len(parts) > 2 else ""
            module, _, component = module_comp.partition("/")
            message = (
                parts[4] if len(parts) > 4 else (parts[3] if len(parts) > 3 else "")
            )
            entries.append(
                LogEntry(
                    timestamp_str=ts,
                    level=level,
                    module=module,
                    component=component or module,
                    message=message[:120],
                )
            )
        return tuple(entries[-20:])
    except Exception:  # noqa: BLE001
        return ()


def _read_recovery_history_entries() -> tuple[RecoveryHistoryEntry, ...]:
    from titan.tui.models import RecoveryHistoryEntry

    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        history = rm.get_recovery_history()
        entries: list[RecoveryHistoryEntry] = []
        for r in history[-20:]:
            entries.append(
                RecoveryHistoryEntry(
                    request_id=r.request_id,
                    component=(
                        r.component.value
                        if hasattr(r.component, "value")
                        else str(r.component)
                    ),
                    strategy=(
                        r.strategy.value
                        if hasattr(r.strategy, "value")
                        else str(r.strategy)
                    ),
                    status=(
                        r.status.value if hasattr(r.status, "value") else str(r.status)
                    ),
                    attempts=r.total_attempts,
                    failure_reason=r.failure_reason,
                    timestamp_str=(
                        r.timestamp.strftime("%H:%M:%S") if r.timestamp else ""
                    ),
                )
            )
        return tuple(entries)
    except Exception:  # noqa: BLE001
        return ()


def _read_circuit_breakers() -> tuple[CircuitBreakerInfo, ...]:
    from titan.tui.models import CircuitBreakerInfo

    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        breakers = rm._circuit_breakers
        result: list[CircuitBreakerInfo] = []
        for name, cb in breakers.items():
            state_val = cb.state.value if hasattr(cb.state, "value") else str(cb.state)
            timeout_s = f"{cb.config.recovery_timeout_seconds:.0f}s"
            result.append(
                CircuitBreakerInfo(
                    name=name,
                    state=state_val,
                    failure_count=cb.failure_count,
                    success_count=cb.success_count,
                    failure_threshold=cb.config.failure_threshold,
                    recovery_timeout=timeout_s,
                )
            )
        return tuple(result)
    except Exception:  # noqa: BLE001
        return ()


def _read_checkpoints() -> tuple[CheckpointInfo, ...]:
    from titan.tui.models import CheckpointInfo

    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        checkpoints = rm.checkpoints.list_all()
        result: list[CheckpointInfo] = []
        for cp in checkpoints[-20:]:
            comp_val = (
                cp.component.value
                if hasattr(cp.component, "value")
                else str(cp.component)
            )
            result.append(
                CheckpointInfo(
                    checkpoint_id=cp.checkpoint_id,
                    component=comp_val,
                    version=cp.version,
                    created_at_str=(
                        cp.created_at.strftime("%H:%M:%S") if cp.created_at else ""
                    ),
                    has_metadata=bool(cp.metadata),
                )
            )
        return tuple(result)
    except Exception:  # noqa: BLE001
        return ()


def _read_backup_status() -> BackupStatusInfo:
    from titan.tui.models import BackupStatusInfo

    try:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        checkpoints = rm.checkpoints.list_all()
        total = len(checkpoints)
        components: set[str] = set()
        last_time = ""
        storage_type = "in_memory"
        storage_path = ""
        for cp in checkpoints:
            comp_val = (
                cp.component.value
                if hasattr(cp.component, "value")
                else str(cp.component)
            )
            components.add(comp_val)
        if checkpoints:
            last = checkpoints[-1]
            if last.created_at:
                last_time = last.created_at.strftime("%H:%M:%S")
        cp_mgr = rm.checkpoints
        if hasattr(cp_mgr, "_storage"):
            storage_path = str(getattr(cp_mgr._storage, "file_path", ""))
            if storage_path:
                storage_type = "jsonl"
        return BackupStatusInfo(
            total_checkpoints=total,
            components_with_checkpoints=", ".join(sorted(components)),
            last_checkpoint_time=last_time,
            storage_type=storage_type,
            storage_path=storage_path,
        )
    except Exception:  # noqa: BLE001
        return BackupStatusInfo()


# ─── Configuration & Deployment state builder ─────────────────────


def build_configuration_state() -> ConfigurationScreenState:
    """Build ConfigurationScreenState by reading configuration and deployment managers."""
    from titan.tui.models import ConfigurationScreenState

    configuration = _read_configuration()
    environment = _read_environment()
    deployment = _read_deployment()
    services = _read_services()
    version = _read_versions()
    backup = _read_backup()
    history = _read_deployment_history()

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    return ConfigurationScreenState(
        configuration=configuration,
        environment=environment,
        deployment=deployment,
        services=services,
        version=version,
        backup=backup,
        history=history,
        last_refresh=now,
    )


def _read_configuration() -> ConfigurationInfo:
    from titan.tui.models import ConfigurationInfo

    try:
        from titan.cli.common import get_config_manager

        cm = get_config_manager()
        report = cm.generate_report()
        config = report.config
        log_level = ""
        pipeline_interval = ""
        if config is not None:
            log_level = config.logging.level
            pipeline_interval = f"{config.runtime.pipeline_interval_seconds}s"
        return ConfigurationInfo(
            profile=report.profile,
            sources=report.sources,
            log_level=log_level,
            pipeline_interval=pipeline_interval,
            validation_status=report.validation_status,
        )
    except Exception:  # noqa: BLE001
        return ConfigurationInfo()


def _read_environment() -> EnvironmentInfo:
    from titan.tui.models import EnvironmentInfo

    try:
        from titan.cli.common import get_deployment_manager

        dm = get_deployment_manager()
        report = dm._env_manager.validate(dm._environment)
        validation_status = "valid"
        if report.errors:
            validation_status = "invalid"
        elif report.warnings:
            validation_status = "warnings"

        return EnvironmentInfo(
            name=(
                dm._environment.value
                if hasattr(dm._environment, "value")
                else str(dm._environment)
            ),
            directories_verified=report.directories_verified,
            secrets_available=report.secrets_available,
            validation_status=validation_status,
        )
    except Exception:  # noqa: BLE001
        return EnvironmentInfo()


def _read_deployment() -> DeploymentInfo:
    from titan.tui.models import DeploymentInfo

    try:
        from titan.cli.common import get_deployment_manager

        dm = get_deployment_manager()
        report = dm.generate_report()
        health = report.health
        start_time = ""
        if report.start_time is not None:
            start_time = report.start_time.strftime("%H:%M:%S")

        status_val = (
            report.status.value
            if hasattr(report.status, "value")
            else str(report.status)
        )
        health_val = (
            health.overall_status.value
            if hasattr(health.overall_status, "value")
            else str(health.overall_status)
        )

        startup_duration = ""
        # Not easily available on report without parsing, use empty or default
        return DeploymentInfo(
            status=status_val,
            uptime=_format_uptime(report.uptime_seconds),
            start_time=start_time,
            health_status=health_val,
            startup_duration=startup_duration,
        )
    except Exception:  # noqa: BLE001
        return DeploymentInfo()


def _read_services() -> tuple[ServiceStatusEntry, ...]:
    from titan.tui.models import ServiceStatusEntry

    try:
        from titan.cli.common import get_deployment_manager

        dm = get_deployment_manager()
        health = dm.health().generate_report()
        return tuple(
            ServiceStatusEntry(
                name=sub.name,
                status=(
                    sub.status.value
                    if hasattr(sub.status, "value")
                    else str(sub.status)
                ),
                latency_ms=f"{sub.latency_ms:.1f}",
                message=sub.message,
            )
            for sub in health.subsystems
        )
    except Exception:  # noqa: BLE001
        return ()


def _read_versions() -> VersionInfo:
    from titan.tui.models import VersionInfo

    try:
        from titan.cli.common import get_deployment_manager

        dm = get_deployment_manager()
        ver = dm.version()
        return VersionInfo(
            version=ver.version,
            build_number=ver.build_number,
            git_commit=ver.git_commit,
            git_branch=ver.git_branch,
            python_version=ver.python_version,
        )
    except Exception:  # noqa: BLE001
        return VersionInfo()


def _read_backup() -> BackupInfo:
    from titan.tui.models import BackupInfo

    # The deployment manager does not maintain backup history natively.
    return BackupInfo()


def _read_deployment_history() -> tuple[DeploymentHistoryEntry, ...]:
    # The deployment manager does not maintain history of deployments natively.
    return ()


# ─── MARKET INTELLIGENCE STATE BUILDERS ──────────────────────────────────────


def build_market_state() -> MarketScreenState:
    """Build MarketScreenState by querying runtime engine and cached intelligence."""
    from datetime import datetime

    from titan.tui.models import MarketScreenState

    return MarketScreenState(
        market_status=_read_market_status(),
        regime=_read_regime(),
        volatility=_read_volatility(),
        liquidity=_read_liquidity(),
        option_chain=_read_option_chain(),
        open_interest=_read_open_interest(),
        greeks=_read_greeks(),
        evidence=_read_evidence(),
        events=_read_market_events(),
        last_refresh=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
    )


def _read_market_status() -> MarketStatusInfo:
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import MarketStatusInfo

    try:
        engine = get_runtime_engine()
        # Fallback values if the actual report generation fails or properties are missing
        report = engine.generate_report()
        return MarketStatusInfo(
            runtime_status=(
                report.runtime_status.name
                if hasattr(report.runtime_status, "name")
                else str(report.runtime_status)
            ),
            broker_status=(
                report.broker.connection.name
                if hasattr(report.broker.connection, "name")
                else str(report.broker.connection)
            ),
            active_subscriptions=report.market.active_subscriptions,
            last_quote_time=(
                str(report.market.last_quote_time)
                if report.market.last_quote_time
                else ""
            ),
        )
    except Exception:  # noqa: BLE001
        return MarketStatusInfo()


def _read_regime() -> RegimeInfo:
    from titan.tui.models import RegimeInfo

    # The intelligence engines do not currently expose a persistent cache property
    # on the RuntimeEngine. As per architecture rules, we return safe defaults.
    return RegimeInfo()


def _read_volatility() -> VolatilityInfo:
    from titan.tui.models import VolatilityInfo

    return VolatilityInfo()


def _read_liquidity() -> LiquidityInfo:
    from titan.tui.models import LiquidityInfo

    return LiquidityInfo()


def _read_option_chain() -> OptionChainSummaryInfo:
    from titan.tui.models import OptionChainSummaryInfo

    return OptionChainSummaryInfo()


def _read_open_interest() -> OpenInterestSummaryInfo:
    from titan.tui.models import OpenInterestSummaryInfo

    return OpenInterestSummaryInfo()


def _read_greeks() -> GreeksSummaryInfo:
    from titan.tui.models import GreeksSummaryInfo

    return GreeksSummaryInfo()


def _read_evidence() -> EvidenceSummaryInfo:
    from titan.tui.models import EvidenceSummaryInfo

    return EvidenceSummaryInfo()


def _read_market_events() -> tuple[MarketEventEntry, ...]:
    # Persistent market event history is not natively stored.
    return ()


# ─── DECISION JOURNAL STATE BUILDERS ─────────────────────────────────────────


def build_decision_state() -> DecisionScreenState:
    from datetime import datetime

    from titan.tui.models import DecisionScreenState

    return DecisionScreenState(
        summary=_read_decision_summary(),
        evidence=_read_decision_evidence(),
        risk=_read_decision_risk(),
        qualification=_read_decision_qualification(),
        reasons=_read_decision_reasons(),
        timeline=_read_decision_timeline(),
        history=_read_decision_history(),
        last_refresh=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
    )


def _read_decision_summary() -> DecisionSummaryInfo:
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import DecisionSummaryInfo

    try:
        engine = get_runtime_engine()
        entries = engine.decision_journal.repository.get_latest(1)
        if not entries:
            return DecisionSummaryInfo()
        entry = entries[0]
        return DecisionSummaryInfo(
            decision_id=entry.id,
            symbol=entry.symbol,
            decision=entry.decision,
            trade_direction=entry.trade_direction,
            instrument_type=entry.instrument_type,
            confidence=entry.confidence,
            trade_score=entry.trade_score,
            institutional_grade=entry.institutional_grade,
            timestamp_str=entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception:  # noqa: BLE001
        return DecisionSummaryInfo()


def _read_decision_evidence() -> DecisionEvidenceInfo:
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import DecisionEvidenceInfo

    try:
        engine = get_runtime_engine()
        entries = engine.decision_journal.repository.get_latest(1)
        if not entries or not entries[0].evidence_snapshot:
            return DecisionEvidenceInfo()
        ev = entries[0].evidence_snapshot
        return DecisionEvidenceInfo(
            source=ev.source,
            category=ev.category,
            signal=ev.signal,
            score=ev.score,
            confidence=ev.confidence,
            weight=ev.weight,
            reasons=ev.reasons,
        )
    except Exception:  # noqa: BLE001
        return DecisionEvidenceInfo()


def _read_decision_risk() -> DecisionRiskInfo:
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import DecisionRiskInfo

    try:
        engine = get_runtime_engine()
        entries = engine.decision_journal.repository.get_latest(1)
        if not entries:
            return DecisionRiskInfo()
        return DecisionRiskInfo(
            risk_summary=entries[0].risk_summary or "No risk data available."
        )
    except Exception:  # noqa: BLE001
        return DecisionRiskInfo()


def _read_decision_qualification() -> DecisionQualificationInfo:
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import DecisionQualificationInfo

    try:
        engine = get_runtime_engine()
        entries = engine.decision_journal.repository.get_latest(1)
        if not entries:
            return DecisionQualificationInfo()
        return DecisionQualificationInfo(
            explanation_summary=entries[0].explanation_summary
            or "No explanation available."
        )
    except Exception:  # noqa: BLE001
        return DecisionQualificationInfo()


def _read_decision_reasons() -> tuple[DecisionReasonEntry, ...]:
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import DecisionReasonEntry

    try:
        engine = get_runtime_engine()
        entries = engine.decision_journal.repository.get_latest(1)
        if not entries:
            return ()
        return tuple(
            DecisionReasonEntry(
                reason_type=r.reason_type,
                description=r.description,
                severity=r.severity,
            )
            for r in entries[0].reasons
        )
    except Exception:  # noqa: BLE001
        return ()


def _read_decision_timeline() -> tuple[DecisionTimelineEntry, ...]:
    # Timeline is a placeholder unless we explicitly track pipeline stages per decision.
    return ()


def _read_decision_history() -> tuple[DecisionJournalEntry, ...]:
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import DecisionJournalEntry

    try:
        engine = get_runtime_engine()
        entries = engine.decision_journal.repository.get_latest(50)
        return tuple(
            DecisionJournalEntry(
                decision_id=e.id,
                symbol=e.symbol,
                decision=e.decision,
                timestamp_str=e.timestamp.strftime("%H:%M:%S"),
            )
            for e in entries
        )
    except Exception:  # noqa: BLE001
        return ()


# ─── DECISION REPLAY STATE BUILDERS ──────────────────────────────────────────


def build_trade_journal_state() -> TradeJournalScreenState:
    """Read TradeJournal data to build TradeJournalScreenState."""
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import (
        TradeHistoryEntry,
        TradeJournalScreenState,
        TradeJournalSummaryInfo,
    )

    try:
        engine = get_runtime_engine()
        journal = engine.trade_journal

        # Calculate summary using analytics engine
        from titan.trading.performance import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer()
        entries = journal.repository.list(page=1, page_size=1000)
        perf = analyzer.analyze(entries)

        summary = TradeJournalSummaryInfo(
            today_pnl=f"INR {perf.overall.net_pnl:.2f}",
            open_risk="INR 0",  # TBD
            exposure="INR 0",  # TBD
            win_percent=f"{perf.overall.win_rate * 100:.1f}%",
            current_drawdown="0.0%",  # TBD: Calculate real-time drawdown
            largest_winner=f"INR {perf.overall.largest_winner:.2f}",
            largest_loser=f"INR {perf.overall.largest_loser:.2f}",
        )

        history = tuple(
            TradeHistoryEntry(
                trade_id=e.trade_id,
                symbol=e.symbol,
                direction=e.direction,
                quantity=e.quantity,
                entry_price=f"INR {e.entry_price:.2f}",
                exit_price=f"INR {e.exit_price:.2f}",
                net_pnl=f"INR {e.net_pnl:.2f}",
                status=e.execution_status.value.upper(),
                open_time=e.open_time.strftime("%H:%M:%S") if e.open_time else "",
            )
            for e in entries
        )

        return TradeJournalScreenState(
            summary=summary,
            history=history,
            last_refresh=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
        )
    except Exception:  # noqa: BLE001
        return TradeJournalScreenState()


def build_replay_state(entry_id: str | None = None) -> ReplayScreenState:
    from datetime import datetime

    from titan.cli.common import get_runtime_engine
    from titan.tui.models import (
        ReplayEvidenceInfo,
        ReplayMetadataInfo,
        ReplayQualificationInfo,
        ReplayReasonEntry,
        ReplayRiskInfo,
        ReplayScreenState,
        ReplaySummaryInfo,
        ReplayTimelineEntry,
    )

    engine = get_runtime_engine()

    if entry_id:
        result = engine.decision_replay.replay(entry_id)
    else:
        result = engine.decision_replay.latest()

    all_entries = engine.decision_journal.repository.list(
        1, 999999
    )  # for count/index logic
    total = len(all_entries)

    if not result:
        return ReplayScreenState(
            metadata=ReplayMetadataInfo(total_decisions=total),
            last_refresh=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
        )

    entry = result.snapshot.entry

    # find index
    current_idx = 0
    # list returns newest first
    for i, e in enumerate(all_entries):
        if e.id == entry.id:
            current_idx = total - i  # 1-based chronological index
            break

    prev_entry = engine.decision_journal.repository.previous(entry.id)
    next_entry = engine.decision_journal.repository.next(entry.id)
    has_previous = prev_entry is not None
    has_next = next_entry is not None

    summary = ReplaySummaryInfo(
        decision_id=entry.id,
        symbol=entry.symbol,
        decision=entry.decision,
        trade_direction=entry.trade_direction,
        instrument_type=entry.instrument_type,
        confidence=entry.confidence,
        trade_score=entry.trade_score,
        institutional_grade=entry.institutional_grade,
        timestamp_str=entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    )

    evidence_info = ReplayEvidenceInfo()
    if entry.evidence_snapshot:
        evidence_info = ReplayEvidenceInfo(
            source=entry.evidence_snapshot.source,
            category=entry.evidence_snapshot.category,
            signal=entry.evidence_snapshot.signal,
            score=entry.evidence_snapshot.score,
            confidence=entry.evidence_snapshot.confidence,
            weight=entry.evidence_snapshot.weight,
            reasons=entry.evidence_snapshot.reasons,
        )

    risk_info = ReplayRiskInfo(
        risk_summary=entry.risk_summary or "No risk data available."
    )
    qual_info = ReplayQualificationInfo(
        explanation_summary=entry.explanation_summary or "No explanation available."
    )

    reasons = tuple(
        ReplayReasonEntry(
            reason_type=r.reason_type, description=r.description, severity=r.severity
        )
        for r in entry.reasons
    )

    timeline = tuple(
        ReplayTimelineEntry(
            step=ev,
            status="Completed",
            timestamp_str=entry.timestamp.strftime("%H:%M:%S"),
        )
        for ev in result.timeline.events
    )

    metadata = ReplayMetadataInfo(
        has_previous=has_previous,
        has_next=has_next,
        previous_id=prev_entry.id if prev_entry else None,
        next_id=next_entry.id if next_entry else None,
        current_index=current_idx,
        total_decisions=total,
        filter_active=False,
    )

    return ReplayScreenState(
        summary=summary,
        evidence=evidence_info,
        risk=risk_info,
        qualification=qual_info,
        reasons=reasons,
        timeline=timeline,
        metadata=metadata,
        last_refresh=datetime.now().strftime("%H:%M:%S"),  # noqa: DTZ005 - local time for display
    )


# ─── Strategy Evaluation state builder ──────────────────────────────


def build_strategy_eval_state() -> StrategyEvalScreenState:
    """Build StrategyEvalScreenState by reading the historical journal (read-only)."""
    from datetime import datetime

    from titan.backtesting.evaluation import StrategyEvaluator
    from titan.cli.common import get_runtime_engine
    from titan.tui.models import (
        RegimePerformanceEntry,
        StrategyEvalScreenState,
        StrategyScorecardInfo,
    )

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    try:
        engine = get_runtime_engine()
        entries = engine.trade_journal.repository.list(page=1, page_size=100000)

        evaluator = StrategyEvaluator()
        report = evaluator.evaluate_trades(entries)

        scorecards = []
        for strat in report.strategies:
            regimes = tuple(
                RegimePerformanceEntry(
                    regime=r.regime,
                    trades=r.total_trades,
                    win_rate=f"{r.win_rate * 100:.1f}%",
                    profit_factor=f"{r.profit_factor:.2f}",
                    net_pnl=f"INR {r.net_pnl:,.2f}",
                )
                for r in strat.regime_breakdown.values()
            )

            scorecards.append(
                StrategyScorecardInfo(
                    strategy_name=strat.strategy_name,
                    total_trades=strat.total_trades,
                    win_rate=f"{strat.win_rate * 100:.1f}%",
                    profit_factor=f"{strat.profit_factor:.2f}",
                    expectancy=f"{strat.expectancy:.2f}R",
                    net_pnl=f"INR {strat.net_pnl:,.2f}",
                    max_drawdown=f"INR {strat.max_drawdown:,.2f}",
                    regimes=regimes,
                )
            )

        return StrategyEvalScreenState(
            best_strategy=report.overall_best_strategy,
            scorecards=tuple(scorecards),
            last_refresh=now,
        )
    except Exception:  # noqa: BLE001
        return StrategyEvalScreenState(last_refresh=now)


# ─── AI Assistant State Builder ─────────────────────────────────────


def build_ai_state(provider_name: str = "mock") -> AIScreenState:
    """Build AIScreenState by delegating to the AIAssistantEngine (read-only)."""
    from datetime import datetime

    from titan.ai.engine import AIAssistantEngine
    from titan.ai.providers.gemini import GeminiAIProvider, MockAIProvider
    from titan.backtesting.evaluation import StrategyEvaluator
    from titan.cli.common import get_runtime_engine
    from titan.portfolio.analytics import PortfolioAnalytics
    from titan.portfolio.models import ExistingPortfolio, OpenPosition
    from titan.tui.models import AIExplanationInfo, AIScreenState

    now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display

    provider = (
        MockAIProvider() if provider_name.lower() == "mock" else GeminiAIProvider()
    )
    ai_engine = AIAssistantEngine(provider=provider)

    try:
        engine = get_runtime_engine()
        broker = getattr(engine, "broker", None)

        if broker and hasattr(broker, "positions"):
            funds = broker.funds()
            positions = broker.positions()
            open_pos = tuple(
                OpenPosition(
                    symbol=p.symbol,
                    instrument_type=getattr(p, "product", "EQUITY"),
                    direction="long" if p.quantity > 0 else "short",
                    quantity=p.quantity,
                    entry_price=float(p.average_price or 0.0),
                    current_price=float(p.current_price or 0.0),
                    market_value=float(p.quantity * (p.current_price or 0.0)),
                    pnl=float(p.pnl or 0.0),
                )
                for p in positions
            )
            portfolio = ExistingPortfolio(
                positions=open_pos,
                total_capital=float(funds.available_cash + funds.used_margin),
                cash_reserve=float(funds.available_cash),
            )
        else:
            portfolio = ExistingPortfolio(total_capital=100000.0)

        snapshot = PortfolioAnalytics().generate_snapshot(portfolio)
        port_resp = ai_engine.explain_portfolio(snapshot)

        port_info = AIExplanationInfo(
            title="Portfolio Synthesis",
            provider=port_resp.provider_name,
            model=port_resp.model_name,
            content=port_resp.content,
            timestamp_str=now,
        )

        entries = engine.trade_journal.repository.list(page=1, page_size=10000)
        strat_report = StrategyEvaluator().evaluate_trades(entries)
        strat_resp = ai_engine.explain_strategy_evaluation(strat_report)

        strat_info = AIExplanationInfo(
            title="Strategy Evaluation Synthesis",
            provider=strat_resp.provider_name,
            model=strat_resp.model_name,
            content=strat_resp.content,
            timestamp_str=now,
        )

        return AIScreenState(
            portfolio_explanation=port_info,
            strategy_explanation=strat_info,
            last_refresh=now,
        )
    except Exception:  # noqa: BLE001
        return AIScreenState(last_refresh=now)

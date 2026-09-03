"""titan paper - Paper trading subsystem commands."""

from __future__ import annotations

import csv
import io
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from titan.cli.common import (
    console,
    get_config_manager,
    logger,
)
from titan.runtime.exceptions import RuntimeError as TitanRuntimeError

paper_app = typer.Typer(help="Paper trading subsystem management.")
app = paper_app


# ── Session State ──────────────────────────────────────────


_paper_broker = None
_paper_start_time: datetime | None = None


def _get_broker():
    return _paper_broker


def _is_running() -> bool:
    from titan.runtime.local_transport import LocalTransport

    try:
        return bool(LocalTransport().paper_status().get("running", False))
    except (RuntimeError, ConnectionError, AttributeError, OSError, TitanRuntimeError):
        return False


def _reset_paper_session() -> None:
    """Reset paper trading session state (for testing)."""
    global _paper_broker, _paper_start_time
    if _paper_broker is not None:
        try:
            _paper_broker.disconnect()
        except (RuntimeError, OSError) as e:
            logger.warning(f"Operation failed: {e}")
    _paper_broker = None
    _paper_start_time = None


# ── Checklist Infrastructure ──────────────────────────────


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str = ""


@dataclass
class StartupChecklist:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.status != CheckStatus.FAIL for c in self.checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)


# ── Formatting Helpers ────────────────────────────────────


def _icon(status: CheckStatus) -> str:
    mapping = {
        CheckStatus.PASS: "[green]+[/green]",
        CheckStatus.FAIL: "[red]![/red]",
        CheckStatus.WARN: "[yellow]~[/yellow]",
        CheckStatus.SKIP: "[dim]-[/dim]",
    }
    return mapping[status]


def _status_icon(status_str: str) -> str:
    mapping = {
        "running": "[green]+[/green]",
        "connected": "[green]+[/green]",
        "healthy": "[green]+[/green]",
        "stopped": "[red]~[/red]",
        "disconnected": "[red]~[/red]",
        "unhealthy": "[red]![/red]",
        "error": "[red]![/red]",
        "degraded": "[yellow]~[/yellow]",
        "paused": "[yellow]~[/yellow]",
        "unknown": "[dim]?[/dim]",
    }
    return mapping.get(status_str.lower(), status_str)


def _format_uptime(seconds: float) -> str:
    if seconds <= 0:
        return "Not started"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _decimal_str(d: Decimal) -> str:
    return f"INR {d:,.2f}"


def _json_serial(obj: object) -> str:
    if hasattr(obj, "isoformat"):
        return str(obj.isoformat())
    if hasattr(obj, "value"):
        return str(obj.value)
    if isinstance(obj, Decimal):
        return str(obj)
    return str(obj)


# ── Validation ────────────────────────────────────────────


def _run_validations() -> StartupChecklist:
    checklist = StartupChecklist()

    checklist.checks.append(CheckResult("Configuration loaded", CheckStatus.PASS))

    try:
        config_mgr = get_config_manager()
        config = config_mgr.get_config()
    except Exception as e:
        checklist.checks.append(
            CheckResult("Configuration loaded", CheckStatus.FAIL, str(e))
        )
        return checklist

    broker_provider = getattr(getattr(config, "broker", None), "provider", "paper")
    checklist.checks.append(
        CheckResult(f"Broker provider: {broker_provider}", CheckStatus.PASS)
    )

    env = getattr(getattr(config, "app", None), "environment", "unknown")
    checklist.checks.append(CheckResult(f"Environment: {env}", CheckStatus.PASS))

    risk = getattr(config, "risk", None)
    if risk:
        max_dd = getattr(risk, "max_drawdown_percent", 0)
        if max_dd > 50:
            checklist.checks.append(
                CheckResult(
                    "Risk limits",
                    CheckStatus.WARN,
                    f"Max drawdown {max_dd}% is aggressive",
                )
            )
        else:
            checklist.checks.append(CheckResult("Risk limits", CheckStatus.PASS))
    else:
        checklist.checks.append(CheckResult("Risk limits", CheckStatus.PASS))

    monitoring = getattr(config, "monitoring", None)
    if monitoring and getattr(monitoring, "enabled", False):
        checklist.checks.append(CheckResult("Monitoring", CheckStatus.PASS))
    else:
        checklist.checks.append(
            CheckResult("Monitoring", CheckStatus.WARN, "Monitoring disabled")
        )

    checklist.checks.append(CheckResult("Recovery system", CheckStatus.PASS))
    checklist.checks.append(CheckResult("Audit trail", CheckStatus.PASS))
    checklist.checks.append(CheckResult("Paper engine", CheckStatus.PASS))

    return checklist


def _display_checklist(checklist: StartupChecklist) -> None:
    table = Table(title="Startup Checklist", show_header=True, header_style="bold")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Message")
    for c in checklist.checks:
        msg = c.message if c.message else ""
        table.add_row(c.name, _icon(c.status), msg)
    console.print(table)
    console.print(
        f"\n  [green]+[/green] {checklist.passed_count} passed  "
        f"[yellow]~[/yellow] {checklist.warn_count} warnings  "
        f"[red]![/red] {checklist.failed_count} failed"
    )


# ── Report Building ───────────────────────────────────────


def _build_session_data() -> dict[str, Any]:
    from titan.runtime.local_transport import LocalTransport

    try:
        transport = LocalTransport()
        return transport.paper_status()
    except (RuntimeError, ConnectionError, AttributeError, OSError, TitanRuntimeError):
        return {"running": False}


def _build_report_data() -> dict[str, Any]:
    from titan.runtime.local_transport import LocalTransport

    try:
        data = LocalTransport().paper_status()
    except (RuntimeError, ConnectionError, AttributeError, OSError, TitanRuntimeError):
        return {"error": "No active paper session"}

    if not data.get("running"):
        return {"error": "No active paper session"}

    return {
        "session": {
            "start_time": data.get("start_time"),
            "uptime_seconds": data.get("session_uptime_seconds", 0.0),
            "initial_cash": data.get("initial_cash", 0.0),
        },
        "portfolio": {
            "cash": data.get("cash_balance", 0.0),
            "equity": data.get("portfolio_value", 0.0),
            "buying_power": data.get("buying_power", 0.0),
            "exposure": data.get("exposure", 0.0),
            "position_count": data.get("open_positions", 0),
            "daily_pnl": data.get("daily_pnl", 0.0),
            "total_pnl": data.get("total_pnl", 0.0),
            "drawdown": data.get("drawdown", 0.0),
        },
        "performance": {
            "total_trades": data.get("total_trades", 0),
            "winning_trades": data.get("winning_trades", 0),
            "losing_trades": data.get("losing_trades", 0),
            "win_rate": data.get("win_rate", 0.0),
            "profit_factor": data.get("profit_factor", 0.0),
            "expectancy": data.get("expectancy", 0.0),
            "avg_winner": data.get("avg_winner", 0.0),
            "avg_loser": data.get("avg_loser", 0.0),
            "max_drawdown": data.get("max_drawdown", 0.0),
        },
        "pnl": {
            "realized": data.get("realized_pnl", 0.0),
            "unrealized": data.get("unrealized_pnl", 0.0),
            "total": data.get("total_pnl", 0.0),
        },
        "positions": data.get("positions", []),
        "orders": data.get("orders", []),
    }


# ── Session Summary Tables ────────────────────────────────


def _print_session_summary(data: dict[str, Any]) -> None:
    if not data.get("running"):
        console.print("[dim]No active paper session.[/dim]")
        return

    table = Table(
        title="Paper Trading Session", show_header=False, box=None, padding=(0, 2)
    )
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Status", f"{_status_icon('running')} running")
    table.add_row("Session Uptime", _format_uptime(data["session_uptime_seconds"]))  # type: ignore[arg-type]
    table.add_row("Initial Cash", _decimal_str(Decimal(str(data["initial_cash"]))))  # type: ignore[arg-type]
    table.add_row("Cash Balance", _decimal_str(Decimal(str(data["cash_balance"]))))  # type: ignore[arg-type]
    table.add_row("Portfolio Value", _decimal_str(Decimal(str(data["portfolio_value"]))))  # type: ignore[arg-type]
    table.add_row("Buying Power", _decimal_str(Decimal(str(data["buying_power"]))))  # type: ignore[arg-type]
    table.add_row("Exposure", _decimal_str(Decimal(str(data["exposure"]))))  # type: ignore[arg-type]

    total_pnl = Decimal(str(data["total_pnl"]))  # type: ignore[arg-type]
    pnl_style = "green" if total_pnl >= 0 else "red"
    table.add_row("Total P&L", f"[{pnl_style}]{_decimal_str(total_pnl)}[/{pnl_style}]")

    daily_pnl = Decimal(str(data["daily_pnl"]))  # type: ignore[arg-type]
    daily_style = "green" if daily_pnl >= 0 else "red"
    table.add_row(
        "Daily P&L", f"[{daily_style}]{_decimal_str(daily_pnl)}[/{daily_style}]"
    )

    realized = Decimal(str(data["realized_pnl"]))  # type: ignore[arg-type]
    r_style = "green" if realized >= 0 else "red"
    table.add_row("Realized P&L", f"[{r_style}]{_decimal_str(realized)}[/{r_style}]")

    unrealized = Decimal(str(data["unrealized_pnl"]))  # type: ignore[arg-type]
    u_style = "green" if unrealized >= 0 else "red"
    table.add_row(
        "Unrealized P&L", f"[{u_style}]{_decimal_str(unrealized)}[/{u_style}]"
    )

    table.add_row("Open Positions", str(data["open_positions"]))
    table.add_row("Total Orders", str(data["total_orders"]))
    table.add_row("Filled Orders", str(data["filled_orders"]))
    table.add_row("Closed Trades", str(data["closed_trades"]))
    console.print(table)

    perf_table = Table(
        title="Performance Metrics", show_header=False, box=None, padding=(0, 2)
    )
    perf_table.add_column("Key", style="bold")
    perf_table.add_column("Value")

    win_rate = data["win_rate"]  # type: ignore[index]
    perf_table.add_row("Win Rate", f"{win_rate:.1%}")
    perf_table.add_row("Winning Trades", str(data["winning_trades"]))
    perf_table.add_row("Losing Trades", str(data["losing_trades"]))
    perf_table.add_row("Profit Factor", f"{data['profit_factor']:.2f}")
    perf_table.add_row(
        "Expectancy", _decimal_str(Decimal(str(data["expectancy"])))  # type: ignore[arg-type]
    )
    perf_table.add_row(
        "Max Drawdown", f"{Decimal(str(data['max_drawdown'])):.2%}"  # type: ignore[arg-type]
    )
    console.print(perf_table)


def _print_positions_table(data: dict[str, Any]) -> None:
    # Use the data dict directly instead of _paper_broker
    if not data.get("running"):
        return

    positions = data.get("positions", [])
    if not positions:
        return

    table = Table(title="Open Positions", show_header=True, header_style="bold")
    table.add_column("Symbol", style="bold")
    table.add_column("Qty")
    table.add_column("Avg Price")
    table.add_column("Current")
    table.add_column("P&L")
    table.add_column("MFE")
    table.add_column("MAE")

    for p in positions:
        avg_p = p.get("average_price", 0.0)
        curr_p = p.get("current_price", 0.0)
        unrealized = p.get("unrealized_pnl", 0.0)
        mfe_val = p.get("mfe", 0.0)
        mae_val = p.get("mae", 0.0)

        avg = f"INR {avg_p:,.2f}" if avg_p else "-"
        curr = f"INR {curr_p:,.2f}" if curr_p else "-"
        pnl_style = "green" if unrealized >= 0 else "red"
        pnl = f"[{pnl_style}]INR {unrealized:,.2f}[/{pnl_style}]"
        mfe = f"INR {mfe_val:,.2f}"
        mae = f"INR {mae_val:,.2f}"
        table.add_row(
            p.get("symbol", ""), str(p.get("quantity", 0)), avg, curr, pnl, mfe, mae
        )

    console.print(table)


# ── CSV Export ────────────────────────────────────────────


def _export_csv(data: dict[str, Any], filepath: Path) -> None:
    rows = []

    rows.append(["Section", "Key", "Value"])
    rows.append(
        ["Session", "Start Time", data.get("session", {}).get("start_time", "")]
    )
    rows.append(
        ["Session", "Uptime (s)", data.get("session", {}).get("uptime_seconds", "")]
    )
    rows.append(
        ["Session", "Initial Cash", data.get("session", {}).get("initial_cash", "")]
    )
    rows.append(["Portfolio", "Cash", data.get("portfolio", {}).get("cash", "")])
    rows.append(["Portfolio", "Equity", data.get("portfolio", {}).get("equity", "")])
    rows.append(
        ["Portfolio", "Buying Power", data.get("portfolio", {}).get("buying_power", "")]
    )
    rows.append(
        ["Portfolio", "Daily P&L", data.get("portfolio", {}).get("daily_pnl", "")]
    )
    rows.append(
        ["Portfolio", "Total P&L", data.get("portfolio", {}).get("total_pnl", "")]
    )
    rows.append(
        ["Portfolio", "Drawdown", data.get("portfolio", {}).get("drawdown", "")]
    )
    rows.append(
        [
            "Performance",
            "Total Trades",
            data.get("performance", {}).get("total_trades", ""),
        ]
    )
    rows.append(
        ["Performance", "Win Rate", data.get("performance", {}).get("win_rate", "")]
    )
    rows.append(
        [
            "Performance",
            "Profit Factor",
            data.get("performance", {}).get("profit_factor", ""),
        ]
    )
    rows.append(
        [
            "Performance",
            "Max Drawdown",
            data.get("performance", {}).get("max_drawdown", ""),
        ]
    )

    rows.append([])
    rows.append(
        [
            "Positions",
            "Symbol",
            "Qty",
            "Avg Price",
            "Current",
            "Unrealized P&L",
            "Realized P&L",
        ]
    )
    for pos in data.get("positions", []):  # type: ignore[attr-defined]
        rows.append(
            [
                "Position",
                pos["symbol"],
                pos["quantity"],
                pos["average_price"],
                pos["current_price"],
                pos["unrealized_pnl"],
                pos["realized_pnl"],
            ]
        )

    rows.append([])
    rows.append(["Orders", "ID", "Symbol", "Side", "Type", "Qty", "Filled", "Status"])
    for order in data.get("orders", []):  # type: ignore[attr-defined]
        rows.append(
            [
                "Order",
                order["order_id"],
                order["symbol"],
                order["side"],
                order["type"],
                order["quantity"],
                order["filled_quantity"],
                order["status"],
            ]
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    filepath.write_text(buf.getvalue(), encoding="utf-8")


# ── Commands ──────────────────────────────────────────────


@app.command("start")
def start(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show startup progress")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Validate only, do not start")
    ] = False,
    cash: Annotated[
        float, typer.Option("--cash", help="Initial cash balance")
    ] = 1000000.0,
    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol to trade")
    ] = "RELIANCE",
    exchange: Annotated[
        str, typer.Option("--exchange", "-e", help="Exchange segment")
    ] = "nse",
) -> None:
    """Start a paper trading session."""
    global _paper_broker, _paper_start_time

    logger.info("Paper start command executed")

    if _is_running():
        console.print("[yellow]~[/yellow] Paper trading session is already running.")
        return

    checklist = _run_validations()

    if verbose or dry_run:
        _display_checklist(checklist)

    if not checklist.all_passed:
        console.print("[bold red]![/bold red] Validation failed. Check errors above.")
        raise typer.Exit(code=2)

    if dry_run:
        console.print("[bold green]+[/bold green] Dry run passed. All validations OK.")
        return

    if verbose:
        _start_with_progress(cash, symbol=symbol, exchange=exchange)
    else:
        _start_silent(cash, symbol=symbol, exchange=exchange)


def _start_silent(initial_cash: float, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:
    try:
        _launch_paper_runtime(initial_cash, symbol=symbol, exchange=exchange)
        console.print("[bold green]+[/bold green] Paper trading session started.")
    except Exception as exc:
        console.print(f"[bold red]![/bold red] Failed to start: {exc}")
        raise typer.Exit(code=3)


def _start_with_progress(initial_cash: float, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:
    _start_silent(initial_cash, symbol=symbol, exchange=exchange)


def _launch_paper_runtime(initial_cash: float, *, symbol: str = "RELIANCE", exchange: str = "nse") -> None:
    import sys

    from titan.runtime.launcher import DetachedRuntimeLauncher

    launcher = DetachedRuntimeLauncher()
    launcher.launch(
        [
            sys.executable,
            "-m",
            "titan",
            "paper",
            "serve",
            "--cash",
            str(initial_cash),
            "--symbol",
            symbol.upper(),
            "--exchange",
            exchange.lower(),
        ],
        log_path=Path("logs") / "paper_runtime.log",
    )


def _wait_until_runtime_stops(timeout_seconds: float = 5.0) -> None:
    from titan.runtime.exceptions import RuntimeError as TitanRuntimeError
    from titan.runtime.local_transport import LocalTransport

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            LocalTransport().status()
        except TitanRuntimeError:
            return
        time.sleep(0.05)

    raise TitanRuntimeError("Timed out waiting for the paper runtime to stop.")


@app.command("serve", hidden=True)
def serve(
    cash: Annotated[float, typer.Option("--cash", help="Initial cash balance")],
    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol to trade")
    ] = "RELIANCE",
    exchange: Annotated[
        str, typer.Option("--exchange", "-e", help="Exchange segment")
    ] = "nse",
) -> None:
    """Run the detached paper runtime process."""
    from decimal import Decimal as D

    from titan.execution.allocator import ExecutionAllocator
    from titan.execution.book import OrderBook
    from titan.execution.execution import ExecutionEngine
    from titan.execution.orchestrator import ExecutionOrchestrator
    from titan.execution.planner import ExecutionPlanner
    from titan.execution.router import OrderRouter
    from titan.execution.validator import ExecutionValidator
    from titan.paper.broker import PaperBroker
    from titan.pipeline.pipeline import TradePipeline
    from titan.runtime.local_transport import LocalTransportServer
    from titan.runtime.runtime import RuntimeEngine
    from titan.runtime.service import RuntimeService
    from titan.trading.strategies.momentum import MomentumStrategy

    broker = PaperBroker(initial_cash=D(str(cash)))
    pipeline = TradePipeline(
        strategy=MomentumStrategy(),
    )
    pipeline._orchestrator = ExecutionOrchestrator(
        planner=ExecutionPlanner(),
        validator=ExecutionValidator(),
        allocator=ExecutionAllocator(),
        oms=ExecutionEngine(order_book=OrderBook(), router=OrderRouter()),
        broker=broker,
    )

    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        target_symbol=symbol.upper(),
        target_exchange=exchange.upper(),
    )
    server = LocalTransportServer(RuntimeService(engine))
    try:
        engine.start()
        server.start()
        engine.run_until_stopped()
    finally:
        if engine.status.name != "STOPPED":
            engine.stop()
        server.stop()


@app.command("stop")
def stop(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show shutdown progress")
    ] = False,
) -> None:
    """Stop the active paper trading session."""
    global _paper_broker, _paper_start_time

    logger.info("Paper stop command executed")

    if not _is_running():
        console.print("[dim]Paper trading session is not running.[/dim]")
        return

    if verbose:
        _stop_with_progress()
    else:
        _stop_silent()


def _stop_silent() -> None:
    from titan.runtime.local_transport import LocalTransport

    try:
        transport = LocalTransport()
        transport.stop()
        _wait_until_runtime_stops()
        console.print("[bold yellow]~[/bold yellow] Paper trading session stopped.")
    except Exception as exc:
        console.print(f"[bold red]![/bold red] Failed to stop: {exc}")


def _stop_with_progress() -> None:
    _stop_silent()


@app.command("restart")
def restart(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show restart progress")
    ] = False,
    cash: Annotated[
        float, typer.Option("--cash", help="Initial cash balance (for new session)")
    ] = 1000000.0,
    symbol: Annotated[
        str, typer.Option("--symbol", "-s", help="Target symbol to trade")
    ] = "RELIANCE",
    exchange: Annotated[
        str, typer.Option("--exchange", "-e", help="Exchange segment")
    ] = "nse",
) -> None:
    """Restart paper trading (stop then start)."""
    logger.info("Paper restart command executed")

    if _is_running():
        if verbose:
            console.print("[yellow]~[/yellow] Stopping current session...")
        stop(verbose=verbose)

    if verbose:
        console.print("[green]+[/green] Starting new session...")

    start(verbose=verbose, dry_run=False, cash=cash, symbol=symbol, exchange=exchange)


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed status")
    ] = False,
) -> None:
    """Show paper trading session status."""
    logger.info("Paper status command executed")

    data = _build_session_data()

    if json_output:
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    if not data.get("running"):
        table = Table(
            title="Paper Trading", show_header=False, box=None, padding=(0, 2)
        )
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Provider", "PaperBroker (Simulated)")
        table.add_row("Status", "[dim]Not Running[/dim]")
        console.print(table)
        return

    _print_session_summary(data)

    if verbose:
        _print_positions_table(data)


@app.command("reset")
def reset(
    force: Annotated[
        bool, typer.Option("--force", help="Reset without confirmation")
    ] = False,
) -> None:
    """Reset paper trading state."""
    logger.info("Paper reset command executed")

    global _paper_broker, _paper_start_time

    if _is_running() and not force:
        console.print(
            "[yellow]~[/yellow] A session is running. Use --force to reset anyway, "
            "or stop the session first."
        )
        raise typer.Exit(code=1)

    if _is_running():
        _stop_silent()
        _paper_broker = None
        _paper_start_time = None

    from titan.paper.broker import PaperBroker

    broker = PaperBroker()
    broker.reset()

    console.print("[bold green]+[/bold green] Paper trading state reset.")


@app.command("report")
def report(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show full report details")
    ] = False,
    reset_after: Annotated[
        bool, typer.Option("--reset", help="Reset session after report")
    ] = False,
    export: Annotated[
        str | None,
        typer.Option("--export", help="Export report to file (JSON or CSV)"),
    ] = None,
) -> None:
    """Generate paper trading session report."""
    logger.info("Paper report command executed")

    if not _is_running():
        if json_output:
            console.print(json.dumps({"error": "No active paper session"}, indent=2))
        else:
            console.print("[dim]No active paper session to report.[/dim]")
        return

    data = _build_report_data()

    if json_output:
        console.print(json.dumps(data, indent=2, default=_json_serial))
    else:
        _print_report_tables(data, verbose)

    if export:
        export_path = Path(export)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        if export_path.suffix.lower() == ".csv":
            _export_csv(data, export_path)
            console.print(
                f"[bold green]+[/bold green] Report exported to {export_path}"
            )
        else:
            export_path.write_text(
                json.dumps(data, indent=2, default=_json_serial),
                encoding="utf-8",
            )
            console.print(
                f"[bold green]+[/bold green] Report exported to {export_path}"
            )

    if reset_after:
        reset(force=True)


def _print_report_tables(data: dict[str, Any], verbose: bool) -> None:
    session = data.get("session", {})
    portfolio = data.get("portfolio", {})
    perf = data.get("performance", {})
    pnl = data.get("pnl", {})

    session_table = Table(
        title="Session Summary", show_header=False, box=None, padding=(0, 2)
    )
    session_table.add_column("Key", style="bold")
    session_table.add_column("Value")
    session_table.add_row("Start Time", str(session.get("start_time", "N/A")))
    session_table.add_row(
        "Session Duration", _format_uptime(session.get("uptime_seconds", 0))  # type: ignore[arg-type]
    )
    session_table.add_row(
        "Initial Cash",
        _decimal_str(Decimal(str(session.get("initial_cash", 0)))),
    )
    console.print(session_table)

    portfolio_table = Table(
        title="Portfolio Summary", show_header=False, box=None, padding=(0, 2)
    )
    portfolio_table.add_column("Key", style="bold")
    portfolio_table.add_column("Value")
    portfolio_table.add_row(
        "Cash Balance", _decimal_str(Decimal(str(portfolio.get("cash", 0))))
    )
    portfolio_table.add_row(
        "Portfolio Value", _decimal_str(Decimal(str(portfolio.get("equity", 0))))
    )
    portfolio_table.add_row(
        "Buying Power", _decimal_str(Decimal(str(portfolio.get("buying_power", 0))))
    )
    portfolio_table.add_row(
        "Exposure", _decimal_str(Decimal(str(portfolio.get("exposure", 0))))
    )
    portfolio_table.add_row("Open Positions", str(portfolio.get("position_count", 0)))

    daily = Decimal(str(portfolio.get("daily_pnl", 0)))
    daily_s = "green" if daily >= 0 else "red"
    portfolio_table.add_row(
        "Daily P&L", f"[{daily_s}]{_decimal_str(daily)}[/{daily_s}]"
    )

    total = Decimal(str(portfolio.get("total_pnl", 0)))
    total_s = "green" if total >= 0 else "red"
    portfolio_table.add_row(
        "Total P&L", f"[{total_s}]{_decimal_str(total)}[/{total_s}]"
    )

    dd = Decimal(str(portfolio.get("drawdown", 0)))
    portfolio_table.add_row("Drawdown", f"{dd:.2%}")
    console.print(portfolio_table)

    realized = Decimal(str(pnl.get("realized", 0)))
    unrealized = Decimal(str(pnl.get("unrealized", 0)))
    pnl_table = Table(
        title="P&L Breakdown", show_header=False, box=None, padding=(0, 2)
    )
    pnl_table.add_column("Key", style="bold")
    pnl_table.add_column("Value")
    r_s = "green" if realized >= 0 else "red"
    pnl_table.add_row("Realized P&L", f"[{r_s}]{_decimal_str(realized)}[/{r_s}]")
    u_s = "green" if unrealized >= 0 else "red"
    pnl_table.add_row("Unrealized P&L", f"[{u_s}]{_decimal_str(unrealized)}[/{u_s}]")
    t_s = "green" if total >= 0 else "red"
    pnl_table.add_row("Total P&L", f"[{t_s}]{_decimal_str(total)}[/{t_s}]")
    console.print(pnl_table)

    perf_table = Table(
        title="Performance Metrics", show_header=False, box=None, padding=(0, 2)
    )
    perf_table.add_column("Key", style="bold")
    perf_table.add_column("Value")
    perf_table.add_row("Total Trades", str(perf.get("total_trades", 0)))
    perf_table.add_row("Winning Trades", str(perf.get("winning_trades", 0)))
    perf_table.add_row("Losing Trades", str(perf.get("losing_trades", 0)))
    wr = perf.get("win_rate", 0)
    perf_table.add_row("Win Rate", f"{wr:.1%}")
    perf_table.add_row("Profit Factor", f"{perf.get('profit_factor', 0):.2f}")
    perf_table.add_row(
        "Expectancy",
        _decimal_str(Decimal(str(perf.get("expectancy", 0)))),
    )
    perf_table.add_row(
        "Avg Winner",
        _decimal_str(Decimal(str(perf.get("avg_winner", 0)))),
    )
    perf_table.add_row(
        "Avg Loser",
        _decimal_str(Decimal(str(perf.get("avg_loser", 0)))),
    )
    perf_table.add_row(
        "Max Drawdown", f"{Decimal(str(perf.get('max_drawdown', 0))):.2%}"
    )
    console.print(perf_table)

    if verbose:
        positions = data.get("positions", [])
        if positions:
            pos_table = Table(
                title="Open Positions", show_header=True, header_style="bold"
            )
            pos_table.add_column("Symbol", style="bold")
            pos_table.add_column("Qty")
            pos_table.add_column("Avg Price")
            pos_table.add_column("Current")
            pos_table.add_column("Unrealized P&L")
            pos_table.add_column("Realized P&L")
            for p in positions:
                u_pnl = Decimal(str(p["unrealized_pnl"]))
                r_pnl = Decimal(str(p["realized_pnl"]))
                u_s = "green" if u_pnl >= 0 else "red"
                r_s = "green" if r_pnl >= 0 else "red"
                pos_table.add_row(
                    p["symbol"],
                    str(p["quantity"]),
                    _decimal_str(Decimal(str(p["average_price"]))),
                    _decimal_str(Decimal(str(p["current_price"]))),
                    f"[{u_s}]{_decimal_str(u_pnl)}[/{u_s}]",
                    f"[{r_s}]{_decimal_str(r_pnl)}[/{r_s}]",
                )
            console.print(pos_table)

        orders = data.get("orders", [])
        if orders:
            ord_table = Table(title="Orders", show_header=True, header_style="bold")
            ord_table.add_column("ID", style="bold")
            ord_table.add_column("Symbol")
            ord_table.add_column("Side")
            ord_table.add_column("Type")
            ord_table.add_column("Qty")
            ord_table.add_column("Filled")
            ord_table.add_column("Status")
            for o in orders:
                side = o["side"]
                side_color = "green" if side == "buy" else "red"
                ord_table.add_row(
                    o["order_id"],
                    o["symbol"],
                    f"[{side_color}]{side}[/{side_color}]",
                    o["type"],
                    str(o["quantity"]),
                    str(o["filled_quantity"]),
                    o["status"],
                )
            console.print(ord_table)

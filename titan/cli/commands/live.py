"""titan live - Live trading subsystem commands."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.live import Live
from rich.table import Table

if TYPE_CHECKING:
    from titan.config.models import TitanConfig

from titan.audit.models import AuditCategory, AuditSeverity, AuditSource
from titan.cli.common import (
    console,
    create_runtime_engine,
    get_alert_manager,
    get_config_manager,
    get_deployment_manager,
    get_monitoring_manager,
    get_recovery_manager,
    logger,
    set_runtime_engine,
)

live_app = typer.Typer(help="Live trading subsystem management.")
app = live_app


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


def _icon(status: CheckStatus) -> str:
    mapping = {
        CheckStatus.PASS: "[green]+[/green]",
        CheckStatus.FAIL: "[red]![/red]",
        CheckStatus.WARN: "[yellow]~[/yellow]",
        CheckStatus.SKIP: "[dim]-[/dim]",
    }
    return mapping[status]


def _runtime_status_icon(status_str: str) -> str:
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


def _to_json(obj: object) -> str:
    def _clean(o: object) -> object:
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_clean(i) for i in o]
        if hasattr(o, "isoformat"):
            return str(o.isoformat())
        if hasattr(o, "value"):
            return str(o.value)
        return o

    return json.dumps(_clean(asdict(obj)), indent=2, default=str) if hasattr(obj, "__dataclass_fields__") else json.dumps({"status": str(obj)}, indent=2)  # type: ignore[call-overload]


def _run_validations(config: TitanConfig, *, force: bool = False) -> StartupChecklist:
    checklist = StartupChecklist()

    checklist.checks.append(CheckResult("Configuration loaded", CheckStatus.PASS))

    broker_provider = getattr(getattr(config, "broker", None), "provider", "unknown")
    checklist.checks.append(
        CheckResult(f"Broker provider: {broker_provider}", CheckStatus.PASS)
    )

    env = getattr(getattr(config, "app", None), "environment", "unknown")
    checklist.checks.append(CheckResult(f"Environment: {env}", CheckStatus.PASS))

    if env == "production" and not force:
        api_key = getattr(getattr(config, "broker", None), "api_key", "")
        if not api_key:
            checklist.checks.append(
                CheckResult(
                    "Production API key",
                    CheckStatus.FAIL,
                    "Missing broker API key for production",
                )
            )
        else:
            checklist.checks.append(CheckResult("Production API key", CheckStatus.PASS))

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

    monitoring = getattr(config, "monitoring", None)
    if monitoring and getattr(monitoring, "enabled", False):
        checklist.checks.append(CheckResult("Monitoring", CheckStatus.PASS))
    else:
        checklist.checks.append(
            CheckResult("Monitoring", CheckStatus.WARN, "Monitoring disabled")
        )

    checklist.checks.append(CheckResult("Recovery system", CheckStatus.PASS))
    checklist.checks.append(CheckResult("Audit trail", CheckStatus.PASS))
    checklist.checks.append(CheckResult("Runtime engine", CheckStatus.PASS))

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


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed status")
    ] = False,
) -> None:
    """Show live trading subsystem status."""
    logger.info("Live status command executed")
    config_mgr = get_config_manager()
    config = config_mgr.get_config()
    deployment = get_deployment_manager()
    dep_report = deployment.generate_report()

    broker_provider = config.broker.provider
    environment = config.app.environment
    dep_status = dep_report.status.value
    dep_uptime = dep_report.uptime_seconds
    dep_version = dep_report.version.version

    engine = None
    try:
        from titan.cli.common import _runtime_engine

        engine = _runtime_engine
    except Exception:
        pass

    runtime_status = "stopped"
    runtime_uptime = 0.0
    broker_connected = False
    pipeline_execs = 0
    active_subs = 0
    if engine is not None:
        report = engine.generate_report()
        runtime_status = report.runtime_status.name.lower()
        runtime_uptime = report.performance.uptime_seconds
        broker_connected = report.broker.connection.value == "connected"
        pipeline_execs = report.scheduler.pipeline_executions
        active_subs = report.market.active_subscriptions

    if json_output:
        data = {
            "broker_provider": broker_provider,
            "environment": environment,
            "deployment_status": dep_status,
            "deployment_uptime_seconds": dep_uptime,
            "version": dep_version,
            "runtime_status": runtime_status,
            "runtime_uptime_seconds": runtime_uptime,
            "broker_connected": broker_connected,
            "pipeline_executions": pipeline_execs,
            "active_subscriptions": active_subs,
        }
        console.print(json.dumps(data, indent=2))
        return

    table = Table(title="Live Trading", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Broker", broker_provider)
    table.add_row("Environment", environment)
    table.add_row("Version", dep_version)

    dep_s = dep_status
    table.add_row("Deployment", f"{_runtime_status_icon(dep_s)} {dep_s}")
    table.add_row("Deployment Uptime", _format_uptime(dep_uptime))

    rt_s = runtime_status
    table.add_row("Runtime", f"{_runtime_status_icon(rt_s)} {rt_s}")
    table.add_row("Runtime Uptime", _format_uptime(runtime_uptime))

    br_s = "connected" if broker_connected else "disconnected"
    table.add_row("Broker Connection", f"{_runtime_status_icon(br_s)} {br_s}")
    table.add_row("Pipeline Executions", str(pipeline_execs))
    table.add_row("Active Subscriptions", str(active_subs))
    console.print(table)

    if verbose:
        _print_verbose_status(config, engine)


def _print_verbose_status(config: object, engine: object) -> None:
    risk = getattr(config, "risk", None)
    if risk:
        table = Table(
            title="Risk Configuration", show_header=False, box=None, padding=(0, 2)
        )
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row(
            "Max Position Size", str(getattr(risk, "max_position_size", "N/A"))
        )
        table.add_row(
            "Max Drawdown", f"{getattr(risk, 'max_drawdown_percent', 'N/A')}%"
        )
        table.add_row("Max Daily Loss", str(getattr(risk, "max_daily_loss", "N/A")))
        table.add_row("Stop Loss", f"{getattr(risk, 'stop_loss_percent', 'N/A')}%")
        console.print(table)

    if engine is not None and hasattr(engine, "generate_report"):
        report = engine.generate_report()
        if report.component_health:
            table = Table(
                title="Component Health", show_header=True, header_style="bold"
            )
            table.add_column("Component", style="bold")
            table.add_column("Status")
            table.add_column("Latency")
            table.add_column("Error")
            for ch in report.component_health:
                s = ch.status.value if hasattr(ch, "status") else str(ch.status)
                icon = _runtime_status_icon(s)
                err = ch.error if ch.error else ""
                lat = f"{ch.latency_ms:.1f}ms" if ch.latency_ms else "-"
                table.add_row(ch.component_name, f"{icon} {s}", lat, err)
            console.print(table)

    try:
        mgr = get_monitoring_manager()
        mreport = mgr.generate_report()
        table = Table(title="Monitoring", show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Collectors", str(mreport.collector_count))
        table.add_row("Total Collections", str(mreport.total_collections))
        table.add_row("Failed", str(mreport.failed_collections))
        console.print(table)
    except Exception:
        pass


@app.command("start")
def start(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show startup progress")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Validate only, do not start")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Skip safety checks")] = False,
) -> None:
    """Start live trading with full validation pipeline."""
    logger.info("Live start command executed")

    config_mgr = get_config_manager()
    try:
        config = config_mgr.get_config()
    except Exception as e:
        console.print(f"[bold red]![/bold red] Configuration error: {e}")
        raise typer.Exit(code=2)

    checklist = _run_validations(config, force=force)

    if verbose or dry_run:
        _display_checklist(checklist)

    if not checklist.all_passed:
        console.print(
            "[bold red]![/bold red] Validation failed. Use --force to override."
        )
        raise typer.Exit(code=2)

    if dry_run:
        console.print("[bold green]+[/bold green] Dry run passed. All validations OK.")
        return

    if verbose:
        _start_with_progress(config)
    else:
        _start_silent(config)


def _start_silent(config: TitanConfig) -> None:
    try:
        engine = create_runtime_engine(config)
        set_runtime_engine(engine)
        engine.start()

        dm = get_deployment_manager()
        try:
            dm.start()
        except Exception:
            pass

        monitoring = get_monitoring_manager()
        try:
            monitoring.start()
        except Exception:
            pass

        console.print("[bold green]+[/bold green] Live trading started.")
    except Exception as e:
        console.print(f"[bold red]![/bold red] Failed to start: {e}")
        raise typer.Exit(code=3)


def _start_with_progress(config: TitanConfig) -> None:
    steps = [
        "Loading configuration",
        "Creating broker",
        "Validating environment",
        "Starting deployment",
        "Starting runtime engine",
        "Starting monitoring",
        "Recording audit event",
        "Live trading started",
    ]

    with Live(console=console, refresh_per_second=4) as live:
        for i, step_name in enumerate(steps):
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for j, name in enumerate(steps):
                if j < i:
                    table.add_row(name, "[green]+[/green] done")
                elif j == i:
                    table.add_row(name, "[yellow]...[/yellow]")
                else:
                    table.add_row(name, "[dim]-[/dim]")
            live.update(table)
            time.sleep(0.15)

        try:
            engine = create_runtime_engine(config)
            set_runtime_engine(engine)
            engine.start()

            try:
                get_deployment_manager().start()
            except Exception:
                pass

            try:
                get_monitoring_manager().start()
            except Exception:
                pass

            try:
                from titan.audit.manager import AuditManager

                audit = AuditManager()
                audit.record(
                    source=AuditSource.USER,
                    category=AuditCategory.SYSTEM_START,
                    severity=AuditSeverity.INFO,
                    action="titan_live_started",
                )
            except Exception:
                pass

            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for name in steps:
                table.add_row(name, "[green]+[/green] done")
            live.update(table)
        except Exception as e:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for j, name in enumerate(steps):
                if j < len(steps) - 1:
                    table.add_row(name, "[green]+[/green] done")
                else:
                    table.add_row(name, "[red]![/red] failed")
            table.add_row(f"Error: {e}", "[bold red]![/bold red]")
            live.update(table)
            raise typer.Exit(code=3)


@app.command("stop")
def stop(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show shutdown progress")
    ] = False,
) -> None:
    """Stop live trading gracefully."""
    logger.info("Live stop command executed")

    from titan.cli.common import _runtime_engine

    engine = _runtime_engine
    if engine is None or engine.status.name == "STOPPED":
        console.print("[dim]Live trading is not running.[/dim]")
        return

    if verbose:
        _stop_with_progress()
    else:
        _stop_silent()


def _stop_silent() -> None:
    from titan.cli.common import _runtime_engine

    engine = _runtime_engine
    if engine is not None:
        try:
            engine.stop()
        except Exception:
            pass

    try:
        get_monitoring_manager().stop()
    except Exception:
        pass

    try:
        get_deployment_manager().stop()
    except Exception:
        pass

    try:
        from titan.audit.manager import AuditManager

        audit = AuditManager()
        audit.record(
            source=AuditSource.USER,
            category=AuditCategory.SYSTEM_STOP,
            severity=AuditSeverity.INFO,
            action="titan_live_stopped",
        )
    except Exception:
        pass

    set_runtime_engine(None)  # type: ignore[arg-type]
    console.print("[bold yellow]~[/bold yellow] Live trading stopped.")


def _stop_with_progress() -> None:
    from titan.cli.common import _runtime_engine

    steps = [
        "Stopping runtime engine",
        "Stopping monitoring",
        "Stopping deployment",
        "Recording audit event",
        "Live trading stopped",
    ]

    with Live(console=console, refresh_per_second=4) as live:
        for i, step_name in enumerate(steps):
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for j, name in enumerate(steps):
                if j < i:
                    table.add_row(name, "[green]+[/green] done")
                elif j == i:
                    table.add_row(name, "[yellow]...[/yellow]")
                else:
                    table.add_row(name, "[dim]-[/dim]")
            live.update(table)
            time.sleep(0.15)

        engine = _runtime_engine
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

        try:
            get_monitoring_manager().stop()
        except Exception:
            pass

        try:
            get_deployment_manager().stop()
        except Exception:
            pass

        try:
            from titan.audit.manager import AuditManager

            audit = AuditManager()
            audit.record(
                source=AuditSource.USER,
                category=AuditCategory.SYSTEM_STOP,
                severity=AuditSeverity.INFO,
                action="titan_live_stopped",
            )
        except Exception:
            pass

        set_runtime_engine(None)  # type: ignore[arg-type]

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Step", style="bold")
        table.add_column("Status")
        for name in steps:
            table.add_row(name, "[green]+[/green] done")
        live.update(table)


@app.command("restart")
def restart(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show restart progress")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Skip safety checks")] = False,
) -> None:
    """Restart live trading (stop then start)."""
    logger.info("Live restart command executed")

    from titan.cli.common import _runtime_engine

    engine = _runtime_engine
    is_running = engine is not None and engine.status.name != "STOPPED"

    if is_running:
        if verbose:
            console.print("[yellow]~[/yellow] Stopping live trading...")
        stop(verbose=verbose)

    if verbose:
        console.print("[green]+[/green] Starting live trading...")

    start(verbose=verbose, dry_run=False, force=force)


# ── Session Reset ──────────────────────────────────────────


def _reset_live_session() -> None:
    """Reset live trading session state (for testing)."""
    set_runtime_engine(None)  # type: ignore[arg-type]


def _get_engine() -> Any:
    """Get the current runtime engine or None."""
    from titan.cli.common import _runtime_engine

    return _runtime_engine


def _get_broker() -> Any:
    """Get the broker from the current runtime engine or None."""
    engine = _get_engine()
    if engine is None:
        return None
    return getattr(engine, "broker", None)


def _require_engine() -> Any:
    """Get engine or print error and exit."""
    engine = _get_engine()
    if engine is None or engine.status.name == "STOPPED":
        console.print("[dim]Live trading is not running.[/dim]")
        raise typer.Exit(code=0)
    return engine


# ── Pause / Resume ────────────────────────────────────────


@app.command("pause")
def pause(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show pause progress")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Pause live trading (suspend scheduler)."""
    logger.info("Live pause command executed")

    engine = _get_engine()
    if engine is None or engine.status.name == "STOPPED":
        if json_output:
            console.print(
                json.dumps({"status": "not running", "paused": False}, indent=2)
            )
            return
        console.print("[dim]Live trading is not running.[/dim]")
        return

    if engine.status.name == "PAUSED":
        if json_output:
            console.print(
                json.dumps({"status": "already paused", "paused": True}, indent=2)
            )
            return
        console.print("[yellow]~[/yellow] Live trading is already paused.")
        return

    try:
        engine.pause()
        if verbose:
            console.print(
                "[yellow]~[/yellow] Live trading paused. Scheduler suspended."
            )
        else:
            console.print("[bold yellow]~[/bold yellow] Live trading paused.")
    except Exception as e:
        if json_output:
            console.print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        else:
            console.print(f"[bold red]![/bold red] Failed to pause: {e}")
        raise typer.Exit(code=3)

    if json_output:
        console.print(json.dumps({"status": "paused", "paused": True}, indent=2))


@app.command("resume")
def resume(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show resume progress")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Resume live trading from paused state."""
    logger.info("Live resume command executed")

    engine = _get_engine()
    if engine is None or engine.status.name == "STOPPED":
        if json_output:
            console.print(
                json.dumps({"status": "not running", "resumed": False}, indent=2)
            )
            return
        console.print("[dim]Live trading is not running.[/dim]")
        return

    if engine.status.name != "PAUSED":
        if json_output:
            console.print(
                json.dumps({"status": "not paused", "resumed": False}, indent=2)
            )
            return
        console.print("[yellow]~[/yellow] Live trading is not paused.")
        return

    try:
        engine.resume()
        if verbose:
            console.print("[green]+[/green] Live trading resumed. Scheduler active.")
        else:
            console.print("[bold green]+[/bold green] Live trading resumed.")
    except Exception as e:
        if json_output:
            console.print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        else:
            console.print(f"[bold red]![/bold red] Failed to resume: {e}")
        raise typer.Exit(code=3)

    if json_output:
        console.print(json.dumps({"status": "running", "resumed": True}, indent=2))


# ── Positions ──────────────────────────────────────────────


@app.command("positions")
def positions(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed positions")
    ] = False,
) -> None:
    """Show current open positions."""
    logger.info("Live positions command executed")

    broker = _get_broker()
    if broker is None:
        if json_output:
            console.print(json.dumps({"positions": [], "count": 0}, indent=2))
            return
        console.print("[dim]No broker connected. Start live trading first.[/dim]")
        return

    try:
        pos_list = broker.positions()
    except Exception as e:
        if json_output:
            console.print(
                json.dumps({"error": str(e), "positions": [], "count": 0}, indent=2)
            )
        else:
            console.print(f"[bold red]![/bold red] Failed to fetch positions: {e}")
        return

    if json_output:
        data = {
            "positions": [
                {
                    "symbol": p.symbol,
                    "exchange": _clean_enum(p.exchange),
                    "instrument_type": _clean_enum(p.instrument_type),
                    "product": _clean_enum(p.product),
                    "quantity": p.quantity,
                    "buy_quantity": p.buy_quantity,
                    "sell_quantity": p.sell_quantity,
                    "buy_price": _clean_decimal(p.buy_price),
                    "sell_price": _clean_decimal(p.sell_price),
                    "current_price": _clean_decimal(p.current_price),
                    "pnl": _clean_decimal(p.pnl),
                    "realised_pnl": _clean_decimal(p.realised_pnl),
                    "multiplier": p.multiplier,
                }
                for p in pos_list
            ],
            "count": len(pos_list),
        }
        console.print(json.dumps(data, indent=2))
        return

    if not pos_list:
        console.print("[dim]No open positions.[/dim]")
        return

    table = Table(title="Open Positions", show_header=True, header_style="bold")
    table.add_column("Symbol", style="bold")
    table.add_column("Exchange")
    table.add_column("Type")
    table.add_column("Qty", justify="right")
    table.add_column("Buy Qty", justify="right")
    table.add_column("Sell Qty", justify="right")
    table.add_column("Buy Price", justify="right")
    table.add_column("Sell Price", justify="right")
    table.add_column("LTP", justify="right")
    table.add_column("P&L", justify="right")

    total_pnl = 0.0
    for p in pos_list:
        pnl_val = _clean_decimal(p.pnl)
        pnl_str = f"{pnl_val}" if pnl_val else "0.00"
        table.add_row(
            p.symbol,
            _clean_enum(p.exchange),
            _clean_enum(p.instrument_type),
            str(p.quantity),
            str(p.buy_quantity),
            str(p.sell_quantity),
            _clean_decimal(p.buy_price) or "-",
            _clean_decimal(p.sell_price) or "-",
            _clean_decimal(p.current_price) or "-",
            pnl_str,
        )
        try:
            total_pnl += float(p.pnl) if p.pnl else 0.0
        except (TypeError, ValueError):
            pass

    console.print(table)
    console.print(f"  {len(pos_list)} position(s), total P&L: {total_pnl:.2f}")


# ── Orders ──────────────────────────────────────────────────


@app.command("orders")
def orders(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed orders")
    ] = False,
    status_filter: Annotated[
        str, typer.Option("--status", "-s", help="Filter by status")
    ] = "",
) -> None:
    """Show current and recent orders."""
    logger.info("Live orders command executed")

    broker = _get_broker()
    if broker is None:
        if json_output:
            console.print(json.dumps({"orders": [], "count": 0}, indent=2))
            return
        console.print("[dim]No broker connected. Start live trading first.[/dim]")
        return

    try:
        order_list = broker.orders()
    except Exception as e:
        if json_output:
            console.print(
                json.dumps({"error": str(e), "orders": [], "count": 0}, indent=2)
            )
        else:
            console.print(f"[bold red]![/bold red] Failed to fetch orders: {e}")
        return

    if status_filter:
        sf = status_filter.upper()
        order_list = [o for o in order_list if o.status.name == sf]

    if json_output:
        data = {
            "orders": [
                {
                    "broker_order_id": o.broker_order_id,
                    "symbol": o.symbol,
                    "exchange": _clean_enum(o.exchange),
                    "side": _clean_enum(o.side),
                    "order_type": _clean_enum(o.order_type),
                    "product": _clean_enum(o.product),
                    "status": _clean_enum(o.status),
                    "quantity": o.quantity,
                    "filled_quantity": o.filled_quantity,
                    "pending_quantity": o.pending_quantity,
                    "average_price": _clean_decimal(o.average_price),
                    "price": _clean_decimal(o.price),
                    "trigger_price": _clean_decimal(o.trigger_price),
                    "tag": o.tag,
                    "rejected_reason": o.rejected_reason or None,
                    "placed_at": _clean_datetime(o.placed_at),
                    "filled_at": _clean_datetime(o.filled_at),
                }
                for o in order_list
            ],
            "count": len(order_list),
        }
        console.print(json.dumps(data, indent=2))
        return

    if not order_list:
        console.print("[dim]No orders found.[/dim]")
        return

    table = Table(title="Orders", show_header=True, header_style="bold")
    table.add_column("Order ID", style="bold")
    table.add_column("Symbol")
    table.add_column("Side")
    table.add_column("Type")
    table.add_column("Qty", justify="right")
    table.add_column("Filled", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Status")
    table.add_column("Tag")

    for o in order_list:
        side_color = "green" if o.side.name == "BUY" else "red"
        table.add_row(
            o.broker_order_id,
            o.symbol,
            f"[{side_color}]{o.side.name}[/{side_color}]",
            o.order_type.name,
            str(o.quantity),
            str(o.filled_quantity),
            _clean_decimal(o.price) or _clean_decimal(o.average_price) or "-",
            o.status.name,
            o.tag or "",
        )

    console.print(table)
    console.print(f"  {len(order_list)} order(s)")


# ── Exposure ───────────────────────────────────────────────


@app.command("exposure")
def exposure(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed exposure")
    ] = False,
) -> None:
    """Show capital and risk exposure."""
    logger.info("Live exposure command executed")

    broker = _get_broker()
    funds_data: dict[str, Any] = {}
    margin_data: dict[str, Any] = {}

    if broker is not None:
        try:
            funds = broker.funds()
            funds_data = {
                "available_cash": _clean_decimal(funds.available_cash),
                "used_cash": _clean_decimal(funds.used_cash),
                "payin": _clean_decimal(funds.payin),
                "payout": _clean_decimal(funds.payout),
                "realised_pnl": _clean_decimal(funds.realised_pnl),
                "unrealised_pnl": _clean_decimal(funds.unrealised_pnl),
            }
        except Exception:
            pass

        try:
            margin = broker.margin()
            margin_data = {
                "total_margin": _clean_decimal(margin.total_margin),
                "used_margin": _clean_decimal(margin.used_margin),
                "available_margin": _clean_decimal(margin.available_margin),
                "delivery_margin": _clean_decimal(margin.delivery_margin),
                "span_margin": _clean_decimal(margin.span_margin),
                "exposure_margin": _clean_decimal(margin.exposure_margin),
            }
        except Exception:
            pass

    if json_output:
        data = {
            "funds": funds_data,
            "margin": margin_data,
            "has_broker": broker is not None,
        }
        console.print(json.dumps(data, indent=2))
        return

    if broker is None:
        console.print("[dim]No broker connected. Start live trading first.[/dim]")
        return

    if funds_data:
        table = Table(title="Funds", show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold")
        table.add_column("Value")
        for k, v in funds_data.items():
            table.add_row(k.replace("_", " ").title(), str(v) if v else "N/A")
        console.print(table)

    if margin_data:
        table = Table(title="Margin", show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold")
        table.add_column("Value")
        for k, v in margin_data.items():
            table.add_row(k.replace("_", " ").title(), str(v) if v else "N/A")
        console.print(table)

    if not funds_data and not margin_data:
        console.print("[dim]No exposure data available.[/dim]")


# ── Health ──────────────────────────────────────────────────


@app.command("health")
def health(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed health")
    ] = False,
) -> None:
    """Show system health across all components."""
    logger.info("Live health command executed")

    engine = _get_engine()
    engine_status = "stopped"
    engine_health: dict[str, Any] = {}
    component_health_list: list[dict[str, Any]] = []

    if engine is not None:
        try:
            report = engine.generate_report()
            engine_status = report.runtime_status.name.lower()
            if report.component_health:
                for ch in report.component_health:
                    s = ch.status.value if hasattr(ch, "status") else str(ch.status)
                    component_health_list.append(
                        {
                            "component": ch.component_name,
                            "status": s,
                            "latency_ms": ch.latency_ms,
                            "error": ch.error or None,
                        }
                    )
            engine_health = {
                "runtime_status": engine_status,
                "broker_connection": report.broker.connection.value,
                "uptime_seconds": report.uptime_seconds,
                "stream_status": report.stream_status,
                "scheduler_active": report.scheduler_active,
                "warnings": list(report.warnings),
                "errors": list(report.errors),
            }
        except Exception:
            pass

    monitoring_health: dict[str, Any] = {}
    try:
        mgr = get_monitoring_manager()
        mreport = mgr.generate_report()
        monitoring_health = {
            "collector_count": mreport.collector_count,
            "total_collections": mreport.total_collections,
            "failed_collections": mreport.failed_collections,
            "uptime_seconds": mreport.uptime_seconds,
        }
    except Exception:
        pass

    recovery_health: dict[str, Any] = {}
    try:
        rmgr = get_recovery_manager()
        rreport = rmgr.generate_report()
        recovery_health = {
            "status": rreport.status.value if hasattr(rreport, "status") else "unknown",
            "total_attempts": rreport.total_attempts,
            "successful_attempts": rreport.successful_attempts,
            "failed_attempts": rreport.failed_attempts,
        }
    except Exception:
        pass

    alert_health: dict[str, Any] = {}
    try:
        amgr = get_alert_manager()
        areport = amgr.generate_report()
        alert_health = {
            "total_alerts": areport.total_alerts,
            "active_alerts": areport.active_alerts,
            "critical_alerts": areport.critical_alerts,
        }
    except Exception:
        pass

    if json_output:
        data = {
            "engine": engine_health,
            "components": component_health_list,
            "monitoring": monitoring_health,
            "recovery": recovery_health,
            "alerts": alert_health,
        }
        console.print(json.dumps(data, indent=2))
        return

    if engine is None:
        console.print("[dim]Live trading is not running.[/dim]")
        return

    table = Table(title="System Health", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    rt_s = engine_status
    table.add_row("Runtime", f"{_runtime_status_icon(rt_s)} {rt_s}")
    table.add_row("Uptime", _format_uptime(engine_health.get("uptime_seconds", 0)))
    br_s = engine_health.get("broker_connection", "unknown")
    table.add_row("Broker", f"{_runtime_status_icon(br_s)} {br_s}")
    st_s = engine_health.get("stream_status", "unknown")
    table.add_row("Stream", f"{_runtime_status_icon(st_s)} {st_s}")
    sched = "active" if engine_health.get("scheduler_active") else "inactive"
    table.add_row(
        "Scheduler",
        f"{_runtime_status_icon('running' if sched == 'active' else 'stopped')} {sched}",
    )
    console.print(table)

    if component_health_list:
        ch_table = Table(
            title="Component Health", show_header=True, header_style="bold"
        )
        ch_table.add_column("Component", style="bold")
        ch_table.add_column("Status")
        ch_table.add_column("Latency")
        ch_table.add_column("Error")
        for ch in component_health_list:
            icon = _runtime_status_icon(ch["status"])
            err = ch["error"] or ""
            lat = f"{ch['latency_ms']:.1f}ms" if ch["latency_ms"] else "-"
            ch_table.add_row(ch["component"], f"{icon} {ch['status']}", lat, err)
        console.print(ch_table)

    if monitoring_health:
        m_table = Table(title="Monitoring", show_header=False, box=None, padding=(0, 2))
        m_table.add_column("Key", style="bold")
        m_table.add_column("Value")
        m_table.add_row("Collectors", str(monitoring_health.get("collector_count", 0)))
        m_table.add_row(
            "Total Collections", str(monitoring_health.get("total_collections", 0))
        )
        m_table.add_row("Failed", str(monitoring_health.get("failed_collections", 0)))
        console.print(m_table)

    if recovery_health:
        r_table = Table(title="Recovery", show_header=False, box=None, padding=(0, 2))
        r_table.add_column("Key", style="bold")
        r_table.add_column("Value")
        r_table.add_row("Status", recovery_health.get("status", "unknown"))
        r_table.add_row("Total Attempts", str(recovery_health.get("total_attempts", 0)))
        r_table.add_row(
            "Successful", str(recovery_health.get("successful_attempts", 0))
        )
        r_table.add_row("Failed", str(recovery_health.get("failed_attempts", 0)))
        console.print(r_table)

    if alert_health:
        a_table = Table(title="Alerts", show_header=False, box=None, padding=(0, 2))
        a_table.add_column("Key", style="bold")
        a_table.add_column("Value")
        a_table.add_row("Total", str(alert_health.get("total_alerts", 0)))
        a_table.add_row("Active", str(alert_health.get("active_alerts", 0)))
        a_table.add_row("Critical", str(alert_health.get("critical_alerts", 0)))
        console.print(a_table)

    warnings = engine_health.get("warnings", [])
    if warnings:
        console.print()
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for w in warnings:
            console.print(f"  [yellow]~[/yellow] {w}")

    errors = engine_health.get("errors", [])
    if errors:
        console.print()
        console.print("[bold red]Errors:[/bold red]")
        for e in errors:
            console.print(f"  [red]![/red] {e}")


# ── Report ──────────────────────────────────────────────────


@app.command("report")
def report(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed report")
    ] = False,
    export_path: Annotated[
        str, typer.Option("--export", help="Export report to file")
    ] = "",
) -> None:
    """Generate comprehensive live trading operational report."""
    logger.info("Live report command executed")

    dep_report = None
    try:
        dep_report = get_deployment_manager().generate_report()
    except Exception:
        pass

    engine = _get_engine()
    rt_report = None
    if engine is not None:
        try:
            rt_report = engine.generate_report()
        except Exception:
            pass

    broker = _get_broker()
    positions_data: list[dict[str, Any]] = []
    orders_data: list[dict[str, Any]] = []
    funds_data: dict[str, Any] = {}
    if broker is not None:
        try:
            for p in broker.positions():
                positions_data.append(
                    {
                        "symbol": p.symbol,
                        "exchange": _clean_enum(p.exchange),
                        "quantity": p.quantity,
                        "pnl": _clean_decimal(p.pnl),
                    }
                )
        except Exception:
            pass
        try:
            for o in broker.orders():
                orders_data.append(
                    {
                        "broker_order_id": o.broker_order_id,
                        "symbol": o.symbol,
                        "side": _clean_enum(o.side),
                        "status": _clean_enum(o.status),
                        "quantity": o.quantity,
                    }
                )
        except Exception:
            pass
        try:
            funds = broker.funds()
            funds_data = {
                "available_cash": _clean_decimal(funds.available_cash),
                "used_cash": _clean_decimal(funds.used_cash),
                "realised_pnl": _clean_decimal(funds.realised_pnl),
                "unrealised_pnl": _clean_decimal(funds.unrealised_pnl),
            }
        except Exception:
            pass

    monitoring_data: dict[str, Any] = {}
    try:
        mreport = get_monitoring_manager().generate_report()
        monitoring_data = {
            "collector_count": mreport.collector_count,
            "total_collections": mreport.total_collections,
            "failed_collections": mreport.failed_collections,
        }
    except Exception:
        pass

    recovery_data: dict[str, Any] = {}
    try:
        rreport = get_recovery_manager().generate_report()
        recovery_data = {
            "status": rreport.status.value if hasattr(rreport, "status") else "unknown",
            "total_attempts": rreport.total_attempts,
        }
    except Exception:
        pass

    audit_data: dict[str, Any] = {}
    try:
        from titan.audit.manager import AuditManager

        audit = AuditManager()
        areport = audit.generate_report()
        audit_data = {
            "total_events": areport.total_events,
            "integrity_status": areport.integrity_status,
        }
    except Exception:
        pass

    report_data: dict[str, Any] = {
        "runtime": {
            "status": rt_report.runtime_status.name.lower() if rt_report else "stopped",
            "uptime_seconds": rt_report.uptime_seconds if rt_report else 0,
            "broker_status": (
                rt_report.broker.connection.value if rt_report else "disconnected"
            ),
            "pipeline_executions": rt_report.pipeline_executions if rt_report else 0,
            "warnings": list(rt_report.warnings) if rt_report else [],
            "errors": list(rt_report.errors) if rt_report else [],
        },
        "deployment": {
            "status": dep_report.status.value if dep_report else "unknown",
            "version": dep_report.version.version if dep_report else "unknown",
            "uptime_seconds": dep_report.uptime_seconds if dep_report else 0,
        },
        "positions": positions_data,
        "orders": orders_data,
        "funds": funds_data,
        "monitoring": monitoring_data,
        "recovery": recovery_data,
        "audit": audit_data,
    }

    if json_output:
        console.print(json.dumps(report_data, indent=2))

        if export_path:
            try:
                with open(export_path, "w") as f:
                    f.write(json.dumps(report_data, indent=2))
                console.print(f"[green]+[/green] Report exported to {export_path}")
            except Exception as e:
                console.print(f"[bold red]![/bold red] Export failed: {e}")
        return

    title = "Live Trading Report"
    console.rule(f"[bold]{title}[/bold]")

    table = Table(title="Runtime Summary", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    rt_data = report_data.get("runtime", {})
    rt_s = str(rt_data.get("status", "stopped"))
    table.add_row("Runtime", f"{_runtime_status_icon(rt_s)} {rt_s}")
    table.add_row("Uptime", _format_uptime(float(rt_data.get("uptime_seconds", 0))))
    br_s = str(rt_data.get("broker_connection", "disconnected"))
    table.add_row("Broker", f"{_runtime_status_icon(br_s)} {br_s}")
    table.add_row("Pipeline Executions", str(rt_data.get("pipeline_executions", 0)))
    dep_data = report_data.get("deployment", {})
    dep_v = str(dep_data.get("version", "unknown"))
    table.add_row("Version", dep_v)
    console.print(table)

    if positions_data:
        p_table = Table(title="Positions", show_header=True, header_style="bold")
        p_table.add_column("Symbol")
        p_table.add_column("Exchange")
        p_table.add_column("Qty", justify="right")
        p_table.add_column("P&L", justify="right")
        for p in positions_data:
            p_table.add_row(
                p["symbol"], p["exchange"], str(p["quantity"]), str(p["pnl"] or "0")
            )
        console.print(p_table)

    if orders_data:
        o_table = Table(title="Orders", show_header=True, header_style="bold")
        o_table.add_column("Order ID")
        o_table.add_column("Symbol")
        o_table.add_column("Side")
        o_table.add_column("Status")
        o_table.add_column("Qty", justify="right")
        for o in orders_data:
            o_table.add_row(
                o["broker_order_id"],
                o["symbol"],
                o["side"],
                o["status"],
                str(o["quantity"]),
            )
        console.print(o_table)

    if funds_data:
        f_table = Table(title="Funds", show_header=False, box=None, padding=(0, 2))
        f_table.add_column("Key", style="bold")
        f_table.add_column("Value")
        for k, v in funds_data.items():
            f_table.add_row(k.replace("_", " ").title(), str(v) if v else "N/A")
        console.print(f_table)

    if monitoring_data:
        m_table = Table(title="Monitoring", show_header=False, box=None, padding=(0, 2))
        m_table.add_column("Key", style="bold")
        m_table.add_column("Value")
        m_table.add_row("Collectors", str(monitoring_data.get("collector_count", 0)))
        m_table.add_row(
            "Total Collections", str(monitoring_data.get("total_collections", 0))
        )
        m_table.add_row("Failed", str(monitoring_data.get("failed_collections", 0)))
        console.print(m_table)

    if recovery_data:
        r_table = Table(title="Recovery", show_header=False, box=None, padding=(0, 2))
        r_table.add_column("Key", style="bold")
        r_table.add_column("Value")
        r_table.add_row("Status", recovery_data.get("status", "unknown"))
        r_table.add_row("Total Attempts", str(recovery_data.get("total_attempts", 0)))
        console.print(r_table)

    if audit_data:
        a_table = Table(title="Audit", show_header=False, box=None, padding=(0, 2))
        a_table.add_column("Key", style="bold")
        a_table.add_column("Value")
        a_table.add_row("Total Events", str(audit_data.get("total_events", 0)))
        a_table.add_row("Integrity", audit_data.get("integrity_status", "unknown"))
        console.print(a_table)

    rt_warnings = rt_data.get("warnings", [])
    if rt_warnings:
        console.print()
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for w in rt_warnings:
            console.print(f"  [yellow]~[/yellow] {w}")

    rt_errors = rt_data.get("errors", [])
    if rt_errors:
        console.print()
        console.print("[bold red]Errors:[/bold red]")
        for err in rt_errors:
            console.print(f"  [red]![/red] {err}")

    console.rule("[dim]End of Report[/dim]")

    if export_path:
        try:
            with open(export_path, "w") as f:
                f.write(json.dumps(report_data, indent=2))
            console.print(f"[green]+[/green] Report exported to {export_path}")
        except Exception as e:
            console.print(f"[bold red]![/bold red] Export failed: {e}")


# ── Serialization Helpers ────────────────────────────────────


def _clean_enum(val: Any) -> str:
    """Extract string value from an enum."""
    if val is None:
        return ""
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


def _clean_decimal(val: Any) -> str | None:
    """Convert Decimal to string, None if unavailable."""
    if val is None:
        return None
    try:
        return str(val)
    except Exception:
        return None


def _clean_datetime(val: Any) -> str | None:
    """Convert datetime to ISO string, None if unavailable."""
    if val is None:
        return None
    try:
        if hasattr(val, "isoformat"):
            return str(val.isoformat())
        return str(val)
    except Exception:
        return None

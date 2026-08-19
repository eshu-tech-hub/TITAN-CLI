"""titan runtime - Runtime engine lifecycle commands."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Annotated

import typer
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from titan.cli.common import (
    console,
    get_monitoring_manager,
    get_recovery_manager,
    get_runtime_engine,
    get_settings,
    logger,
)
from titan.runtime.exceptions import RuntimeError as TitanRuntimeError
from titan.runtime.models import RuntimeReport, RuntimeStatus
from titan.runtime.service import RuntimeService
from titan.runtime.transport import InProcessTransport

if TYPE_CHECKING:
    from titan.runtime.runtime import RuntimeEngine

runtime_app = typer.Typer(help="Runtime engine lifecycle management.")
app = runtime_app


def _status_icon(status_str: str) -> str:
    mapping = {
        "running": "[green]+[/green]",
        "healthy": "[green]+[/green]",
        "connected": "[green]+[/green]",
        "stopped": "[red]~[/red]",
        "unhealthy": "[red]![/red]",
        "disconnected": "[red]~[/red]",
        "degraded": "[yellow]~[/yellow]",
        "paused": "[yellow]~[/yellow]",
        "error": "[red]![/red]",
        "unknown": "[dim]?[/dim]",
    }
    return mapping.get(status_str.lower(), status_str)


def _report_to_json(report: RuntimeReport) -> str:
    data = {
        "runtime_status": report.runtime_status.name.lower(),
        "uptime_seconds": getattr(report, "uptime_seconds", getattr(report.performance, "uptime_seconds", 0.0)),
        "broker_status": getattr(report, "broker_status", getattr(report.broker, "connection", "unknown")),
        "stream_status": getattr(report, "stream_status", getattr(report.market, "stream_status", "unknown")),
        "scheduler_active": getattr(report, "scheduler_active", getattr(report.scheduler, "active", False)),
        "pipeline_executions": getattr(report, "pipeline_executions", getattr(report.scheduler, "pipeline_executions", 0)),
        "warnings": list(getattr(report, "warnings", getattr(report.health, "warnings", []))),
        "errors": list(getattr(report, "errors", getattr(report.health, "errors", []))),
    }
    
    # Handle enum values if they leaked through
    if hasattr(data["broker_status"], "value"):
        data["broker_status"] = data["broker_status"].value
        
    return str(json.dumps(data, indent=2))


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


def _get_transport():
    from titan.cli.common import _runtime_engine
    if _runtime_engine is not None:
        from titan.runtime.service import RuntimeService
        from titan.runtime.transport import InProcessTransport
        return InProcessTransport(RuntimeService(_runtime_engine))
    from titan.runtime.local_transport import LocalTransport
    return LocalTransport()


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed status")
    ] = False,
) -> None:
    """Show runtime engine status."""
    logger.info("Runtime status command executed")
    from titan.runtime.exceptions import RuntimeError as TitanRuntimeError

    transport = _get_transport()
    try:
        report = transport.status()
    except TitanRuntimeError:
        # Not running
        if json_output:
            console.print('{"status": "stopped"}')
        else:
            console.print("[red]~[/red] Runtime is STOPPED or unreachable.")
        return

    if json_output:
        console.print(_report_to_json(report))
        return

    status_val = report.runtime_status.name.lower()
    status_display = f"{_status_icon(status_val)} {status_val}"

    table = Table(title="Runtime Engine", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Status", status_display)
    table.add_row("Uptime", _format_uptime(report.performance.uptime_seconds))

    broker_display = f"{_status_icon(report.broker.connection.value)} {report.broker.connection.value}"
    table.add_row("Broker", broker_display)

    stream_display = (
        f"{_status_icon(report.market.stream_status)} {report.market.stream_status}"
    )
    table.add_row("Stream", stream_display)

    sched_display = f"{_status_icon('running' if report.scheduler.active else 'stopped')} {'active' if report.scheduler.active else 'inactive'}"
    table.add_row("Scheduler", sched_display)
    table.add_row("Pipeline Executions", str(report.scheduler.pipeline_executions))
    table.add_row("Active Subscriptions", str(report.market.active_subscriptions))

    if report.scheduler.last_pipeline_time:
        table.add_row("Last Pipeline", report.scheduler.last_pipeline_time.isoformat())
    if report.market.last_quote_time:
        table.add_row("Last Quote", report.market.last_quote_time.isoformat())

    console.print(table)

    if report.health.warnings:
        console.print()
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for w in report.health.warnings:
            console.print(f"  [yellow]~[/yellow] {w}")

    if report.health.errors:
        console.print()
        console.print("[bold red]Errors:[/bold red]")
        for e in report.health.errors:
            console.print(f"  [red]![/red] {e}")

    if verbose:
        console.print()
        _print_component_health(report)
        _print_monitoring_summary()
        _print_recovery_summary()


def _print_component_health(report: object) -> None:
    if not hasattr(report, "health") or not hasattr(report.health, "component_health"):
        return
    health = getattr(report.health, "component_health", ())
    if not health:
        return
    table = Table(title="Component Health", show_header=True, header_style="bold")
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Latency")
    table.add_column("Error")
    for ch in health:
        s = ch.status.value if hasattr(ch, "status") else str(ch.status)
        icon = _status_icon(s)
        err = ch.error if ch.error else ""
        lat = f"{ch.latency_ms:.1f}ms" if ch.latency_ms else "-"
        table.add_row(ch.component_name, f"{icon} {s}", lat, err)
    console.print(table)


def _print_monitoring_summary() -> None:
    try:
        manager = get_monitoring_manager()
        report = manager.generate_report()
        table = Table(
            title="Monitoring Summary", show_header=False, box=None, padding=(0, 2)
        )
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Collectors", str(report.collector_count))
        table.add_row("Total Collections", str(report.total_collections))
        table.add_row("Failed", str(report.failed_collections))
        table.add_row("Uptime", f"{report.uptime_seconds:,.0f}s")
        console.print(table)
    except (RuntimeError, ConnectionError, AttributeError, OSError, TitanRuntimeError) as e:
        logger.debug(f"Fetch failed: {e}")


def _print_recovery_summary() -> None:
    try:
        mgr = get_recovery_manager()
        report = mgr.generate_report()
        table = Table(
            title="Recovery Summary", show_header=False, box=None, padding=(0, 2)
        )
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row(
            "Status", report.status.value if hasattr(report, "status") else "unknown"
        )
        table.add_row("Total Attempts", str(getattr(report, "total_attempts", 0)))
        table.add_row("Successful", str(getattr(report, "successful_attempts", 0)))
        table.add_row("Failed", str(getattr(report, "failed_attempts", 0)))
        console.print(table)
    except (RuntimeError, ConnectionError, AttributeError, OSError, TitanRuntimeError) as e:
        logger.debug(f"Fetch failed: {e}")


@app.command("start")
def start(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show startup progress")
    ] = False,
    detach: Annotated[
        bool, typer.Option("--detach", "-d", help="Run in background")
    ] = False,
) -> None:
    """Start the runtime engine."""
    logger.info("Runtime start command executed")

    # Check if already running
    transport_client = _get_transport()
    try:
        transport_client.status()
        console.print("[yellow]~[/yellow] Runtime is already running.")
        return
    except (RuntimeError, ConnectionError, AttributeError, OSError, TitanRuntimeError) as e:
        logger.debug(f"Fetch failed: {e}")

    if detach:
        console.print("[dim]Starting runtime in detached mode...[/dim]")
        import subprocess
        import sys

        titan_exe = [sys.executable, "-m", "titan", "runtime", "start"]
        if verbose:
            titan_exe.append("--verbose")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )

        log_out = open("runtime_daemon.log", "a")

        subprocess.Popen(
            titan_exe,
            stdin=subprocess.DEVNULL,
            stdout=log_out,
            stderr=log_out,
            close_fds=True,
            creationflags=creationflags,
        )
        console.print("[bold green]+[/bold green] Runtime started in background.")
        return

    engine = get_runtime_engine()
    service = RuntimeService(engine)
    
    from titan.cli.common import _runtime_engine
    server = None
    if _runtime_engine is None:
        from titan.runtime.local_transport import LocalTransportServer
        server = LocalTransportServer(service)
        server.start()

    try:
        if verbose:
            _start_with_progress(engine)
        else:
            console.print("[bold green]+[/bold green] Runtime started.")
            engine.start()  # blocks
    except TitanRuntimeError as e:
        console.print(f"[bold red]![/bold red] Failed to start runtime: {e}")
        if server:
            server.stop()
        raise typer.Exit(code=3)
    except Exception as e:
        console.print(f"[bold red]![/bold red] Unexpected error: {e}")
        if server:
            server.stop()
        raise typer.Exit(code=3)

    if server:
        server.stop()


def _start_with_progress(engine: RuntimeEngine) -> None:
    steps = [
        ("Initializing", lambda: None),
        ("Connecting broker", lambda: getattr(engine, "start", lambda: None)()),
    ]

    with Live(console=console, refresh_per_second=4) as live:
        for i, (step_name, _) in enumerate(steps):
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for j, (name, _) in enumerate(steps):
                if j < i:
                    table.add_row(name, "[green]+[/green] done")
                elif j == i:
                    table.add_row(name, "[yellow]...[/yellow]")
                else:
                    table.add_row(name, "[dim]-[/dim]")
            live.update(table)
            time.sleep(0.3)

        try:
            engine.start()
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for name, _ in steps:
                table.add_row(name, "[green]+[/green] done")
            table.add_row("Runtime started", "[bold green]+[/bold green]")
            live.update(table)
        except TitanRuntimeError as e:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for j, (name, _) in enumerate(steps):
                if j < i:
                    table.add_row(name, "[green]+[/green] done")
                else:
                    table.add_row(name, "[red]![/red] failed")
            table.add_row(f"Error: {e}", "[bold red]![/bold red]")
            live.update(table)
            raise typer.Exit(code=3)
        except Exception as e:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for j, (name, _) in enumerate(steps):
                if j < i:
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
    """Stop the runtime engine gracefully."""
    logger.info("Runtime stop command executed")

    from titan.runtime.exceptions import RuntimeError as TitanRuntimeError

    transport = _get_transport()
    try:
        transport.stop()
        console.print("[bold yellow]~[/bold yellow] Runtime stopped.")
    except TitanRuntimeError as e:
        if "connection refused" in str(e).lower():
            console.print("[dim]Runtime is already stopped.[/dim]")
        else:
            console.print(f"[bold red]![/bold red] Error stopping runtime: {e}")
            raise typer.Exit(code=3)


def _stop_with_progress(engine: RuntimeEngine) -> None:
    steps = [
        "Stopping heartbeat",
        "Stopping scheduler",
        "Stopping stream",
        "Disconnecting broker",
        "Runtime stopped",
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
            time.sleep(0.2)

        try:
            engine.stop()
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for name in steps:
                table.add_row(name, "[green]+[/green] done")
            live.update(table)
        except Exception as e:
            console.print(f"[bold red]![/bold red] Error during shutdown: {e}")
            raise typer.Exit(code=3)


@app.command("restart")
def restart(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show restart progress")
    ] = False,
) -> None:
    """Restart the runtime engine (stop then start)."""
    logger.info("Runtime restart command executed")
    engine = get_runtime_engine()
    service = RuntimeService(engine)
    transport = InProcessTransport(service)

    if engine.status == RuntimeStatus.STOPPED:
        console.print("[dim]Runtime is stopped. Starting...[/dim]")
    else:
        if verbose:
            console.print("[yellow]~[/yellow] Stopping runtime...")
        try:
            transport.stop()
        except Exception as e:
            console.print(f"[bold red]![/bold red] Error stopping: {e}")
            raise typer.Exit(code=3)

    try:
        if verbose:
            console.print("[green]+[/green] Starting runtime...")
        transport.start()
        console.print("[bold green]+[/bold green] Runtime restarted.")
    except TitanRuntimeError as e:
        console.print(f"[bold red]![/bold red] Failed to restart: {e}")
        raise typer.Exit(code=3)
    except Exception as e:
        console.print(f"[bold red]![/bold red] Unexpected error: {e}")
        raise typer.Exit(code=3)


@app.command("version")
def version(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed version info")
    ] = False,
) -> None:
    """Display TITAN version information."""
    settings = get_settings()
    logger.info("Version command executed")

    text = Text()
    text.append(f"{settings.app_name}\n", style="bold cyan")
    text.append("Institutional Trading Intelligence System\n")
    text.append(f"Version : {settings.app_version}\n")
    text.append(f"Status  : {settings.environment}")

    if verbose:
        from titan.deployment.version import VersionManager

        vm = VersionManager.instance()
        info = vm.get()
        if info.build_number:
            text.append(f"\nBuild   : {info.build_number}")
        if info.git_commit:
            text.append(f"\nGit     : {info.git_commit[:8]}")
        if info.python_version:
            text.append(f"\nPython  : {info.python_version}")
        if info.platform:
            text.append(f"\nOS      : {info.platform}")

    console.print(Panel(text, title="TITAN", expand=False))

"""titan monitor - Monitoring subsystem commands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Any

import typer
from rich.table import Table

from titan.cli.common import console, get_monitoring_manager, logger

monitor_app = typer.Typer(help="Monitoring subsystem management.")
app = monitor_app


# ── Session State ──────────────────────────────────────────

_monitor_running: bool = False
_monitor_start_time: datetime | None = None


def _reset_monitor_session() -> None:
    """Reset monitor session state (for testing)."""
    global _monitor_running, _monitor_start_time
    _monitor_running = False
    _monitor_start_time = None


def _is_running() -> bool:
    return _monitor_running


def _format_duration(seconds: float) -> str:
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


def _json_serial(obj: object) -> str:
    if hasattr(obj, "isoformat"):
        return str(obj.isoformat())
    if hasattr(obj, "value"):
        return str(obj.value)
    return str(obj)


def _health_icon(status_str: str) -> str:
    mapping = {
        "healthy": "[green]+[/green]",
        "warning": "[yellow]~[/yellow]",
        "critical": "[red]![/red]",
        "offline": "[red]x[/red]",
    }
    return mapping.get(status_str.lower(), status_str)


def _trend_icon(trend: str) -> str:
    mapping = {
        "increasing": "[green]^[/green]",
        "decreasing": "[red]v[/red]",
        "stable": "[dim]-[/dim]",
    }
    return mapping.get(trend, trend)


# ── Commands ──────────────────────────────────────────────


@app.command("start")
def start(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show startup progress")
    ] = False,
) -> None:
    """Start the monitoring subsystem."""
    global _monitor_running, _monitor_start_time

    logger.info("Monitor start command executed")

    if _is_running():
        console.print("[yellow]~[/yellow] Monitoring is already running.")
        return

    try:
        manager = get_monitoring_manager()
        manager.start()
        _monitor_running = True
        _monitor_start_time = datetime.now(timezone.utc)
        console.print("[bold green]+[/bold green] Monitoring subsystem started.")
    except Exception as e:
        console.print(f"[bold red]![/bold red] Failed to start monitoring: {e}")
        raise typer.Exit(code=3)

    if verbose:
        report = manager.generate_report()
        console.print(f"  Collectors: {report.collector_count}")
        console.print(f"  Subsystems registered: {len(manager.health.all_health())}")


@app.command("stop")
def stop(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show shutdown progress")
    ] = False,
) -> None:
    """Stop the monitoring subsystem."""
    global _monitor_running, _monitor_start_time

    logger.info("Monitor stop command executed")

    if not _is_running():
        console.print("[dim]Monitoring is not running.[/dim]")
        return

    try:
        manager = get_monitoring_manager()
        manager.stop()
    except Exception:
        pass

    _monitor_running = False
    _monitor_start_time = None
    console.print("[bold yellow]~[/bold yellow] Monitoring subsystem stopped.")


@app.command("restart")
def restart(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show restart progress")
    ] = False,
) -> None:
    """Restart the monitoring subsystem."""
    logger.info("Monitor restart command executed")

    if _is_running():
        if verbose:
            console.print("[yellow]~[/yellow] Stopping current session...")
        stop(verbose=verbose)

    if verbose:
        console.print("[green]+[/green] Starting new session...")

    start(verbose=verbose)


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed status")
    ] = False,
) -> None:
    """Show monitoring subsystem status."""
    logger.info("Monitor status command executed")

    manager = get_monitoring_manager()
    report = manager.generate_report()

    if json_output:
        data: dict[str, Any] = {
            "running": _is_running(),
            "uptime_seconds": report.uptime_seconds,
            "collector_count": report.collector_count,
            "total_collections": report.total_collections,
            "failed_collections": report.failed_collections,
            "warnings": list(report.warnings),
            "recommendations": list(report.recommendations),
        }
        if report.system_health is not None:
            sh = report.system_health
            data["health"] = {
                "overall": sh.overall.value,
                "healthy_count": sh.healthy_count,
                "warning_count": sh.warning_count,
                "critical_count": sh.critical_count,
                "offline_count": sh.offline_count,
                "subsystems": [
                    {
                        "subsystem": s.subsystem.value,
                        "status": s.status.value,
                        "message": s.message,
                        "latency_ms": s.latency_ms,
                        "failures": s.failures,
                    }
                    for s in sh.subsystems
                ],
            }
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    table = Table(
        title="Monitoring Subsystem", show_header=False, box=None, padding=(0, 2)
    )
    table.add_column("Key", style="bold")
    table.add_column("Value")

    running_str = (
        "[green]+ running[/green]" if _is_running() else "[dim]not running[/dim]"
    )
    table.add_row("Status", running_str)

    if _monitor_start_time is not None and _is_running():
        elapsed = (datetime.now(timezone.utc) - _monitor_start_time).total_seconds()
        table.add_row("Session Uptime", _format_duration(elapsed))

    table.add_row("Total Uptime", _format_duration(report.uptime_seconds))
    table.add_row("Collectors", str(report.collector_count))
    table.add_row("Total Collections", str(report.total_collections))
    table.add_row("Failed Collections", str(report.failed_collections))

    if report.system_health is not None:
        sh = report.system_health
        table.add_row("Health", f"{_health_icon(sh.overall.value)} {sh.overall.value}")
        table.add_row(
            "Subsystems",
            f"{sh.healthy_count} healthy, {sh.warning_count} warning, "
            f"{sh.critical_count} critical, {sh.offline_count} offline",
        )
    else:
        table.add_row("Health", "[dim]No data[/dim]")

    table.add_row("Warnings", str(len(report.warnings)))
    console.print(table)

    if verbose:
        _print_health_details(manager)


@app.command("metrics")
def metrics(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show collected metrics by category."""
    logger.info("Monitor metrics command executed")

    manager = get_monitoring_manager()
    snapshot = manager.collect_snapshot()

    latest = manager.metrics.latest_values()

    if json_output:
        data = {
            "metric_count": len(latest),
            "metrics": {name: {"value": val} for name, val in sorted(latest.items())},
            "snapshot_timestamp": snapshot.timestamp.isoformat(),
        }
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    if not latest:
        console.print("[dim]No metrics collected yet.[/dim]")
        return

    categories: dict[str, list[tuple[str, float]]] = {
        "CPU": [],
        "Memory": [],
        "Runtime": [],
        "Pipeline": [],
        "Event Bus": [],
        "Scheduler": [],
        "Broker": [],
        "Stream": [],
        "Recovery": [],
        "Alerting": [],
        "Other": [],
    }

    category_keywords = {
        "CPU": ["cpu"],
        "Memory": ["memory", "mem", "rss", "heap"],
        "Runtime": ["runtime", "uptime", "thread", "process"],
        "Pipeline": ["pipeline", "stage", "decision"],
        "Event Bus": ["event", "bus", "listener"],
        "Scheduler": ["scheduler", "schedule", "cron"],
        "Broker": ["broker", "connection", "session"],
        "Stream": ["stream", "feed", "market_data"],
        "Recovery": ["recovery", "retry", "circuit"],
        "Alerting": ["alert", "notification", "channel"],
    }

    for name, val in latest.items():
        placed = False
        name_lower = name.lower()
        for cat, keywords in category_keywords.items():
            if any(kw in name_lower for kw in keywords):
                categories[cat].append((name, val))
                placed = True
                break
        if not placed:
            categories["Other"].append((name, val))

    for cat_name, cat_metrics in categories.items():
        if not cat_metrics:
            continue
        table = Table(title=cat_name, show_header=True, header_style="bold")
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        for metric_name, metric_val in sorted(cat_metrics):
            table.add_row(metric_name, f"{metric_val:.4f}")
        console.print(table)


@app.command("dashboard")
def dashboard(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show full details")
    ] = False,
) -> None:
    """Show monitoring dashboard."""
    logger.info("Monitor dashboard command executed")

    manager = get_monitoring_manager()
    dash_status = manager.dashboard_status()

    if json_output:
        data: dict[str, Any] = {
            "uptime_seconds": dash_status.uptime_seconds,
            "active_collectors": dash_status.active_collectors,
            "total_collections": dash_status.total_collections,
            "failed_collections": dash_status.failed_collections,
            "recent_failures": list(dash_status.recent_failures),
            "metric_summaries": [
                {
                    "name": s.name,
                    "current": s.current,
                    "min": s.min,
                    "max": s.max,
                    "avg": s.avg,
                    "unit": s.unit.value,
                    "trend": s.trend,
                }
                for s in dash_status.metric_summaries
            ],
        }
        if dash_status.system_health is not None:
            sh = dash_status.system_health
            data["health"] = {
                "overall": sh.overall.value,
                "healthy_count": sh.healthy_count,
                "warning_count": sh.warning_count,
                "critical_count": sh.critical_count,
                "offline_count": sh.offline_count,
            }
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    if dash_status.system_health is not None:
        sh = dash_status.system_health
        health_table = Table(
            title="System Health", show_header=False, box=None, padding=(0, 2)
        )
        health_table.add_column("Key", style="bold")
        health_table.add_column("Value")
        health_table.add_row(
            "Overall", f"{_health_icon(sh.overall.value)} {sh.overall.value}"
        )
        health_table.add_row("Healthy", str(sh.healthy_count))
        health_table.add_row("Warning", str(sh.warning_count))
        health_table.add_row("Critical", str(sh.critical_count))
        health_table.add_row("Offline", str(sh.offline_count))
        health_table.add_row("Active Collectors", str(dash_status.active_collectors))
        health_table.add_row("Uptime", _format_duration(dash_status.uptime_seconds))
        console.print(health_table)

    if dash_status.metric_summaries:
        metric_table = Table(
            title="Metric Summaries", show_header=True, header_style="bold"
        )
        metric_table.add_column("Metric", style="bold")
        metric_table.add_column("Current")
        metric_table.add_column("Min")
        metric_table.add_column("Max")
        metric_table.add_column("Avg")
        metric_table.add_column("Trend")

        for s in dash_status.metric_summaries:
            metric_table.add_row(
                s.name,
                f"{s.current:.4f}",
                f"{s.min:.4f}",
                f"{s.max:.4f}",
                f"{s.avg:.4f}",
                f"{_trend_icon(s.trend)} {s.trend}",
            )
        console.print(metric_table)

    if dash_status.recent_failures:
        fail_table = Table(
            title="Recent Failures", show_header=True, header_style="bold"
        )
        fail_table.add_column("#", style="dim")
        fail_table.add_column("Failure")
        for i, f in enumerate(dash_status.recent_failures, 1):
            fail_table.add_row(str(i), f)
        console.print(fail_table)

    if verbose:
        _print_health_details(manager)


# ── Helpers ────────────────────────────────────────────────


def _print_health_details(manager: Any) -> None:
    """Print per-subsystem health details."""
    health_data = manager.health.all_health()
    if not health_data:
        return

    table = Table(title="Subsystem Health", show_header=True, header_style="bold")
    table.add_column("Subsystem")
    table.add_column("Status")
    table.add_column("Message")
    table.add_column("Latency")
    table.add_column("Failures")

    for sh in health_data:
        table.add_row(
            sh.subsystem.value,
            f"{_health_icon(sh.status.value)} {sh.status.value}",
            sh.message or "-",
            f"{sh.latency_ms:.1f}ms" if sh.latency_ms > 0 else "-",
            str(sh.failures) if sh.failures > 0 else "0",
        )
    console.print(table)

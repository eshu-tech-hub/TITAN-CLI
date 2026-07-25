"""titan alert - Alerting subsystem commands."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.table import Table

from titan.cli.common import console, get_alert_manager, logger

alert_app = typer.Typer(help="Alerting subsystem management.")
app = alert_app


# ── Helpers ────────────────────────────────────────────────


def _get_alert_manager() -> Any:
    return get_alert_manager()


def _level_icon(level_str: str) -> str:
    mapping = {
        "info": "[cyan]i[/cyan]",
        "warning": "[yellow]~[/yellow]",
        "error": "[red]![/red]",
        "critical": "[bold red]!![/bold red]",
        "emergency": "[bold red]!!![/bold red]",
    }
    return mapping.get(level_str.lower(), level_str)


def _status_icon(status_str: str) -> str:
    mapping = {
        "new": "[red]*[/red]",
        "acknowledged": "[yellow]~[/yellow]",
        "resolved": "[green]+[/green]",
        "suppressed": "[dim]-[/dim]",
        "escalated": "[bold red]![/bold red]",
    }
    return mapping.get(status_str.lower(), status_str)


def _json_serial(obj: object) -> str:
    if hasattr(obj, "isoformat"):
        return str(obj.isoformat())
    if hasattr(obj, "value"):
        return str(obj.value)
    if isinstance(obj, dict):
        return str(obj)
    return str(obj)


def _alert_to_dict(alert: Any) -> dict[str, Any]:
    return {
        "alert_id": alert.alert_id,
        "level": alert.level.value,
        "source": alert.source.value,
        "title": alert.title,
        "message": alert.message,
        "timestamp": alert.timestamp.isoformat(),
        "status": alert.status.value,
        "acknowledged_at": (
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        ),
        "acknowledged_by": alert.acknowledged_by or None,
        "resolved_at": (alert.resolved_at.isoformat() if alert.resolved_at else None),
        "resolved_by": alert.resolved_by or None,
        "rule_name": alert.rule_name or None,
        "tags": list(alert.tags),
    }


def _report_to_dict(report: Any) -> dict[str, Any]:
    return {
        "total_alerts": report.total_alerts,
        "active_alerts": report.active_alerts,
        "critical_alerts": report.critical_alerts,
        "acknowledged_alerts": report.acknowledged_alerts,
        "resolved_alerts": report.resolved_alerts,
        "suppressed_alerts": report.suppressed_alerts,
        "escalated_alerts": report.escalated_alerts,
        "alerts_by_source": dict(report.alerts_by_source),
        "alerts_by_level": dict(report.alerts_by_level),
        "warnings": list(report.warnings),
        "timestamp": report.timestamp.isoformat(),
    }


# ── Commands ──────────────────────────────────────────────


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed status")
    ] = False,
) -> None:
    """Show alerting subsystem status."""
    logger.info("Alert status command executed")

    manager = _get_alert_manager()
    report = manager.generate_report()
    channels = manager.channels.registered_channels()

    if json_output:
        data: dict[str, Any] = {
            "report": _report_to_dict(report),
            "channels": [c.value for c in channels],
            "active_count": report.active_alerts,
        }
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    table = Table(
        title="Alerting Subsystem", show_header=False, box=None, padding=(0, 2)
    )
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Total Alerts", str(report.total_alerts))
    table.add_row("Active Alerts", str(report.active_alerts))
    table.add_row("Critical Alerts", str(report.critical_alerts))
    table.add_row("Acknowledged", str(report.acknowledged_alerts))
    table.add_row("Resolved", str(report.resolved_alerts))
    table.add_row("Suppressed", str(report.suppressed_alerts))
    table.add_row("Escalated", str(report.escalated_alerts))
    table.add_row("Channels", ", ".join(c.value for c in channels) or "none")
    console.print(table)

    if verbose:
        if report.alerts_by_level:
            level_table = Table(
                title="Alerts by Level", show_header=True, header_style="bold"
            )
            level_table.add_column("Level")
            level_table.add_column("Count")
            for level, count in sorted(report.alerts_by_level.items()):
                level_table.add_row(f"{_level_icon(level)} {level}", str(count))
            console.print(level_table)

        if report.alerts_by_source:
            src_table = Table(
                title="Alerts by Source", show_header=True, header_style="bold"
            )
            src_table.add_column("Source")
            src_table.add_column("Count")
            for source, count in sorted(report.alerts_by_source.items()):
                src_table.add_row(source, str(count))
            console.print(src_table)

        if report.warnings:
            warn_table = Table(title="Warnings", show_header=True, header_style="bold")
            warn_table.add_column("#", style="dim")
            warn_table.add_column("Warning")
            for i, w in enumerate(report.warnings, 1):
                warn_table.add_row(str(i), w)
            console.print(warn_table)


@app.command("active")
def active(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show active (unresolved) alerts."""
    logger.info("Alert active command executed")

    manager = _get_alert_manager()
    alerts = manager.get_active_alerts()

    if json_output:
        data = {
            "active_alerts": [_alert_to_dict(a) for a in alerts],
            "count": len(alerts),
        }
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    if not alerts:
        console.print("[dim]No active alerts.[/dim]")
        return

    table = Table(title="Active Alerts", show_header=True, header_style="bold")
    table.add_column("ID", style="bold")
    table.add_column("Level")
    table.add_column("Source")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Time")

    for a in alerts:
        table.add_row(
            a.alert_id,
            f"{_level_icon(a.level.value)} {a.level.value}",
            a.source.value,
            a.title,
            f"{_status_icon(a.status.value)} {a.status.value}",
            a.timestamp.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)
    console.print(f"  {len(alerts)} active alert(s)")


@app.command("history")
def history(
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Max entries to show")
    ] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show alert history."""
    logger.info("Alert history command executed")

    manager = _get_alert_manager()
    all_alerts = manager.history.all_alerts()
    recent = all_alerts[-limit:] if len(all_alerts) > limit else all_alerts

    if json_output:
        data = {
            "alerts": [_alert_to_dict(a) for a in recent],
            "total_count": len(all_alerts),
            "shown_count": len(recent),
        }
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    if not recent:
        console.print("[dim]No alert history.[/dim]")
        return

    table = Table(
        title=f"Alert History (last {len(recent)})",
        show_header=True,
        header_style="bold",
    )
    table.add_column("ID", style="bold")
    table.add_column("Level")
    table.add_column("Source")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Time")

    for a in recent:
        table.add_row(
            a.alert_id,
            f"{_level_icon(a.level.value)} {a.level.value}",
            a.source.value,
            a.title,
            f"{_status_icon(a.status.value)} {a.status.value}",
            a.timestamp.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)
    console.print(f"  {len(all_alerts)} total, showing {len(recent)}")


@app.command("acknowledge")
def acknowledge(
    alert_id: Annotated[str, typer.Argument(help="Alert ID to acknowledge")],
    by: Annotated[str, typer.Option("--by", help="Acknowledged by")] = "",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Acknowledge an active alert."""
    logger.info("Alert acknowledge command executed")

    manager = _get_alert_manager()

    existing = manager.get_alert(alert_id)
    if existing is None:
        console.print(f"[bold red]![/bold red] Alert not found: {alert_id}")
        raise typer.Exit(code=1)

    if existing.status.value in ("resolved", "suppressed"):
        console.print(
            f"[yellow]~[/yellow] Alert {alert_id} is already {existing.status.value}."
        )
        return

    try:
        manager.acknowledge(alert_id, acknowledged_by=by)
    except Exception as e:
        console.print(f"[bold red]![/bold red] Failed to acknowledge: {e}")
        raise typer.Exit(code=3)

    if json_output:
        updated = manager.get_alert(alert_id)
        if updated is not None:
            console.print(
                json.dumps(_alert_to_dict(updated), indent=2, default=_json_serial)
            )
        return

    console.print(f"[bold green]+[/bold green] Alert {alert_id} acknowledged.")


@app.command("resolve")
def resolve(
    alert_id: Annotated[str, typer.Argument(help="Alert ID to resolve")],
    by: Annotated[str, typer.Option("--by", help="Resolved by")] = "",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Resolve an active alert."""
    logger.info("Alert resolve command executed")

    manager = _get_alert_manager()

    existing = manager.get_alert(alert_id)
    if existing is None:
        console.print(f"[bold red]![/bold red] Alert not found: {alert_id}")
        raise typer.Exit(code=1)

    if existing.status.value == "resolved":
        console.print(f"[yellow]~[/yellow] Alert {alert_id} is already resolved.")
        return

    try:
        manager.resolve(alert_id, resolved_by=by)
    except Exception as e:
        console.print(f"[bold red]![/bold red] Failed to resolve: {e}")
        raise typer.Exit(code=3)

    if json_output:
        updated = manager.get_alert(alert_id)
        if updated is not None:
            console.print(
                json.dumps(_alert_to_dict(updated), indent=2, default=_json_serial)
            )
        return

    console.print(f"[bold green]+[/bold green] Alert {alert_id} resolved.")


@app.command("rules")
def rules(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show registered alert rules."""
    logger.info("Alert rules command executed")

    manager = _get_alert_manager()
    rule_names = manager.rules.rule_names()

    if json_output:
        data = {
            "rules": list(rule_names),
            "count": len(rule_names),
        }
        console.print(json.dumps(data, indent=2, default=_json_serial))
        return

    if not rule_names:
        console.print("[dim]No alert rules registered.[/dim]")
        return

    table = Table(title="Alert Rules", show_header=True, header_style="bold")
    table.add_column("Rule", style="bold")
    for name in rule_names:
        table.add_row(name)
    console.print(table)
    console.print(f"  {len(rule_names)} rule(s) registered")

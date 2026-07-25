"""titan deployment - Deployment lifecycle commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from titan.cli.common import console, get_deployment_manager, logger

deployment_app = typer.Typer(help="Deployment lifecycle management.")
app = deployment_app


def _clean_enum(val: object) -> str:
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Detailed output")
    ] = False,
) -> None:
    """Show deployment status."""
    logger.info("Deployment status command executed")
    dm = get_deployment_manager()
    report = dm.generate_report()

    if json_output:
        data = {
            "status": _clean_enum(report.status),
            "environment": _clean_enum(report.environment),
            "version": report.version.version,
            "uptime_seconds": report.uptime_seconds,
        }
        console.print(json.dumps(data))
        return

    table = Table(title="Deployment", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    status_val = report.status.value
    if status_val == "running":
        status_display = f"[green]{status_val}[/green]"
    elif status_val in ("starting", "stopped"):
        status_display = f"[yellow]{status_val}[/yellow]"
    else:
        status_display = f"[red]{status_val}[/red]"
    table.add_row("Status", status_display)
    table.add_row("Version", report.version.version)
    table.add_row("Environment", report.environment.value)
    table.add_row("Uptime", f"{report.uptime_seconds:,.0f}s")
    console.print(table)

    if verbose:
        health = dm.health().generate_report()
        htable = Table(
            title="Health Probes", show_header=False, box=None, padding=(0, 2)
        )
        htable.add_column("Key", style="bold")
        htable.add_column("Value")
        htable.add_row("Readiness", str(health.readiness))
        htable.add_row("Liveness", str(health.liveness))
        htable.add_row("Startup Complete", str(health.startup_complete))
        console.print(htable)


@app.command("start")
def start() -> None:
    """Start the deployment."""
    logger.info("Deployment start command executed")
    dm = get_deployment_manager()
    dm.start()
    console.print("[bold green]+[/bold green] Deployment started.")


@app.command("stop")
def stop() -> None:
    """Stop the deployment."""
    logger.info("Deployment stop command executed")
    dm = get_deployment_manager()
    dm.stop()
    console.print("[bold yellow]~[/bold yellow] Deployment stopped.")


@app.command("backup")
def backup(
    destination: Annotated[
        str, typer.Option("--dest", help="Backup destination directory")
    ] = "backups",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Create a deployment backup."""
    logger.info("Deployment backup command executed")
    dm = get_deployment_manager()
    manifest = dm.backup(destination)

    if json_output:
        data = {
            "backup_id": manifest.backup_id,
            "destination": manifest.destination,
            "components": list(manifest.components),
            "total_files": manifest.total_files,
            "success": manifest.success,
            "errors": list(manifest.errors),
        }
        console.print(json.dumps(data))
        return

    console.print(f"[bold green]+[/bold green] Backup created: {manifest.destination}")
    console.print(f"  Components: {', '.join(manifest.components) or 'none'}")
    console.print(f"  Files: {manifest.total_files}")


@app.command("restore")
def restore(
    backup_id: Annotated[str, typer.Argument(help="Backup ID to restore from")],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Restore from a deployment backup."""
    import shutil
    from pathlib import Path

    from titan.core.config import get_settings

    settings = get_settings()
    backups_dir = Path(settings.app_name.lower().replace(" ", "_")) / "backups"

    if not backups_dir.exists():
        if json_output:
            console.print(json.dumps({"error": "No backups directory found"}))
        else:
            console.print("[red]No backups directory found.[/red]")
        raise typer.Exit(1)

    backup_dir = backups_dir / backup_id
    if not backup_dir.exists():
        if json_output:
            console.print(json.dumps({"error": f"Backup not found: {backup_id}"}))
        else:
            console.print(f"[red]Backup not found: {backup_id}[/red]")
        raise typer.Exit(1)

    restored: list[str] = []
    errors: list[str] = []

    for dirname in ("data", "logs"):
        src = backup_dir / dirname
        if src.exists():
            try:
                dst = Path(dirname)
                if dst.exists():
                    shutil.rmtree(str(dst))
                shutil.copytree(str(src), str(dst))
                restored.append(dirname)
            except Exception as exc:
                errors.append(f"{dirname}: {exc}")

    for filename in (".env", ".env.example"):
        src = backup_dir / filename
        if src.exists():
            try:
                shutil.copy2(str(src), filename)
                restored.append(filename)
            except Exception as exc:
                errors.append(f"{filename}: {exc}")

    if json_output:
        console.print(
            json.dumps(
                {
                    "backup_id": backup_id,
                    "restored": restored,
                    "errors": errors,
                    "success": len(errors) == 0,
                }
            )
        )
    else:
        if errors:
            console.print(
                f"[bold yellow]~[/bold yellow] Restored with errors: {', '.join(errors)}"
            )
        else:
            console.print(
                f"[bold green]+[/bold green] Restored from backup: {backup_id}"
            )


@app.command("validate")
def validate(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Detailed output")
    ] = False,
) -> None:
    """Validate deployment environment."""
    dm = get_deployment_manager()
    report = dm.health().generate_report()

    if json_output:
        data = {
            "overall_status": _clean_enum(report.overall_status),
            "readiness": report.readiness,
            "liveness": report.liveness,
            "startup_complete": report.startup_complete,
            "subsystems": [
                {"name": s.name, "status": _clean_enum(s.status), "message": s.message}
                for s in report.subsystems
            ],
        }
        console.print(json.dumps(data))
        return

    status_val = _clean_enum(report.overall_status)
    console.print(f"Overall: [bold]{status_val}[/bold]")
    console.print(f"Readiness: {report.readiness}")
    console.print(f"Liveness: {report.liveness}")

    if verbose and report.subsystems:
        table = Table(title="Subsystems", show_header=True)
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Message")
        for s in report.subsystems:
            table.add_row(s.name, _clean_enum(s.status), s.message)
        console.print(table)


@app.command("health")
def health(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Detailed output")
    ] = False,
) -> None:
    """Show deployment health status."""
    dm = get_deployment_manager()
    report = dm.health().generate_report()

    if json_output:
        data = {
            "overall_status": _clean_enum(report.overall_status),
            "readiness": report.readiness,
            "liveness": report.liveness,
            "startup_complete": report.startup_complete,
            "uptime_seconds": report.uptime_seconds,
        }
        console.print(json.dumps(data))
        return

    table = Table(
        title="Deployment Health", show_header=False, box=None, padding=(0, 2)
    )
    table.add_column("Key", style="bold")
    table.add_column("Value")
    status_val = _clean_enum(report.overall_status)
    table.add_row("Overall", f"[bold]{status_val}[/bold]")
    table.add_row("Readiness", str(report.readiness))
    table.add_row("Liveness", str(report.liveness))
    table.add_row("Startup Complete", str(report.startup_complete))
    table.add_row("Uptime", f"{report.uptime_seconds:,.0f}s")
    console.print(table)

    if verbose and report.subsystems:
        stable = Table(title="Subsystems", show_header=True)
        stable.add_column("Name")
        stable.add_column("Status")
        stable.add_column("Latency")
        for s in report.subsystems:
            stable.add_row(s.name, _clean_enum(s.status), f"{s.latency_ms:.1f}ms")
        console.print(stable)

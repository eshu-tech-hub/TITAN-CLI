"""titan config - Configuration management commands."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.table import Table

from titan.cli.common import console, get_config_manager, logger

config_app = typer.Typer(help="Configuration management.")
app = config_app


@app.command("show")
def show(
    section: Annotated[
        str | None, typer.Argument(help="Config section to show (all if empty)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show current TITAN configuration."""
    logger.info("Config show command executed")
    manager = get_config_manager()
    config = manager.get_config()

    sections = {
        "app": {
            "Name": config.app.name,
            "Version": config.app.version,
            "Environment": config.app.environment,
            "Log Level": config.app.log_level,
            "Data Dir": config.app.data_dir,
            "Config Dir": config.app.config_dir,
        },
        "broker": {
            "Provider": config.broker.provider,
            "Connection Timeout": f"{config.broker.connection_timeout_seconds}s",
            "Max Retries": config.broker.max_retries,
            "Paper Cash": f"INR {config.broker.paper_initial_cash:,.2f}",
        },
        "runtime": {
            "Pipeline Interval": f"{config.runtime.pipeline_interval_seconds}s",
            "Heartbeat Interval": f"{config.runtime.heartbeat_interval_seconds}s",
            "Stream Enabled": config.runtime.stream_enabled,
            "Scheduler Enabled": config.runtime.scheduler_enabled,
            "Max Pipeline Executions": config.runtime.max_pipeline_executions,
        },
        "risk": {
            "Max Position Size": f"{config.risk.max_position_size:,.0f}",
            "Max Drawdown": f"{config.risk.max_drawdown_percent}%",
            "Max Daily Loss": f"{config.risk.max_daily_loss:,.0f}",
            "Max Leverage": f"{config.risk.max_leverage}x",
            "Stop Loss": f"{config.risk.stop_loss_percent}%",
        },
        "execution": {
            "Max Retries": config.execution.max_retries,
            "Retry Delay": f"{config.execution.retry_delay_seconds}s",
            "Order Timeout": f"{config.execution.order_timeout_seconds}s",
            "Slippage": f"{config.execution.default_slippage_percent}%",
        },
        "logging": {
            "Level": config.logging.level,
            "File": config.logging.file,
            "Max Size": f"{config.logging.max_size_mb}MB",
            "Backup Count": config.logging.backup_count,
        },
        "monitoring": {
            "Enabled": config.monitoring.enabled,
            "Collector Interval": f"{config.monitoring.collector_interval_seconds}s",
            "Prometheus": config.monitoring.prometheus_enabled,
            "Prometheus Port": config.monitoring.prometheus_port,
        },
    }

    if json_output:
        flat = {}
        for sec_name, data in sections.items():
            flat[sec_name] = data
        target = {section: flat.get(section, {})} if section else flat
        console.print(json.dumps(target))
        return

    target_sections = (
        sections if section is None else {section: sections.get(section, {})}
    )

    for name, data in target_sections.items():
        if not data:
            console.print(f"[yellow]Unknown section: {name}[/yellow]")
            continue
        table = Table(title=name.upper(), show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold")
        table.add_column("Value")
        if isinstance(data, dict):
            for k, v in data.items():
                table.add_row(k, str(v))
        console.print(table)
        console.print()


@app.command("validate")
def validate(
    strict: Annotated[bool, typer.Option("--strict", help="Fail on warnings")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show all findings")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Validate current configuration and environment against requirements."""
    from titan.config.validators import ConfigurationValidator
    import dataclasses

    manager = get_config_manager()
    validator = ConfigurationValidator(manager)
    report = validator.validate_all()

    if json_output:
        profile_name = "default"
        try:
            profile_name = manager.get_config().app.profile.value
        except Exception:
            pass
            
        data = {
            "validation_status": "valid" if report.is_valid else "invalid",
            "profile": profile_name,
            "errors": [dataclasses.asdict(e) for e in report.blocking_errors],
            "warnings": [dataclasses.asdict(w) for w in report.warnings],
        }
        console.print(json.dumps(data))
        if not report.is_valid or (strict and report.warnings):
            raise typer.Exit(code=1)
        return

    if report.is_valid and (not strict or not report.warnings):
        console.print(
            "[bold green]+[/bold green] Configuration and environment are valid."
        )
    else:
        console.print(
            "[bold red]![/bold red] Configuration validation failed or issues found."
        )

    if verbose or not report.is_valid:
        for e in report.blocking_errors:
            console.print(f"  [red]ERROR ({e.category}):[/red] {e.message}")
            if e.resolution:
                console.print(f"    [dim]Resolution: {e.resolution}[/dim]")
        for w in report.warnings:
            console.print(f"  [yellow]WARNING ({w.category}):[/yellow] {w.message}")
            if w.resolution:
                console.print(f"    [dim]Resolution: {w.resolution}[/dim]")

    if verbose:
        for r in report.recommendations:
            console.print(f"  [blue]INFO ({r.category}):[/blue] {r.message}")
            if r.resolution:
                console.print(f"    [dim]Resolution: {r.resolution}[/dim]")

    if not report.is_valid or (strict and report.warnings):
        raise typer.Exit(code=1)


@app.command("diff")
def diff(
    profile: Annotated[
        str, typer.Option("--profile", "-p", help="Profile to compare against")
    ] = "development",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Compare current config against a profile's defaults."""
    from titan.config.profiles import profile_defaults

    manager = get_config_manager()
    current = manager.get_config()

    try:
        profile_data = profile_defaults(profile)
    except ValueError as exc:
        if json_output:
            console.print(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    current_dict: dict[str, dict[str, Any]] = {
        "app": {"log_level": current.app.log_level},
        "broker": {"provider": current.broker.provider},
        "runtime": {
            "pipeline_interval_seconds": current.runtime.pipeline_interval_seconds
        },
    }

    diffs: list[dict[str, str]] = []
    for section, values in profile_data.items():
        if isinstance(values, dict):
            section_data: dict[str, Any] = current_dict.get(section, {})
            for key, val in values.items():
                current_val = section_data.get(key)
                if current_val != val:
                    diffs.append(
                        {
                            "section": section,
                            "key": key,
                            "current": str(current_val),
                            "profile": str(val),
                        }
                    )

    if json_output:
        console.print(json.dumps({"profile": profile, "diffs": diffs}))
        return

    if not diffs:
        console.print(f"[green]No differences from profile '{profile}'.[/green]")
        return

    table = Table(title=f"Config Diff vs '{profile}'", show_header=True)
    table.add_column("Section")
    table.add_column("Key")
    table.add_column("Current")
    table.add_column("Profile")
    for d in diffs:
        table.add_row(d["section"], d["key"], d["current"], d["profile"])
    console.print(table)


@app.command("export")
def export(
    output: Annotated[
        str, typer.Option("--output", "-o", help="Export file path")
    ] = "config_export.json",
    fmt: Annotated[
        str, typer.Option("--format", help="Export format: json or yaml")
    ] = "json",
) -> None:
    """Export current configuration to file."""
    manager = get_config_manager()
    config = manager.get_config()

    data = {
        "app": {
            "name": config.app.name,
            "version": config.app.version,
            "environment": config.app.environment,
            "log_level": config.app.log_level,
        },
        "broker": {
            "provider": config.broker.provider,
            "paper_initial_cash": config.broker.paper_initial_cash,
        },
        "runtime": {
            "pipeline_interval_seconds": config.runtime.pipeline_interval_seconds,
            "heartbeat_interval_seconds": config.runtime.heartbeat_interval_seconds,
            "stream_enabled": config.runtime.stream_enabled,
            "scheduler_enabled": config.runtime.scheduler_enabled,
        },
        "risk": {
            "max_position_size": config.risk.max_position_size,
            "max_drawdown_percent": config.risk.max_drawdown_percent,
            "max_daily_loss": config.risk.max_daily_loss,
            "max_leverage": config.risk.max_leverage,
        },
        "execution": {
            "max_retries": config.execution.max_retries,
            "retry_delay_seconds": config.execution.retry_delay_seconds,
            "order_timeout_seconds": config.execution.order_timeout_seconds,
        },
    }

    if fmt == "yaml":
        try:
            import yaml

            with open(output, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False)
        except ImportError:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    else:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    console.print(f"[bold green]+[/bold green] Configuration exported to {output}")


@app.command("profile")
def profile(
    profile_name: Annotated[
        str | None, typer.Argument(help="Profile to show or set")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show or set configuration profile."""
    manager = get_config_manager()

    if profile_name is None:
        current = manager.profile
        if json_output:
            console.print(json.dumps({"profile": current}))
        else:
            console.print(f"Current profile: [bold]{current}[/bold]")
        return

    valid_profiles = {"development", "testing", "paper", "backtesting", "production"}
    if profile_name.lower() not in valid_profiles:
        if json_output:
            console.print(json.dumps({"error": f"Invalid profile: {profile_name}"}))
        else:
            console.print(
                f"[red]Invalid profile: {profile_name}. Valid: {', '.join(sorted(valid_profiles))}[/red]"
            )
        raise typer.Exit(1)

    manager.set_profile(profile_name)
    if json_output:
        console.print(json.dumps({"profile": profile_name, "set": True}))
    else:
        console.print(f"[bold green]+[/bold green] Profile set to: {profile_name}")

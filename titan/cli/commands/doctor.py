"""titan doctor - Health check for TITAN installation."""

from __future__ import annotations

import importlib
import sys

from rich.table import Table

from titan.cli.common import console, get_settings, logger


def _check_import(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, module_name
    except ImportError:
        return False, module_name


def _check_python() -> tuple[bool, str]:
    v = sys.version_info
    return (v >= (3, 12), f"{v.major}.{v.minor}.{v.micro}")


def doctor() -> None:
    """Check TITAN installation health."""
    logger.info("Doctor command executed")
    settings = get_settings()

    table = Table(title="TITAN Doctor", show_header=True, header_style="bold cyan")
    table.add_column("Check", style="bold")
    table.add_column("Result")
    table.add_column("Status")

    py_ok, py_ver = _check_python()
    py_status = "[green]+[/green]" if py_ok else "[red]![/red]"
    table.add_row("Python", py_ver, py_status)

    for module in ("typer", "rich", "pydantic", "loguru", "dotenv"):
        ok, name = _check_import(module)
        st = "[green]+[/green]" if ok else "[red]![/red]"
        table.add_row(name, "installed", st)

    titan_modules = [
        "titan.core.config",
        "titan.analysis.factory",
        "titan.deployment.manager",
        "titan.monitoring.manager",
        "titan.config.manager",
        "titan.paper.broker",
    ]
    for mod in titan_modules:
        ok, name = _check_import(mod)
        st = "[green]+[/green]" if ok else "[red]![/red]"
        table.add_row(name, "importable", st)

    console.print(table)
    console.print(
        f"\nApplication : [bold]{settings.app_name}[/bold]"
        f"\nVersion     : [bold]{settings.app_version}[/bold]"
        f"\nEnvironment : [bold]{settings.environment}[/bold]"
    )

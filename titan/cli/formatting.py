"""Rich formatting helpers for CLI output."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from titan.core.display import console

STATUS_STYLES: dict[str, str] = {
    "running": "green",
    "healthy": "green",
    "ok": "green",
    "connected": "green",
    "enabled": "green",
    "stopped": "red",
    "unhealthy": "red",
    "error": "red",
    "disconnected": "red",
    "disabled": "dim",
    "paused": "yellow",
    "degraded": "yellow",
    "unknown": "dim",
    "not running": "dim",
}


def status_label(status: str) -> str:
    style = STATUS_STYLES.get(status.lower(), "white")
    return f"[{style}]{status}[/{style}]"


def status_icon(status: str) -> str:
    style = STATUS_STYLES.get(status.lower(), "white")
    return f"[{style}]*[/{style}]"


def kv_table(**kwargs: str | float | bool) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in kwargs.items():
        table.add_row(key, str(value))
    return table


def command_panel(title: str, content: str, style: str = "cyan") -> Panel:
    return Panel(content, title=f"[bold {style}]{title}[/bold {style}]", expand=False)


def success_message(msg: str) -> None:
    console.print(f"[bold green]+[/bold green] {msg}")


def error_message(msg: str) -> None:
    console.print(f"[bold red]![/bold red] {msg}")


def warning_message(msg: str) -> None:
    console.print(f"[bold yellow]~[/bold yellow] {msg}")


def info_message(msg: str) -> None:
    console.print(f"[bold cyan]>[/bold cyan] {msg}")

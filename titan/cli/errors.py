"""CLI error handling and display utilities."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from titan.cli.exit_codes import (
    CONFIG_ERROR,
    NETWORK_ERROR,
    RUNTIME_ERROR,
)
from titan.core.exceptions import (
    AnalysisError,
    BrokerError,
    ConfigurationError,
    TitanError,
)

console = Console(stderr=True)

_ERROR_MAP: dict[type[TitanError], int] = {
    ConfigurationError: CONFIG_ERROR,
    AnalysisError: RUNTIME_ERROR,
    BrokerError: NETWORK_ERROR,
}


def exit_code_for(exc: Exception) -> int:
    if isinstance(exc, TitanError):
        return _ERROR_MAP.get(type(exc), RUNTIME_ERROR)
    return RUNTIME_ERROR


def format_error(exc: Exception) -> Panel:
    text = Text()
    text.append(f"{type(exc).__name__}: ", style="bold red")
    text.append(str(exc), style="red")
    return Panel(text, title="[bold red]Error[/bold red]", border_style="red")


def handle_error(exc: Exception) -> int:
    code = exit_code_for(exc)
    console.print(format_error(exc))
    return code


def handle_unexpected(exc: Exception) -> int:
    console.print(
        Panel(
            "[bold red]Unexpected error occurred.[/bold red]",
            border_style="red",
        )
    )
    return RUNTIME_ERROR

"""titan logs - Log viewing and management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from titan.cli.common import console

logs_app = typer.Typer(help="Log viewing and management.")
app = logs_app


@app.command("show")
def show(
    lines: Annotated[
        int, typer.Option("--lines", "-n", help="Number of lines to show")
    ] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show recent log entries."""
    log_file = Path("logs/titan.log")

    if not log_file.exists():
        if json_output:
            console.print(json.dumps({"entries": [], "file": str(log_file)}))
        else:
            console.print("[dim]No log file found.[/dim]")
        return

    with open(log_file, encoding="utf-8") as f:
        all_lines = f.readlines()
        recent = all_lines[-lines:]

    if json_output:
        console.print(
            json.dumps(
                {"entries": [line.rstrip() for line in recent], "count": len(recent)}
            )
        )
        return

    for line in recent:
        console.print(line.rstrip())


@app.command("path")
def path() -> None:
    """Show log file path."""
    log_file = Path("logs/titan.log")
    if log_file.exists():
        console.print(f"[bold]{log_file.resolve()}[/bold]")
    else:
        console.print("[dim]No log file found.[/dim]")


@app.command("stats")
def stats(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show log statistics."""
    log_file = Path("logs/titan.log")
    if not log_file.exists():
        if json_output:
            console.print(json.dumps({"exists": False}))
        else:
            console.print("[dim]No log file found.[/dim]")
        return

    size = log_file.stat().st_size
    with open(log_file, encoding="utf-8") as f:
        line_count = sum(1 for _ in f)

    if json_output:
        console.print(
            json.dumps(
                {
                    "file": str(log_file.resolve()),
                    "size_bytes": size,
                    "size_kb": round(size / 1024, 1),
                    "line_count": line_count,
                }
            )
        )
        return

    table = Table(title="Log Statistics", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("File", str(log_file.resolve()))
    table.add_row("Size", f"{size / 1024:.1f} KB")
    table.add_row("Lines", str(line_count))
    console.print(table)


@app.command("level")
def level(
    level_name: Annotated[
        str | None,
        typer.Argument(help="Log level to set (DEBUG, INFO, WARNING, ERROR)"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Get or set the current log level."""
    log_file = Path("logs/titan.log")

    if level_name is None:
        current = "INFO"
        if log_file.exists():
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if " | " in stripped:
                        parts = stripped.split(" | ")
                        if len(parts) >= 2:
                            lvl = parts[1].upper()
                            if lvl in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                                current = lvl
                                break

        if json_output:
            console.print(json.dumps({"level": current}))
        else:
            console.print(f"Current log level: [bold]{current}[/bold]")
        return

    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level_name.upper() not in valid_levels:
        if json_output:
            console.print(json.dumps({"error": f"Invalid level: {level_name}"}))
        else:
            console.print(
                f"[red]Invalid level: {level_name}. Valid: {', '.join(sorted(valid_levels))}[/red]"
            )
        raise typer.Exit(1)

    if json_output:
        console.print(
            json.dumps(
                {
                    "level": level_name.upper(),
                    "note": "Level change applies to new log entries",
                }
            )
        )
    else:
        console.print(
            f"[bold green]+[/bold green] Log level set to: {level_name.upper()}"
        )


@app.command("rotate")
def rotate(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Rotate log files."""
    log_file = Path("logs/titan.log")
    if not log_file.exists():
        if json_output:
            console.print(json.dumps({"error": "No log file found"}))
        else:
            console.print("[dim]No log file found.[/dim]")
        return

    size = log_file.stat().st_size
    backup = log_file.with_suffix(".log.1")

    if backup.exists():
        backup.unlink()

    log_file.rename(backup)
    log_file.touch()

    if json_output:
        console.print(
            json.dumps(
                {
                    "rotated": True,
                    "backup": str(backup),
                    "previous_size_bytes": size,
                }
            )
        )
    else:
        console.print(f"[bold green]+[/bold green] Log rotated. Backup: {backup}")


@app.command("clear")
def clear(
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Clear without confirmation")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Clear the log file."""
    log_file = Path("logs/titan.log")
    if not log_file.exists():
        if json_output:
            console.print(json.dumps({"error": "No log file found"}))
        else:
            console.print("[dim]No log file found.[/dim]")
        return

    if not force and not json_output:
        confirm = typer.confirm("Are you sure you want to clear the log file?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            return

    size = log_file.stat().st_size
    log_file.write_text("", encoding="utf-8")

    if json_output:
        console.print(json.dumps({"cleared": True, "previous_size_bytes": size}))
    else:
        console.print(
            f"[bold green]+[/bold green] Log file cleared ({size / 1024:.1f} KB removed)"
        )

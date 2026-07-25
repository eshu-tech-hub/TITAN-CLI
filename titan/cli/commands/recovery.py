"""titan recovery - Recovery subsystem commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from titan.cli.common import console, get_recovery_manager

recovery_app = typer.Typer(help="Recovery subsystem management.")
app = recovery_app


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
    """Show recovery subsystem status."""
    rm = get_recovery_manager()
    report = rm.generate_report()
    history = rm.get_recovery_history()

    if json_output:
        data = {
            "total_requests": len(history),
            "successful": report.successful_attempts,
            "failed": report.failed_attempts,
            "recovered_components": list(report.recovered_components),
            "status": _clean_enum(report.status),
        }
        console.print(json.dumps(data))
        return

    table = Table(
        title="Recovery Subsystem", show_header=False, box=None, padding=(0, 2)
    )
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Total Requests", str(len(history)))
    table.add_row("Successful", str(report.successful_attempts))
    table.add_row("Failed", str(report.failed_attempts))
    table.add_row("Status", _clean_enum(report.status))
    console.print(table)

    if verbose and history:
        detail = Table(title="Recent History", show_header=True)
        detail.add_column("Component")
        detail.add_column("Strategy")
        detail.add_column("Status")
        detail.add_column("Reason")
        for h in history[-10:]:
            detail.add_row(
                _clean_enum(h.component),
                _clean_enum(h.strategy),
                _clean_enum(h.status),
                h.failure_reason[:50] if h.failure_reason else "",
            )
        console.print(detail)


@app.command("retry")
def retry(
    component: Annotated[
        str, typer.Argument(help="Component to recover (e.g. broker_session)")
    ],
    reason: Annotated[str, typer.Argument(help="Failure reason")] = "manual retry",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Trigger a recovery retry for a component."""
    from titan.recovery.models import ComponentType

    try:
        comp = ComponentType(component)
    except ValueError:
        console.print(f"[red]Invalid component: {component}[/red]")
        console.print(f"Valid: {', '.join(c.value for c in ComponentType)}")
        raise typer.Exit(1)

    rm = get_recovery_manager()
    report = rm.request_recovery(component=comp, failure_reason=reason)

    if json_output:
        data = {
            "request_id": report.request_id,
            "component": _clean_enum(report.component),
            "strategy": _clean_enum(report.strategy),
            "status": _clean_enum(report.status),
            "total_attempts": report.total_attempts,
            "duration_seconds": report.duration_seconds,
        }
        console.print(json.dumps(data))
        return

    status_str = _clean_enum(report.status)
    if status_str == "success":
        console.print(
            f"[bold green]+[/bold green] Recovery {status_str} for {component}"
        )
    else:
        console.print(f"[bold red]![/bold red] Recovery {status_str} for {component}")


@app.command("checkpoint")
def checkpoint(
    action: Annotated[str, typer.Argument(help="Action: save, list, latest")] = "list",
    component: Annotated[
        str, typer.Option("--component", help="Component type")
    ] = "pipeline",
    checkpoint_id: Annotated[
        str, typer.Option("--id", help="Checkpoint ID for save")
    ] = "",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Manage recovery checkpoints."""
    from titan.recovery.models import ComponentType

    rm = get_recovery_manager()

    if action == "save":
        try:
            comp = ComponentType(component)
        except ValueError:
            console.print(f"[red]Invalid component: {component}[/red]")
            raise typer.Exit(1)

        cid = checkpoint_id or f"cp-{component}"
        cp = rm.checkpoints.save(
            checkpoint_id=cid,
            component=comp,
            state_data={"cli_save": True},
        )
        if json_output:
            console.print(
                json.dumps(
                    {
                        "checkpoint_id": cp.checkpoint_id,
                        "component": _clean_enum(cp.component),
                    }
                )
            )
        else:
            console.print(
                f"[bold green]+[/bold green] Checkpoint saved: {cp.checkpoint_id}"
            )

    elif action == "latest":
        try:
            comp = ComponentType(component)
        except ValueError:
            console.print(f"[red]Invalid component: {component}[/red]")
            raise typer.Exit(1)

        latest_cp = rm.checkpoints.latest(comp)
        if latest_cp is None:
            console.print("[dim]No checkpoint found.[/dim]")
            return
        if json_output:
            console.print(
                json.dumps(
                    {
                        "checkpoint_id": latest_cp.checkpoint_id,
                        "component": _clean_enum(latest_cp.component),
                    }
                )
            )
        else:
            console.print(
                f"Checkpoint: {latest_cp.checkpoint_id} ({_clean_enum(latest_cp.component)})"
            )

    else:
        checkpoints = rm.checkpoints.list_all()
        if json_output:
            data = [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "component": _clean_enum(cp.component),
                }
                for cp in checkpoints
            ]
            console.print(json.dumps(data))
            return

        if not checkpoints:
            console.print("[dim]No checkpoints found.[/dim]")
            return

        table = Table(title="Checkpoints", show_header=True)
        table.add_column("ID")
        table.add_column("Component")
        for cp in checkpoints:
            table.add_row(cp.checkpoint_id, _clean_enum(cp.component))
        console.print(table)


@app.command("restore")
def restore(
    checkpoint_id: Annotated[str, typer.Argument(help="Checkpoint ID to restore")],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Restore state from a checkpoint."""
    rm = get_recovery_manager()

    try:
        cp = rm.checkpoints.load(checkpoint_id)
    except Exception as exc:
        if json_output:
            console.print(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print(
            json.dumps(
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "component": _clean_enum(cp.component),
                    "restored": True,
                }
            )
        )
    else:
        console.print(
            f"[bold green]+[/bold green] Restored from checkpoint: {cp.checkpoint_id}"
        )


@app.command("circuit")
def circuit(
    action: Annotated[str, typer.Argument(help="Action: list, reset")] = "list",
    name: Annotated[str, typer.Option("--name", help="Circuit breaker name")] = "",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Manage circuit breakers."""
    rm = get_recovery_manager()

    if action == "reset" and name:
        cb = rm.get_circuit_breaker(name)
        if cb is None:
            if json_output:
                console.print(json.dumps({"error": f"Not found: {name}"}))
            else:
                console.print(f"[red]Circuit breaker not found: {name}[/red]")
            raise typer.Exit(1)
        cb.reset()
        if json_output:
            console.print(json.dumps({"name": name, "reset": True}))
        else:
            console.print(f"[bold green]+[/bold green] Circuit breaker '{name}' reset.")
        return

    cb = rm.get_circuit_breaker(name) if name else None
    if name and cb is None:
        if json_output:
            console.print(json.dumps({"error": f"Not found: {name}"}))
        else:
            console.print(f"[red]Circuit breaker not found: {name}[/red]")
        raise typer.Exit(1)

    if cb is not None:
        if json_output:
            console.print(
                json.dumps(
                    {
                        "name": name,
                        "state": _clean_enum(cb.state),
                        "failure_count": cb.failure_count,
                        "success_count": cb.success_count,
                    }
                )
            )
        else:
            table = Table(
                title=f"Circuit Breaker: {name}",
                show_header=False,
                box=None,
                padding=(0, 2),
            )
            table.add_column("Key", style="bold")
            table.add_column("Value")
            table.add_row("State", _clean_enum(cb.state))
            table.add_row("Failures", str(cb.failure_count))
            table.add_row("Successes", str(cb.success_count))
            console.print(table)
    else:
        if json_output:
            console.print(json.dumps({"circuit_breakers": []}))
        else:
            console.print("[dim]No circuit breakers registered.[/dim]")

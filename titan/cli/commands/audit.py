"""titan audit - Audit trail commands."""

from __future__ import annotations

import csv
import io
import json
from typing import Annotated

import typer
from rich.table import Table

from titan.cli.common import console, logger

audit_app = typer.Typer(help="Audit trail management.")
app = audit_app


def _clean_enum(val: object) -> str:
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show audit subsystem status."""
    logger.info("Audit status command executed")
    from titan.audit.manager import AuditManager

    manager = AuditManager()
    report = manager.generate_report()

    if json_output:
        data = {
            "total_events": report.total_events,
            "integrity_status": report.integrity_status,
            "verification_failures": report.verification_failures,
            "sequence_range": list(report.sequence_range),
        }
        console.print(json.dumps(data))
        return

    table = Table(title="Audit Trail", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Total Events", str(report.total_events))
    if report.integrity_status == "valid":
        table.add_row("Integrity", f"[green]{report.integrity_status}[/green]")
    else:
        table.add_row("Integrity", f"[red]{report.integrity_status}[/red]")
    table.add_row("Verification Failures", str(report.verification_failures))
    seq = report.sequence_range
    table.add_row("Sequence Range", f"{seq[0]} - {seq[1]}")
    console.print(table)


@app.command("verify")
def verify() -> None:
    """Verify audit chain integrity."""
    logger.info("Audit verify command executed")
    from titan.audit.manager import AuditManager

    manager = AuditManager()
    integrity = manager.verify_integrity()
    if integrity.is_valid:
        console.print("[bold green]+[/bold green] Audit chain integrity verified.")
    else:
        console.print("[bold red]![/bold red] Audit chain integrity compromised.")


@app.command("search")
def search(
    source: Annotated[
        str | None, typer.Option("--source", help="Filter by source")
    ] = None,
    category: Annotated[
        str | None, typer.Option("--category", help="Filter by category")
    ] = None,
    severity: Annotated[
        str | None, typer.Option("--severity", help="Filter by severity")
    ] = None,
    action: Annotated[
        str | None, typer.Option("--action", help="Filter by action substring")
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Max events to show")
    ] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Search audit events."""
    from titan.audit.manager import AuditManager
    from titan.audit.models import AuditCategory, AuditSeverity, AuditSource
    from titan.audit.query import AuditQuery

    manager = AuditManager()
    query = AuditQuery()

    if source:
        query = AuditQuery(source=AuditSource(source))
    if category:
        query = AuditQuery(category=AuditCategory(category))
    if severity:
        query = AuditQuery(severity=AuditSeverity(severity))
    if action:
        pass

    results = manager.search(query)

    if action:
        results = [e for e in results if action.lower() in e.action.lower()]

    results = results[:limit]

    if json_output:
        data = [e.to_dict() for e in results]
        console.print(json.dumps(data))
        return

    if not results:
        console.print("[dim]No events found.[/dim]")
        return

    table = Table(title=f"Audit Events ({len(results)} found)", show_header=True)
    table.add_column("Seq")
    table.add_column("Source")
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("Action")
    table.add_column("Result")
    for e in results:
        table.add_row(
            str(e.sequence_number),
            _clean_enum(e.source),
            _clean_enum(e.category),
            _clean_enum(e.severity),
            e.action[:40],
            _clean_enum(e.result),
        )
    console.print(table)


@app.command("export")
def export(
    output: Annotated[
        str, typer.Option("--output", "-o", help="Output file path")
    ] = "audit_export.json",
    fmt: Annotated[
        str, typer.Option("--format", help="Export format: json or csv")
    ] = "json",
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Max events to export")
    ] = 0,
) -> None:
    """Export audit events to file."""
    from titan.audit.manager import AuditManager

    manager = AuditManager()
    all_events = manager.storage.load_all()

    if limit > 0:
        all_events = all_events[:limit]

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "sequence_number",
                "timestamp",
                "source",
                "category",
                "severity",
                "action",
                "result",
                "event_id",
            ]
        )
        for e in all_events:
            writer.writerow(
                [
                    e.sequence_number,
                    e.timestamp.isoformat(),
                    _clean_enum(e.source),
                    _clean_enum(e.category),
                    _clean_enum(e.severity),
                    e.action,
                    _clean_enum(e.result),
                    e.event_id,
                ]
            )
        with open(output, "w", encoding="utf-8") as f:
            f.write(buf.getvalue())
    else:
        data = [e.to_dict() for e in all_events]
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    console.print(
        f"[bold green]+[/bold green] Exported {len(all_events)} events to {output}"
    )


@app.command("stats")
def stats(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show audit event statistics."""
    from titan.audit.manager import AuditManager

    manager = AuditManager()
    report = manager.generate_report()

    if json_output:
        data = {
            "total_events": report.total_events,
            "events_by_source": report.events_by_source,
            "events_by_severity": report.events_by_severity,
            "events_by_category": report.events_by_category,
            "integrity_status": report.integrity_status,
        }
        console.print(json.dumps(data))
        return

    table = Table(title="Audit Statistics", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Total Events", str(report.total_events))
    table.add_row("Integrity", report.integrity_status)

    if report.events_by_source:
        console.print(table)
        st = Table(title="By Source", show_header=True)
        st.add_column("Source")
        st.add_column("Count")
        for src, cnt in sorted(report.events_by_source.items(), key=lambda x: -x[1]):
            st.add_row(src, str(cnt))
        console.print(st)
    else:
        console.print(table)

    if report.events_by_severity:
        sev = Table(title="By Severity", show_header=True)
        sev.add_column("Severity")
        sev.add_column("Count")
        for s, cnt in sorted(report.events_by_severity.items(), key=lambda x: -x[1]):
            sev.add_row(s, str(cnt))
        console.print(sev)

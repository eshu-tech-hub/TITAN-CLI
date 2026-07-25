"""titan report - Generate system reports."""

from __future__ import annotations

import typer
from rich.panel import Panel

from titan.cli.common import console, logger

report_app = typer.Typer(help="System report generation.")
app = report_app


@app.command("generate")
def generate() -> None:
    """Generate comprehensive system report."""
    logger.info("Report generate command executed")

    from titan.deployment.manager import DeploymentManager

    dm = DeploymentManager.instance()
    report = dm.generate_report()

    table_str = (
        f"Status    : {report.status.value}\n"
        f"Version   : {report.version.version}\n"
        f"Uptime    : {report.uptime_seconds:,.0f}s\n"
        f"Start Time: {report.start_time}"
    )
    console.print(Panel(table_str, title="Deployment Report", expand=False))

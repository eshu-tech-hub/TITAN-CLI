"""TITAN CLI - Institutional Trading Intelligence System.

Typer application with modular command groups.
"""

from __future__ import annotations

from typing import Annotated

import typer

from titan.cli.commands.ai import app as ai_app
from titan.cli.commands.alert import alert_app
from titan.cli.commands.audit import audit_app
from titan.cli.commands.backtest import backtest_app
from titan.cli.commands.broker import broker_app
from titan.cli.commands.config import config_app
from titan.cli.commands.deployment import deployment_app
from titan.cli.commands.doctor import doctor as _doctor
from titan.cli.commands.live import live_app
from titan.cli.commands.logs import logs_app
from titan.cli.commands.monitor import monitor_app
from titan.cli.commands.paper import paper_app
from titan.cli.commands.portfolio import app as portfolio_app
from titan.cli.commands.recovery import recovery_app
from titan.cli.commands.report import report_app
from titan.cli.commands.runtime import runtime_app
from titan.cli.commands.runtime import version as _version
from titan.cli.commands.validate import app as validate_app

app = typer.Typer(
    name="titan",
    help="TITAN CLI - Institutional Trading Intelligence System",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)


@app.command("version")
def cmd_version(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed version info")
    ] = False,
) -> None:
    """Display TITAN version information."""
    _version(verbose=verbose)


@app.command("doctor")
def cmd_doctor() -> None:
    """Check TITAN installation health."""
    _doctor()


app.add_typer(runtime_app, name="runtime", help="Runtime engine lifecycle")
app.add_typer(paper_app, name="paper", help="Paper trading management")
app.add_typer(live_app, name="live", help="Live trading management")
app.add_typer(monitor_app, name="monitor", help="Monitoring subsystem")
app.add_typer(config_app, name="config", help="Configuration management")
app.add_typer(alert_app, name="alert", help="Alerting subsystem")
app.add_typer(audit_app, name="audit", help="Audit trail")
app.add_typer(report_app, name="report", help="System reports")
app.add_typer(deployment_app, name="deployment", help="Deployment lifecycle")
app.add_typer(logs_app, name="logs", help="Log management")
app.add_typer(backtest_app, name="backtest", help="Backtesting management")
app.add_typer(recovery_app, name="recovery", help="Recovery subsystem")
app.add_typer(validate_app, name="validate", help="Operational validation framework")
app.add_typer(broker_app, name="broker", help="Broker certification and management")
app.add_typer(
    portfolio_app, name="portfolio", help="Portfolio Analytics & Risk Dashboard"
)
app.add_typer(ai_app, name="ai", help="AI Research Assistant & Synthesizer")

@app.command("tui")
def launch_tui():
    """Launch the TITAN Terminal User Interface (Dashboard)."""
    # Force .env to load before ConfigManager or Textual App initialise.
    # Without this the TUI boots under the 'default' profile instead of
    # honouring the project .env file (e.g. TITAN__ENVIRONMENT=development).
    try:
        from dotenv import load_dotenv

        load_dotenv(override=True)
    except ImportError:
        pass  # python-dotenv is optional; silently skip if absent

    try:
        import inspect

        from textual.app import App

        from titan.tui import shell
        
        # Dynamically find the class that inherits from Textual's App
        app_class = None
        for name, obj in inspect.getmembers(shell, inspect.isclass):
            if issubclass(obj, App) and obj is not App:
                app_class = obj
                break
                
        if not app_class:
            raise ImportError("Could not locate the main Textual App class in titan.tui.shell")
            
        # Instantiate and run the dashboard
        tui_app = app_class()
        tui_app.run()
        
    except Exception as e:
        import typer
        from rich.console import Console
        Console().print(f"[bold red]Error launching TUI:[/bold red] {e}")
        raise typer.Exit(1)
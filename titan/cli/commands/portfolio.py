"""CLI commands for Portfolio Analytics & Risk Dashboard."""

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
import json

app = typer.Typer(help="Portfolio Analytics & Risk Dashboard")
console = Console()


def _get_analytics_data():
    """Helper to safely extract current portfolio and journal from runtime."""
    try:
        from titan.cli.common import get_runtime_engine
        from titan.portfolio.models import ExistingPortfolio, OpenPosition
        from titan.portfolio.analytics import PortfolioAnalytics

        engine = get_runtime_engine()
        if not engine or not getattr(engine, "broker", None):
            console.print(
                "[bold red]Error:[/bold red] Runtime engine or broker not running. Start a live or paper session first."
            )
            raise typer.Exit(1)

        broker = engine.broker
        funds = broker.funds()
        positions = broker.positions()

        open_positions = tuple(
            OpenPosition(
                symbol=p.symbol,
                instrument_type=getattr(p, "product", "EQUITY"),
                direction="long" if p.quantity > 0 else "short",
                quantity=p.quantity,
                entry_price=float(p.average_price or 0.0),
                current_price=float(p.current_price or 0.0),
                market_value=float(p.quantity * (p.current_price or 0.0)),
                pnl=float(p.pnl or 0.0),
            )
            for p in positions
        )

        portfolio = ExistingPortfolio(
            positions=open_positions,
            total_capital=float(funds.available_cash + funds.used_margin),
            cash_reserve=float(funds.available_cash),
        )
        entries = engine.trade_journal.repository.list(page=1, page_size=10000)
        return PortfolioAnalytics(), portfolio, entries
    except Exception as e:
        console.print(f"[bold red]Error fetching portfolio state:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("summary")
def summary(json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """Display high-level portfolio snapshot."""
    analytics, portfolio, _ = _get_analytics_data()
    snapshot = analytics.generate_snapshot(portfolio)

    if json_output:
        import dataclasses

        console.print(json.dumps(dataclasses.asdict(snapshot), indent=2))
        return

    table = Table(title="Portfolio Summary", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Capital", f"₹{snapshot.total_capital:,.2f}")
    table.add_row("Capital Used", f"₹{snapshot.capital_used:,.2f}")
    table.add_row("Available Capital", f"₹{snapshot.available_capital:,.2f}")
    table.add_row("Total P&L", f"₹{snapshot.total_pnl:,.2f}")
    table.add_row("Utilization", f"{snapshot.utilization * 100:.1f}%")
    table.add_row("Open Positions", str(snapshot.position_count))

    console.print(table)


@app.command("risk")
def risk(json_output: bool = typer.Option(False, "--json", help="Output as JSON")):
    """Display portfolio risk and exposure analytics."""
    analytics, portfolio, entries = _get_analytics_data()
    exposure = analytics.analyze_exposure(portfolio)
    drawdown = analytics.analyze_drawdown(entries, portfolio.total_capital)

    if json_output:
        import dataclasses

        out = {
            "exposure": dataclasses.asdict(exposure),
            "drawdown": dataclasses.asdict(drawdown),
        }
        console.print(json.dumps(out, indent=2))
        return

    table = Table(title="Risk & Exposure Analysis", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Gross Exposure", f"₹{exposure.gross_exposure:,.2f}")
    table.add_row("Net Exposure", f"₹{exposure.net_exposure:,.2f}")
    table.add_row("Max Drawdown", f"₹{drawdown.max_drawdown:,.2f}")
    table.add_row("Current Drawdown", f"₹{drawdown.current_drawdown:,.2f}")
    table.add_row("Concentration Score", f"{exposure.concentration_score:.2f}")

    console.print(table)


@app.command("performance")
def performance(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Display institutional portfolio performance metrics."""
    analytics, _, entries = _get_analytics_data()
    perf = analytics.analyze_performance(entries)

    if json_output:
        import dataclasses

        console.print(json.dumps(dataclasses.asdict(perf), indent=2))
        return

    table = Table(title="Performance Analytics", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Win Rate", f"{perf.win_rate * 100:.1f}%")
    table.add_row("Profit Factor", f"{perf.profit_factor:.2f}")
    table.add_row("Expectancy", f"{perf.expectancy:.2f}R")
    table.add_row("Avg Winner", f"₹{perf.average_winner:,.2f}")
    table.add_row("Avg Loser", f"₹{perf.average_loser:,.2f}")

    console.print(table)


@app.command("allocation")
def allocation(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Display capital allocation breakdown."""
    analytics, portfolio, _ = _get_analytics_data()
    alloc = analytics.analyze_allocation(portfolio)

    if json_output:
        import dataclasses

        console.print(json.dumps(dataclasses.asdict(alloc), indent=2))
        return

    table = Table(title="Sector Allocation")
    table.add_column("Sector", style="cyan")
    table.add_column("Weight", justify="right", style="green")

    for sector, weight in sorted(
        alloc.by_sector.items(), key=lambda x: x[1], reverse=True
    ):
        table.add_row(sector, f"{weight * 100:.1f}%")

    if not alloc.by_sector:
        table.add_row("No open positions", "-")

    console.print(table)


@app.command("export")
def export(
    output: Path = typer.Option(..., "--out", "-o", help="Output file path"),
    fmt: str = typer.Option(
        "json", "--format", "-f", help="Export format (json or csv)"
    ),
):
    """Export complete portfolio analytics to disk."""
    analytics, portfolio, entries = _get_analytics_data()

    try:
        if fmt.lower() == "csv":
            analytics.export_csv(output, portfolio, entries)
        else:
            analytics.export_json(output, portfolio, entries)
        console.print(
            f"[bold green]Success:[/bold green] Portfolio analytics exported to {output}"
        )
    except Exception as e:
        console.print(f"[bold red]Export Failed:[/bold red] {e}")
        raise typer.Exit(1)

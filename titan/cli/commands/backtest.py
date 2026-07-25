"""titan backtest - Backtesting subsystem commands."""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.live import Live
from rich.table import Table

from titan.cli.common import console, logger

backtest_app = typer.Typer(help="Backtesting subsystem management.")
app = backtest_app


# ── Session State ──────────────────────────────────────────

_backtest_history: list[dict[str, Any]] = []
_backtest_running: bool = False
_backtest_start_time: datetime | None = None


def _reset_backtest_session() -> None:
    """Reset backtest session state (for testing)."""
    global _backtest_history, _backtest_running, _backtest_start_time
    _backtest_history = []
    _backtest_running = False
    _backtest_start_time = None


def _is_running() -> bool:
    return _backtest_running


def _last_result() -> dict[str, Any] | None:
    if _backtest_history:
        return _backtest_history[-1]
    return None


# ── Helpers ────────────────────────────────────────────────


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "< 1s"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def _decimal_str(d: Decimal) -> str:
    return f"INR {d:,.2f}"


def _pnl_str(value: Decimal) -> str:
    style = "green" if value >= 0 else "red"
    return f"[{style}]{_decimal_str(value)}[/{style}]"


def _return_str(value: Decimal) -> str:
    pct = float(value) * 100
    style = "green" if value >= 0 else "red"
    return f"[{style}]{pct:+.2f}%[/{style}]"


def _json_serial(obj: object) -> str:
    if hasattr(obj, "isoformat"):
        return str(obj.isoformat())
    if hasattr(obj, "value"):
        return str(obj.value)
    if isinstance(obj, Decimal):
        return str(obj)
    return str(obj)


# ── CSV Loading ────────────────────────────────────────────


def _load_csv_dataset(
    csv_path: Path,
    symbol: str,
    exchange: str,
) -> Any:
    """Load a HistoricalDataset from a CSV file.

    CSV format: timestamp,open,high,low,close,volume
    Timestamps are ISO-8601 format.
    """
    from titan.backtesting.dataset import HistoricalDataset
    from titan.backtesting.exceptions import DatasetValidationError
    from titan.backtesting.models import HistoricalBar
    from titan.brokers.models import Exchange

    try:
        exchange_enum = Exchange(exchange.lower())
    except ValueError:
        valid = [e.value for e in Exchange]
        raise DatasetValidationError(
            f"Invalid exchange '{exchange}'. Valid: {', '.join(valid)}"
        )

    if not csv_path.exists():
        raise DatasetValidationError(f"CSV file not found: {csv_path}")

    bars: list[HistoricalBar] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if reader.fieldnames is None:
            raise DatasetValidationError("CSV file is empty.")
        missing = required - set(reader.fieldnames)
        if missing:
            raise DatasetValidationError(
                f"CSV missing columns: {', '.join(sorted(missing))}"
            )

        for row_idx, row in enumerate(reader):
            try:
                timestamp = datetime.fromisoformat(row["timestamp"])
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                bar = HistoricalBar(
                    timestamp=timestamp,
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=int(row["volume"]),
                )
                bars.append(bar)
            except (InvalidOperation, ValueError, KeyError) as e:
                raise DatasetValidationError(f"Invalid data at row {row_idx + 2}: {e}")

    if not bars:
        raise DatasetValidationError("CSV file contains no data rows.")

    return HistoricalDataset(symbol=symbol, exchange=exchange_enum, bars=bars)


def _report_to_dict(report: Any) -> dict[str, Any]:
    """Convert a BacktestReport to a JSON-serializable dict."""
    s = report.statistics
    m = report.metrics
    return {
        "backtest_id": report.backtest_id,
        "symbol": report.symbol,
        "exchange": report.exchange,
        "status": report.status.value,
        "bars_processed": report.bars_processed,
        "start_time": report.start_time.isoformat(),
        "end_time": report.end_time.isoformat(),
        "duration_seconds": report.duration_seconds,
        "total_capital": str(report.total_capital),
        "final_equity": str(report.final_equity),
        "total_pnl": str(report.total_pnl),
        "total_return": str(report.total_return),
        "statistics": {
            "total_trades": s.total_trades,
            "winning_trades": s.winning_trades,
            "losing_trades": s.losing_trades,
            "win_rate": s.win_rate,
            "loss_rate": s.loss_rate,
            "profit_factor": s.profit_factor,
            "average_gain": str(s.average_gain),
            "average_loss": str(s.average_loss),
            "expectancy": str(s.expectancy),
            "max_consecutive_wins": s.max_consecutive_wins,
            "max_consecutive_losses": s.max_consecutive_losses,
            "max_drawdown": str(s.max_drawdown),
            "recovery_factor": s.recovery_factor,
        },
        "metrics": {
            "daily_return": m.daily_return,
            "monthly_return": m.monthly_return,
            "annualized_return": m.annualized_return,
            "volatility": m.volatility,
            "sharpe_ratio": m.sharpe_ratio,
            "sortino_ratio": m.sortino_ratio,
            "calmar_ratio": m.calmar_ratio,
            "mar_ratio": m.mar_ratio,
        },
        "warnings": list(report.warnings),
        "errors": list(report.errors),
        "equity_curve_points": len(report.equity_curve),
    }


# ── Display Helpers ────────────────────────────────────────


def _print_backtest_list() -> None:
    if not _backtest_history:
        console.print("[dim]No completed backtests.[/dim]")
        return

    table = Table(title="Backtest History", show_header=True, header_style="bold")
    table.add_column("#", style="dim")
    table.add_column("Symbol")
    table.add_column("Exchange")
    table.add_column("Bars")
    table.add_column("Trades")
    table.add_column("Win Rate")
    table.add_column("P&L")
    table.add_column("Return")
    table.add_column("Duration")

    for i, entry in enumerate(_backtest_history, 1):
        table.add_row(
            str(i),
            entry["symbol"],
            entry["exchange"],
            str(entry["bars_processed"]),
            str(entry["statistics"]["total_trades"]),
            f"{entry['statistics']['win_rate']:.1%}",
            _pnl_str(Decimal(entry["total_pnl"])),
            _return_str(Decimal(entry["total_return"])),
            _format_duration(entry["duration_seconds"]),
        )

    console.print(table)


def _print_backtest_status(data: dict[str, Any] | None) -> None:
    table = Table(title="Backtest Status", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")

    running = _is_running()
    status_str = "[yellow]running[/yellow]" if running else "[dim]idle[/dim]"
    table.add_row("Engine Status", status_str)

    if running and _backtest_start_time is not None:
        elapsed = (datetime.now(timezone.utc) - _backtest_start_time).total_seconds()
        table.add_row("Elapsed", _format_duration(elapsed))

    if data is not None:
        table.add_row("Symbol", data["symbol"])
        table.add_row("Exchange", data["exchange"])
        table.add_row("Bars Processed", str(data["bars_processed"]))
        table.add_row("Duration", _format_duration(data["duration_seconds"]))
        table.add_row("Status", data["status"])
        table.add_row("Total P&L", _pnl_str(Decimal(data["total_pnl"])))
        table.add_row("Total Return", _return_str(Decimal(data["total_return"])))
        table.add_row("Win Rate", f"{data['statistics']['win_rate']:.1%}")
        table.add_row("Trades", str(data["statistics"]["total_trades"]))
        table.add_row(
            "Max Drawdown", f"{Decimal(data['statistics']['max_drawdown']):.2%}"
        )
        if data.get("warnings"):
            table.add_row("Warnings", str(len(data["warnings"])))
        if data.get("errors"):
            table.add_row("Errors", str(len(data["errors"])))
    else:
        table.add_row("Last Run", "[dim]None[/dim]")

    console.print(table)


def _print_backtest_report(data: dict[str, Any], verbose: bool) -> None:
    s = data["statistics"]
    m = data["metrics"]

    summary = Table(
        title="Backtest Summary", show_header=False, box=None, padding=(0, 2)
    )
    summary.add_column("Key", style="bold")
    summary.add_column("Value")
    summary.add_row("Backtest ID", data["backtest_id"])
    summary.add_row("Symbol", data["symbol"])
    summary.add_row("Exchange", data["exchange"])
    summary.add_row("Status", data["status"])
    summary.add_row("Bars Processed", str(data["bars_processed"]))
    summary.add_row("Start Time", data["start_time"])
    summary.add_row("End Time", data["end_time"])
    summary.add_row("Duration", _format_duration(data["duration_seconds"]))
    console.print(summary)

    capital = Table(title="Capital", show_header=False, box=None, padding=(0, 2))
    capital.add_column("Key", style="bold")
    capital.add_column("Value")
    capital.add_row("Starting Capital", _decimal_str(Decimal(data["total_capital"])))
    capital.add_row("Final Equity", _decimal_str(Decimal(data["final_equity"])))
    capital.add_row("Total P&L", _pnl_str(Decimal(data["total_pnl"])))
    capital.add_row("Total Return", _return_str(Decimal(data["total_return"])))
    console.print(capital)

    stats = Table(
        title="Trading Statistics", show_header=False, box=None, padding=(0, 2)
    )
    stats.add_column("Key", style="bold")
    stats.add_column("Value")
    stats.add_row("Total Trades", str(s["total_trades"]))
    stats.add_row("Winning Trades", str(s["winning_trades"]))
    stats.add_row("Losing Trades", str(s["losing_trades"]))
    stats.add_row("Win Rate", f"{s['win_rate']:.1%}")
    stats.add_row("Loss Rate", f"{s['loss_rate']:.1%}")
    stats.add_row("Profit Factor", f"{s['profit_factor']:.2f}")
    stats.add_row("Average Gain", _decimal_str(Decimal(s["average_gain"])))
    stats.add_row("Average Loss", _decimal_str(Decimal(s["average_loss"])))
    stats.add_row("Expectancy", _decimal_str(Decimal(s["expectancy"])))
    stats.add_row("Max Consecutive Wins", str(s["max_consecutive_wins"]))
    stats.add_row("Max Consecutive Losses", str(s["max_consecutive_losses"]))
    stats.add_row("Max Drawdown", f"{Decimal(s['max_drawdown']):.2%}")
    stats.add_row("Recovery Factor", f"{s['recovery_factor']:.2f}")
    console.print(stats)

    metrics = Table(
        title="Performance Metrics", show_header=False, box=None, padding=(0, 2)
    )
    metrics.add_column("Key", style="bold")
    metrics.add_column("Value")
    metrics.add_row("Daily Return", f"{m['daily_return']:.4%}")
    metrics.add_row("Monthly Return", f"{m['monthly_return']:.4%}")
    metrics.add_row("Annualized Return", f"{m['annualized_return']:.4%}")
    metrics.add_row("Volatility", f"{m['volatility']:.4%}")
    metrics.add_row("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}")
    metrics.add_row("Sortino Ratio", f"{m['sortino_ratio']:.2f}")
    metrics.add_row("Calmar Ratio", f"{m['calmar_ratio']:.2f}")
    metrics.add_row("MAR Ratio", f"{m['mar_ratio']:.2f}")
    console.print(metrics)

    if verbose:
        if data.get("warnings"):
            warn_table = Table(title="Warnings", show_header=True, header_style="bold")
            warn_table.add_column("#", style="dim")
            warn_table.add_column("Message")
            for i, w in enumerate(data["warnings"], 1):
                warn_table.add_row(str(i), w)
            console.print(warn_table)

        if data.get("errors"):
            err_table = Table(title="Errors", show_header=True, header_style="bold")
            err_table.add_column("#", style="dim")
            err_table.add_column("Message")
            for i, e in enumerate(data["errors"], 1):
                err_table.add_row(str(i), e)
            console.print(err_table)


# ── Commands ──────────────────────────────────────────────


@app.command("run")
def run(
    symbol: Annotated[str, typer.Argument(help="Trading symbol")],
    exchange: Annotated[str, typer.Argument(help="Exchange (NSE, BSE, NFO, etc.)")],
    csv_path: Annotated[str, typer.Option("--csv", help="Path to OHLCV CSV file")],
    capital: Annotated[
        float, typer.Option("--capital", help="Starting capital")
    ] = 1000000.0,
    risk_profile: Annotated[
        str,
        typer.Option("--risk", help="Risk profile (CONSERVATIVE/MODERATE/AGGRESSIVE)"),
    ] = "MODERATE",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show progress")
    ] = False,
) -> None:
    """Run a backtest on historical CSV data."""
    global _backtest_running, _backtest_start_time

    logger.info("Backtest run command executed")

    if _is_running():
        console.print("[yellow]~[/yellow] A backtest is already running.")
        raise typer.Exit(code=1)

    path = Path(csv_path)

    if verbose:
        _run_with_progress(symbol, exchange, path, capital, risk_profile)
    else:
        _run_silent(symbol, exchange, path, capital, risk_profile)


def _run_silent(
    symbol: str,
    exchange: str,
    csv_path: Path,
    capital: float,
    risk_profile: str,
) -> None:
    global _backtest_running, _backtest_start_time

    _backtest_running = True
    _backtest_start_time = datetime.now(timezone.utc)

    try:
        console.print(f"[cyan]>[/cyan] Loading dataset from {csv_path}...")
        dataset = _load_csv_dataset(csv_path, symbol, exchange)
        console.print(
            f"[cyan]>[/cyan] Dataset loaded: {dataset.bar_count} bars "
            f"({dataset.start_time} to {dataset.end_time})"
        )

        from titan.backtesting.engine import BacktestEngine

        engine = BacktestEngine(
            dataset=dataset,
            total_capital=Decimal(str(capital)),
            risk_profile=risk_profile,
        )

        console.print("[cyan]>[/cyan] Running backtest...")
        report = engine.run()

        entry = _report_to_dict(report)
        _backtest_history.append(entry)

        console.print("[bold green]+[/bold green] Backtest completed.")
        _print_backtest_report(entry, verbose=False)

    except Exception as e:
        console.print(f"[bold red]![/bold red] Backtest failed: {e}")
        _backtest_running = False
        _backtest_start_time = None
        raise typer.Exit(code=3)

    _backtest_running = False
    _backtest_start_time = None


def _run_with_progress(
    symbol: str,
    exchange: str,
    csv_path: Path,
    capital: float,
    risk_profile: str,
) -> None:
    global _backtest_running, _backtest_start_time

    _backtest_running = True
    _backtest_start_time = datetime.now(timezone.utc)

    steps = [
        "Loading dataset",
        "Initializing engine",
        "Running backtest",
        "Computing statistics",
        "Backtest completed",
    ]

    with Live(console=console, refresh_per_second=4) as live:
        for i, step_name in enumerate(steps):
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Step", style="bold")
            table.add_column("Status")
            for j, name in enumerate(steps):
                if j < i:
                    table.add_row(name, "[green]+[/green] done")
                elif j == i:
                    table.add_row(name, "[yellow]...[/yellow]")
                else:
                    table.add_row(name, "[dim]-[/dim]")
            live.update(table)
            time.sleep(0.1)

            if i == 0:
                try:
                    dataset = _load_csv_dataset(csv_path, symbol, exchange)
                except Exception as e:
                    table.add_row(f"Error: {e}", "[bold red]![/bold red]")
                    live.update(table)
                    _backtest_running = False
                    _backtest_start_time = None
                    raise typer.Exit(code=3)

            if i == 1:
                from titan.backtesting.engine import BacktestEngine

                engine = BacktestEngine(
                    dataset=dataset,
                    total_capital=Decimal(str(capital)),
                    risk_profile=risk_profile,
                )

            if i == 2:
                try:
                    report = engine.run()
                except Exception as e:
                    table.add_row(f"Error: {e}", "[bold red]![/bold red]")
                    live.update(table)
                    _backtest_running = False
                    _backtest_start_time = None
                    raise typer.Exit(code=3)

            if i == 3:
                entry = _report_to_dict(report)
                _backtest_history.append(entry)

        for name in steps:
            table.add_row(name, "[green]+[/green] done")
        live.update(table)

    _backtest_running = False
    _backtest_start_time = None

    console.print("[bold green]+[/bold green] Backtest completed.")
    if _backtest_history:
        _print_backtest_report(_backtest_history[-1], verbose=True)


@app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show backtesting subsystem status."""
    logger.info("Backtest status command executed")

    last = _last_result()
    data = last if last else None

    if json_output:
        output: dict[str, Any] = {
            "running": _is_running(),
            "completed_backtests": len(_backtest_history),
        }
        if data is not None:
            output["last_backtest"] = data
        console.print(json.dumps(output, indent=2, default=_json_serial))
        return

    _print_backtest_status(data)


@app.command("report")
def report(
    index: Annotated[
        int, typer.Argument(help="Backtest index (1-based, default: last)")
    ] = 0,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show full details")
    ] = False,
    export: Annotated[
        str | None,
        typer.Option("--export", help="Export report to JSON file"),
    ] = None,
) -> None:
    """Show detailed report for a completed backtest."""
    logger.info("Backtest report command executed")

    if not _backtest_history:
        if json_output:
            console.print(json.dumps({"error": "No completed backtests"}, indent=2))
        else:
            console.print("[dim]No completed backtests to report.[/dim]")
        return

    if index == 0:
        data = _backtest_history[-1]
    elif 1 <= index <= len(_backtest_history):
        data = _backtest_history[index - 1]
    else:
        console.print(
            f"[bold red]![/bold red] Invalid index {index}. "
            f"Valid range: 1-{len(_backtest_history)}"
        )
        raise typer.Exit(code=1)

    if json_output:
        console.print(json.dumps(data, indent=2, default=_json_serial))
    else:
        _print_backtest_report(data, verbose=verbose)

    if export:
        export_path = Path(export)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(
            json.dumps(data, indent=2, default=_json_serial),
            encoding="utf-8",
        )
        console.print(f"[bold green]+[/bold green] Report exported to {export_path}")


@app.command("list")
def list_backtests(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List all completed backtests in this session."""
    logger.info("Backtest list command executed")

    if json_output:
        console.print(
            json.dumps(
                {"backtests": _backtest_history, "count": len(_backtest_history)},
                indent=2,
                default=_json_serial,
            )
        )
        return

    _print_backtest_list()


@app.command("evaluate")
def evaluate(
    strategy: str = typer.Argument(
        None, help="Specific strategy name to evaluate. Evaluates all if omitted."
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Evaluate historical strategy performance and regime breakdown."""
    try:
        from titan.cli.common import get_runtime_engine
        from titan.backtesting.evaluation import StrategyEvaluator

        # Extract historical entries from the central repository
        engine = get_runtime_engine()
        entries = engine.trade_journal.repository.list(page=1, page_size=100000)

        evaluator = StrategyEvaluator()
        report = evaluator.evaluate_trades(entries)

        if json_output:
            import dataclasses
            import json

            def default_serializer(o):
                if hasattr(o, "isoformat"):
                    return o.isoformat()
                return str(o)

            console.print(
                json.dumps(
                    dataclasses.asdict(report), default=default_serializer, indent=2
                )
            )
            return

        if not report.strategies:
            console.print(
                "[yellow]No strategies found in the historical journal.[/yellow]"
            )
            return

        for strat in report.strategies:
            if strategy and strat.strategy_name.lower() != strategy.lower():
                continue

            # Core Performance Table
            table = Table(
                title=f"Strategy Scorecard: {strat.strategy_name}", show_header=False
            )
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Trades", str(strat.total_trades))
            table.add_row("Win Rate", f"{strat.win_rate * 100:.1f}%")
            table.add_row("Profit Factor", f"{strat.profit_factor:.2f}")
            table.add_row("Expectancy", f"{strat.expectancy:.2f}")
            table.add_row("Net PnL", f"₹{strat.net_pnl:,.2f}")
            table.add_row("Max Drawdown", f"₹{strat.max_drawdown:,.2f}")

            console.print(table)

            # Regime Breakdown Table
            if strat.regime_breakdown:
                regime_table = Table(title=f"{strat.strategy_name} - Regime Breakdown")
                regime_table.add_column("Market Regime", style="magenta")
                regime_table.add_column("Trades", justify="right")
                regime_table.add_column("Win Rate", justify="right")
                regime_table.add_column("Profit Factor", justify="right")
                regime_table.add_column("Net PnL", justify="right", style="green")

                for regime, perf in sorted(strat.regime_breakdown.items()):
                    regime_table.add_row(
                        regime,
                        str(perf.total_trades),
                        f"{perf.win_rate * 100:.1f}%",
                        f"{perf.profit_factor:.2f}",
                        f"₹{perf.net_pnl:,.2f}",
                    )
                console.print(regime_table)
                console.print()

    except Exception as e:
        console.print(f"[bold red]Error during strategy evaluation:[/bold red] {e}")
        raise typer.Exit(1)

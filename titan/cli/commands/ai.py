"""CLI commands for AI Assistant Engine."""

import json

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="AI Research Assistant & Synthesizer")
console = Console()


def _get_provider(provider_name: str = "gemini"):
    """Instantiate the requested AI provider."""
    from titan.ai.providers.gemini import GeminiAIProvider, MockAIProvider

    if provider_name.lower() == "mock":
        return MockAIProvider()
    return GeminiAIProvider()


@app.command("portfolio")
def explain_portfolio(
    provider: str = typer.Option(
        "gemini", "--provider", "-p", help="AI provider (gemini or mock)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Generate an AI explanation of current portfolio state."""
    try:
        from titan.ai.engine import AIAssistantEngine
        from titan.cli.commands.portfolio import _get_analytics_data

        analytics, portfolio, _ = _get_analytics_data()
        snapshot = analytics.generate_snapshot(portfolio)

        engine = AIAssistantEngine(provider=_get_provider(provider))
        response = engine.explain_portfolio(snapshot)

        if json_output:
            import dataclasses

            console.print(json.dumps(dataclasses.asdict(response), indent=2))
            return

        console.print(
            Panel(
                response.content,
                title=f"AI Portfolio Analysis ({response.provider_name}:{response.model_name})",
                border_style="cyan",
            )
        )
    except Exception as e:
        console.print(f"[bold red]AI Analysis Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command("strategy")
def explain_strategy(
    provider: str = typer.Option(
        "gemini", "--provider", "-p", help="AI provider (gemini or mock)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Generate an AI synthesis of historical strategy performance."""
    try:
        from titan.ai.engine import AIAssistantEngine
        from titan.backtesting.evaluation import StrategyEvaluator
        from titan.cli.common import get_runtime_engine

        engine_rt = get_runtime_engine()
        entries = engine_rt.trade_journal.repository.list(page=1, page_size=100000)
        evaluator = StrategyEvaluator()
        report = evaluator.evaluate_trades(entries)

        ai_engine = AIAssistantEngine(provider=_get_provider(provider))
        response = ai_engine.explain_strategy_evaluation(report)

        if json_output:
            import dataclasses

            console.print(json.dumps(dataclasses.asdict(response), indent=2))
            return

        console.print(
            Panel(
                response.content,
                title=f"AI Strategy Synthesis ({response.provider_name}:{response.model_name})",
                border_style="magenta",
            )
        )
    except Exception as e:
        console.print(f"[bold red]AI Analysis Error:[/bold red] {e}")
        raise typer.Exit(1)

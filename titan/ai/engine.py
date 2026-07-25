"""AI Assistant Engine.

Orchestrates prompt formatting and delegates to the configured AIProvider.
Converts deterministic TITAN DTOs into structured natural language explanations.
"""

from __future__ import annotations


from titan.ai.base import AIProvider
from titan.ai.models import AIResponse, PromptContext
from titan.ai.providers.gemini import MockAIProvider
from titan.backtesting.evaluation import StrategyEvaluationReport
from titan.portfolio.models import PortfolioSnapshot


class AIAssistantEngine:
    """Central AI Orchestrator that formats snapshots into reasoning context."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or MockAIProvider()

    def explain_portfolio(
        self, snapshot: PortfolioSnapshot, extra_notes: str = ""
    ) -> AIResponse:
        """Format a PortfolioSnapshot DTO into an explanation prompt."""
        system_prompt = (
            "You are TITAN's AI Research Assistant. Explain the provided portfolio snapshot "
            "in clear, concise, institutional terms. Do NOT offer financial advice or recommend "
            "unauthorized trades."
        )
        user_prompt = (
            f"Portfolio Snapshot Details:\n"
            f"- Total Capital: ₹{snapshot.total_capital:,.2f}\n"
            f"- Capital Used: ₹{snapshot.capital_used:,.2f}\n"
            f"- Available Capital: ₹{snapshot.available_capital:,.2f}\n"
            f"- Total P&L: ₹{snapshot.total_pnl:,.2f}\n"
            f"- Capital Utilization: {snapshot.utilization * 100:.1f}%\n"
            f"- Open Positions: {snapshot.position_count}\n"
            f"Extra Context: {extra_notes}"
        )

        context = PromptContext(
            template_name="explain_portfolio",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return self.provider.generate(context)

    def explain_strategy_evaluation(
        self, report: StrategyEvaluationReport
    ) -> AIResponse:
        """Format a StrategyEvaluationReport DTO into a scorecard summary prompt."""
        system_prompt = (
            "You are TITAN's AI Strategy Analyst. Summarize the historical performance "
            "and regime suitability of the evaluated strategies based strictly on the provided report."
        )

        summary_lines = [f"Best Strategy: {report.overall_best_strategy}"]
        for s in report.strategies:
            summary_lines.append(
                f"Strategy '{s.strategy_name}': Trades={s.total_trades}, "
                f"WinRate={s.win_rate*100:.1f}%, ProfitFactor={s.profit_factor:.2f}, "
                f"NetPnL=₹{s.net_pnl:,.2f}, MaxDrawdown=₹{s.max_drawdown:,.2f}"
            )

        user_prompt = "Strategy Performance Summary:\n" + "\n".join(summary_lines)

        context = PromptContext(
            template_name="explain_strategy_evaluation",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return self.provider.generate(context)

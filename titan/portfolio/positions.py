from dataclasses import dataclass

from titan.portfolio.models import ExistingPortfolio, PortfolioSnapshot


@dataclass(slots=True)
class PositionAnalyzer:
    """Analyses open positions and produces a portfolio snapshot.

    Evaluates:
        - Open position count and breakdown.
        - Winning vs losing positions.
        - Total capital used and available.
        - Portfolio utilisation ratio.
    """

    name: str = "PositionAnalyzer"

    def analyze(self, portfolio: ExistingPortfolio) -> PortfolioSnapshot:
        """Produce a snapshot of the current portfolio state.

        Args:
            portfolio: Existing portfolio with open positions.

        Returns:
            Portfolio snapshot with aggregated metrics.
        """
        positions = portfolio.positions
        total_capital = max(portfolio.total_capital, 0.0)
        cash_reserve = max(portfolio.cash_reserve, 0.0)

        capital_used = sum(abs(p.market_value) for p in positions)
        total_market_value = sum(p.market_value for p in positions)
        total_pnl = sum(p.pnl for p in positions)
        position_count = len(positions)
        winning = sum(1 for p in positions if p.pnl > 0.0)
        losing = sum(1 for p in positions if p.pnl < 0.0)

        available_capital = max(total_capital - capital_used - cash_reserve, 0.0)
        utilization = capital_used / total_capital if total_capital > 0.0 else 0.0
        utilization = max(0.0, min(1.0, utilization))

        return PortfolioSnapshot(
            total_capital=total_capital,
            cash_reserve=cash_reserve,
            capital_used=round(capital_used, 2),
            available_capital=round(available_capital, 2),
            total_market_value=round(total_market_value, 2),
            total_pnl=round(total_pnl, 2),
            position_count=position_count,
            winning_positions=winning,
            losing_positions=losing,
            utilization=round(utilization, 4),
        )

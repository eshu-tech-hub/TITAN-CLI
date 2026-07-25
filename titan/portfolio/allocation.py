from dataclasses import dataclass

from titan.portfolio.models import ExistingPortfolio, PortfolioSnapshot


@dataclass(slots=True)
class CapitalAllocationAnalyzer:
    """Analyses portfolio capital allocation and determines remaining capacity.

    Determines:
        - Portfolio utilisation ratio.
        - Cash remaining for new trades.
        - Maximum new allocation based on concentration limits.
        - Capital efficiency (return on deployed capital).
    """

    name: str = "CapitalAllocationAnalyzer"
    max_concentration_pct: float = 0.15

    def analyze(
        self,
        portfolio: ExistingPortfolio,
        snapshot: PortfolioSnapshot,
    ) -> tuple[float, float, float, float]:
        """Analyse capital allocation.

        Args:
            portfolio: Existing portfolio with open positions.
            snapshot: Portfolio snapshot from the PositionAnalyzer.

        Returns:
            Tuple of (remaining_capital, max_new_allocation,
                      capital_efficiency, concentration_headroom).
        """
        remaining_capital = snapshot.available_capital
        max_new_allocation = self._compute_max_new_allocation(
            portfolio, snapshot, remaining_capital
        )
        capital_efficiency = self._compute_efficiency(snapshot)
        concentration_headroom = self._compute_concentration_headroom(
            portfolio, snapshot
        )
        return (
            remaining_capital,
            max_new_allocation,
            capital_efficiency,
            concentration_headroom,
        )

    def _compute_max_new_allocation(
        self,
        portfolio: ExistingPortfolio,
        snapshot: PortfolioSnapshot,
        remaining_capital: float,
    ) -> float:
        if snapshot.utilization >= 1.0:
            return 0.0
        max_allocation = snapshot.total_capital * self.max_concentration_pct
        used = snapshot.capital_used
        headroom = max(max_allocation - used, 0.0)
        return min(remaining_capital, headroom)

    def _compute_efficiency(self, snapshot: PortfolioSnapshot) -> float:
        if snapshot.capital_used <= 0.0:
            return 0.0
        return max(-1.0, min(1.0, snapshot.total_pnl / snapshot.capital_used))

    def _compute_concentration_headroom(
        self,
        portfolio: ExistingPortfolio,
        snapshot: PortfolioSnapshot,
    ) -> float:
        if snapshot.total_capital <= 0.0:
            return 0.0
        max_allowed = snapshot.total_capital * self.max_concentration_pct
        largest_position = 0.0
        if portfolio.positions:
            largest_position = max(abs(p.market_value) for p in portfolio.positions)
        return max(max_allowed - largest_position, 0.0)

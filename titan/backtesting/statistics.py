from dataclasses import dataclass, field
from decimal import Decimal

from titan.backtesting.models import BacktestStatistics


@dataclass(slots=True)
class StatisticsEngine:
    """Computes trading statistics from a sequence of trade P&L values.

    Tracks win/loss counts, profit factor, expectancy, consecutive
    wins/losses, and maximum drawdown from a stream of trade results.

    Attributes:
        _pnls: Accumulated trade P&L values.
        _trade_results: Boolean flags (True = winning trade).
    """

    _pnls: list[Decimal] = field(default_factory=list, init=False)
    _trade_results: list[bool] = field(default_factory=list, init=False)

    def record_trade(self, pnl: Decimal) -> None:
        """Record a completed trade result.

        Args:
            pnl: Realized P&L for the trade.

        Raises:
            StatisticsError: If P&L is invalid.
        """
        self._pnls.append(pnl)
        self._trade_results.append(pnl > Decimal(0))

    def record_trades(self, pnls: list[Decimal]) -> None:
        """Record multiple trade results at once.

        Args:
            pnls: List of realized P&L values.
        """
        for pnl in pnls:
            self.record_trade(pnl)

    def compute(self) -> BacktestStatistics:
        """Compute statistics from all recorded trades.

        Returns:
            BacktestStatistics with computed values.
        """
        total_trades = len(self._pnls)

        if total_trades == 0:
            return BacktestStatistics()

        winning_pnls = [p for p in self._pnls if p > Decimal(0)]
        losing_pnls = [p for p in self._pnls if p < Decimal(0)]

        winning_trades = len(winning_pnls)
        losing_trades = len(losing_pnls)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        loss_rate = losing_trades / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(winning_pnls, Decimal(0))
        gross_loss = abs(sum(losing_pnls, Decimal(0)))
        profit_factor = (
            float(gross_profit / gross_loss) if gross_loss > Decimal(0) else 0.0
        )

        net_pnl = gross_profit - gross_loss
        expectancy = (
            net_pnl / Decimal(str(total_trades)) if total_trades > 0 else Decimal(0)
        )

        average_gain = (
            gross_profit / Decimal(str(winning_trades))
            if winning_trades > 0
            else Decimal(0)
        )
        average_loss = (
            gross_loss / Decimal(str(losing_trades))
            if losing_trades > 0
            else Decimal(0)
        )

        max_consecutive_wins = self._max_consecutive(True)
        max_consecutive_losses = self._max_consecutive(False)

        max_drawdown = self._compute_max_drawdown()

        recovery_factor = (
            float(net_pnl / max_drawdown) if max_drawdown > Decimal(0) else 0.0
        )

        return BacktestStatistics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 4),
            loss_rate=round(loss_rate, 4),
            profit_factor=round(profit_factor, 4),
            average_gain=average_gain.quantize(Decimal("0.01")),
            average_loss=average_loss.quantize(Decimal("0.01")),
            expectancy=expectancy.quantize(Decimal("0.01")),
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            max_drawdown=max_drawdown.quantize(Decimal("0.01")),
            recovery_factor=round(recovery_factor, 4),
        )

    def _max_consecutive(self, winning: bool) -> int:
        """Compute the maximum consecutive wins or losses.

        Args:
            winning: True for consecutive wins, False for losses.

        Returns:
            Maximum consecutive count.
        """
        max_count = 0
        current_count = 0
        for result in self._trade_results:
            if result == winning:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        return max_count

    def _compute_max_drawdown(self) -> Decimal:
        """Compute the maximum peak-to-trough drawdown from P&L values.

        Uses a cumulative equity simulation from the recorded trades.
        """
        if not self._pnls:
            return Decimal(0)

        cumulative = Decimal(0)
        peak = Decimal(0)
        max_drawdown = Decimal(0)

        for pnl in self._pnls:
            cumulative += pnl
            peak = max(peak, cumulative)
            drawdown = peak - cumulative
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def reset(self) -> None:
        """Clear all recorded trade data."""
        self._pnls.clear()
        self._trade_results.clear()

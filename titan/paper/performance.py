from dataclasses import dataclass
from decimal import Decimal

from titan.paper.journal import TradeJournal
from titan.paper.models import (
    PaperOrder,
    PaperPerformanceMetrics,
    PaperPortfolioState,
)


@dataclass(slots=True)
class PerformanceEngine:
    """Computes performance metrics from paper trading history.

    Reads completed trades from the TradeJournal and portfolio
    state to compute standard trading performance metrics.

    Attributes:
        journal: Source of trade data for performance computation.
    """

    journal: TradeJournal | None = None

    def compute(self, portfolio_state: PaperPortfolioState) -> PaperPerformanceMetrics:
        """Compute performance metrics from journal and portfolio data.

        Args:
            portfolio_state: Current portfolio snapshot for drawdown and P&L.

        Returns:
            PaperPerformanceMetrics with all computed values.
        """
        if self.journal is None:
            return PaperPerformanceMetrics()

        trades = self.journal.to_broker_trades()
        orders = self.journal.all_orders()

        total_trades = len(trades)

        winning_pnl: list[Decimal] = []
        losing_pnl: list[Decimal] = []

        for order in orders:
            if order.fills and order.status.value == "filled":
                pnl = self._compute_order_pnl(order)
                if pnl > Decimal(0):
                    winning_pnl.append(pnl)
                elif pnl < Decimal(0):
                    losing_pnl.append(pnl)

        winning_trades = len(winning_pnl)
        losing_trades = len(losing_pnl)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        loss_rate = losing_trades / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(winning_pnl, Decimal(0))
        gross_loss = abs(sum(losing_pnl, Decimal(0)))
        profit_factor = (
            float(gross_profit / gross_loss) if gross_loss > Decimal(0) else 0.0
        )

        net_pnl = gross_profit - gross_loss
        expectancy = (
            net_pnl / Decimal(str(total_trades)) if total_trades > 0 else Decimal(0)
        )

        avg_winner = (
            gross_profit / Decimal(str(winning_trades))
            if winning_trades > 0
            else Decimal(0)
        )
        avg_loser = (
            gross_loss / Decimal(str(losing_trades))
            if losing_trades > 0
            else Decimal(0)
        )

        avg_holding_time = self._compute_avg_holding_time(orders)

        return PaperPerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 4),
            loss_rate=round(loss_rate, 4),
            profit_factor=round(profit_factor, 4),
            expectancy=expectancy.quantize(Decimal("0.01")),
            avg_winner=avg_winner.quantize(Decimal("0.01")),
            avg_loser=avg_loser.quantize(Decimal("0.01")),
            avg_holding_time_seconds=round(avg_holding_time, 2),
            max_drawdown=portfolio_state.drawdown,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
        )

    def _compute_order_pnl(self, order: PaperOrder) -> Decimal:
        """Compute P&L for a completed order."""
        total_buy_value = Decimal(0)
        total_sell_value = Decimal(0)
        buy_qty = 0
        sell_qty = 0

        for fill in order.fills:
            value = fill.price * Decimal(str(fill.quantity))
            if fill.side.value == "buy":
                total_buy_value += value
                buy_qty += fill.quantity
            else:
                total_sell_value += value
                sell_qty += fill.quantity

        if buy_qty == 0 or sell_qty == 0:
            return Decimal(0)

        avg_buy = total_buy_value / Decimal(str(buy_qty))
        avg_sell = total_sell_value / Decimal(str(sell_qty))
        closed_qty = min(buy_qty, sell_qty)
        return (avg_sell - avg_buy) * Decimal(str(closed_qty))

    def _compute_avg_holding_time(self, orders: list[PaperOrder]) -> float:
        """Compute average holding time in seconds for filled orders."""
        total_seconds = 0.0
        count = 0

        for order in orders:
            if order.filled_at is not None and order.placed_at is not None:
                delta = (order.filled_at - order.placed_at).total_seconds()
                total_seconds += delta
                count += 1

        return total_seconds / count if count > 0 else 0.0

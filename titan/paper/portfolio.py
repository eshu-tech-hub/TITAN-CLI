from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from titan.brokers.models import FundsInfo, MarginInfo
from titan.paper.exceptions import PaperPortfolioError
from titan.paper.models import PaperFill, PaperPortfolioState, PaperPosition


@dataclass(slots=True)
class PaperPortfolio:
    """Tracks capital, equity, and P&L for paper trading.

    Maintains a running balance of cash, computes equity based
    on open positions, and tracks P&L and drawdown metrics.

    Attributes:
        initial_cash: Starting cash balance.
        _cash: Current available cash.
        _peak_equity: Highest equity value seen (for drawdown).
        _daily_start_equity: Equity at start of current day.
        _current_day: Current trading day tracker.
    """

    initial_cash: Decimal = Decimal(100000)
    _cash: Decimal = field(init=False)
    _peak_equity: Decimal = field(init=False)
    _daily_start_equity: Decimal = field(init=False)
    _current_day: str = field(init=False)

    def __post_init__(self) -> None:
        self._cash = self.initial_cash
        self._peak_equity = self.initial_cash
        self._daily_start_equity = self.initial_cash
        self._current_day = datetime.now(UTC).strftime("%Y-%m-%d")

    def apply_fill(self, fill: PaperFill) -> None:
        """Update cash balance based on a fill.

        Args:
            fill: The fill to apply.

        Raises:
            PaperPortfolioError: If insufficient cash for a buy.
        """
        trade_value = fill.price * Decimal(str(fill.quantity))
        total_cost = trade_value + fill.commission

        if fill.side.value == "buy":
            if total_cost > self._cash:
                raise PaperPortfolioError(
                    f"Insufficient cash: need {total_cost}, have {self._cash}"
                )
            self._cash -= total_cost
        else:
            self._cash += trade_value - fill.commission

    def compute_state(
        self,
        positions: list[PaperPosition],
    ) -> PaperPortfolioState:
        """Compute a snapshot of the current portfolio state.

        Args:
            positions: Current open positions for valuation.

        Returns:
            A PaperPortfolioState snapshot.
        """
        position_value = Decimal(0)
        for pos in positions:
            if pos.current_price is not None:
                position_value += pos.current_price * Decimal(str(abs(pos.quantity)))

        equity = self._cash + position_value
        daily_pnl = equity - self._daily_start_equity
        total_pnl = equity - self.initial_cash

        self._peak_equity = max(self._peak_equity, equity)

        drawdown = (
            (self._peak_equity - equity) / self._peak_equity
            if self._peak_equity > Decimal(0)
            else Decimal(0)
        )

        buying_power = self._cash
        margin_used = Decimal(0)
        exposure = position_value

        return PaperPortfolioState(
            cash=self._cash,
            equity=equity,
            buying_power=buying_power,
            margin_used=margin_used,
            daily_pnl=daily_pnl,
            total_return=total_pnl,
            total_pnl=total_pnl,
            drawdown=drawdown,
            exposure=exposure,
            position_count=len(positions),
        )

    def to_funds_info(self, state: PaperPortfolioState) -> FundsInfo:
        """Convert portfolio state to broker FundsInfo model.

        Args:
            state: Current portfolio state.

        Returns:
            FundsInfo for broker API compatibility.
        """
        return FundsInfo(
            available_cash=self._cash,
            used_cash=self.initial_cash - self._cash,
            realised_pnl=Decimal(0),
            unrealised_pnl=state.total_pnl,
        )

    def to_margin_info(self) -> MarginInfo:
        """Convert portfolio state to broker MarginInfo model.

        Returns:
            MarginInfo for broker API compatibility.
        """
        return MarginInfo(
            total_margin=self._cash,
            available_margin=self._cash,
        )

    def reset(self, initial_cash: Decimal | None = None) -> None:
        """Reset portfolio to initial state.

        Args:
            initial_cash: New initial cash balance (uses current if None).
        """
        if initial_cash is not None:
            self.initial_cash = initial_cash
        self._cash = self.initial_cash
        self._peak_equity = self.initial_cash
        self._daily_start_equity = self.initial_cash
        self._current_day = datetime.now(UTC).strftime("%Y-%m-%d")

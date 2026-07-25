from dataclasses import dataclass, field
from decimal import Decimal
from math import sqrt

from titan.backtesting.models import BacktestMetrics, EquityPoint


@dataclass(slots=True)
class MetricsEngine:
    """Computes performance metrics from backtest equity curve data.

    Provides annualized return, volatility, Sharpe ratio, Sortino
    ratio, Calmar ratio, and MAR ratio. Placeholder implementations
    are used for advanced metrics that require risk-free rate data
    or higher-frequency return data.

    Attributes:
        _equity_points: Accumulated equity curve points.
    """

    _equity_points: list[EquityPoint] = field(default_factory=list, init=False)

    def record_equity(self, point: EquityPoint) -> None:
        """Record an equity curve point.

        Args:
            point: Equity curve snapshot.
        """
        self._equity_points.append(point)

    def record_equity_many(self, points: list[EquityPoint]) -> None:
        """Record multiple equity curve points at once.

        Args:
            points: List of equity curve snapshots.
        """
        self._equity_points.extend(points)

    def compute(
        self,
        equity_curve: list[EquityPoint] | None = None,
        total_return: Decimal | None = None,
        risk_free_rate: float = 0.05,
        trading_days: int = 252,
    ) -> BacktestMetrics:
        """Compute performance metrics from the equity curve.

        Args:
            equity_curve: Optional equity curve (uses stored if None).
            total_return: Total return as a decimal ratio.
            risk_free_rate: Annual risk-free rate (default 5%).
            trading_days: Number of trading days per year.

        Returns:
            BacktestMetrics with computed values.
        """
        curve = equity_curve if equity_curve is not None else self._equity_points

        if len(curve) < 2:
            return BacktestMetrics()

        initial_equity = float(curve[0].equity)
        final_equity = float(curve[-1].equity)

        if initial_equity <= 0:
            return BacktestMetrics()

        n_points = len(curve)

        daily_returns = self._compute_daily_returns(curve)

        avg_daily_return = (
            sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
        )

        monthly_return = (1 + avg_daily_return) ** 21 - 1
        annualized_return = (1 + avg_daily_return) ** trading_days - 1

        if len(daily_returns) > 1:
            variance = sum((r - avg_daily_return) ** 2 for r in daily_returns) / (
                len(daily_returns) - 1
            )
            daily_volatility = sqrt(variance)
            volatility = daily_volatility * sqrt(trading_days)
        else:
            daily_volatility = 0.0
            volatility = 0.0

        sharpe_ratio = (
            (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0.0
        )

        downside_returns = [r for r in daily_returns if r < 0]
        if downside_returns:
            downside_var = sum(r**2 for r in downside_returns) / len(downside_returns)
            daily_downside_vol = sqrt(downside_var)
            downside_vol = daily_downside_vol * sqrt(trading_days)
            sortino_ratio = (
                (annualized_return - risk_free_rate) / downside_vol
                if downside_vol > 0
                else 0.0
            )
        else:
            sortino_ratio = 0.0

        max_drawdown = self._compute_max_drawdown(curve)
        max_drawdown_float = (
            float(max_drawdown) if isinstance(max_drawdown, Decimal) else max_drawdown
        )

        calmar_ratio = (
            annualized_return / abs(max_drawdown_float)
            if max_drawdown_float != 0
            else 0.0
        )

        years = n_points / trading_days if trading_days > 0 else 1.0
        cagr = (
            (final_equity / initial_equity) ** (1.0 / years) - 1 if years > 0 else 0.0
        )
        mar_ratio = cagr / abs(max_drawdown_float) if max_drawdown_float != 0 else 0.0

        return BacktestMetrics(
            daily_return=round(avg_daily_return, 8),
            monthly_return=round(monthly_return, 6),
            annualized_return=round(annualized_return, 6),
            volatility=round(volatility, 6),
            sharpe_ratio=round(sharpe_ratio, 4),
            sortino_ratio=round(sortino_ratio, 4),
            calmar_ratio=round(calmar_ratio, 4),
            mar_ratio=round(mar_ratio, 4),
        )

    @staticmethod
    def _compute_daily_returns(curve: list[EquityPoint]) -> list[float]:
        """Compute daily return ratios from an equity curve.

        Args:
            curve: Ordered list of equity curve points.

        Returns:
            List of daily return ratios.
        """
        returns: list[float] = []
        for i in range(1, len(curve)):
            prev = float(curve[i - 1].equity)
            curr = float(curve[i].equity)
            if prev > 0:
                returns.append((curr - prev) / prev)
        return returns

    @staticmethod
    def _compute_max_drawdown(curve: list[EquityPoint]) -> Decimal:
        """Compute the maximum drawdown from an equity curve.

        Args:
            curve: Ordered list of equity curve points.

        Returns:
            Maximum drawdown as a Decimal ratio.
        """
        if not curve:
            return Decimal("0")

        peak = curve[0].equity
        max_drawdown = Decimal("0")

        for point in curve:
            if point.equity > peak:
                peak = point.equity
            drawdown = (
                (peak - point.equity) / peak if peak > Decimal("0") else Decimal("0")
            )
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    def reset(self) -> None:
        """Clear all stored equity curve data."""
        self._equity_points.clear()

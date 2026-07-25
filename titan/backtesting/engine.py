from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from typing import Any, Mapping
from uuid import uuid4

from titan.backtesting.clock import SimulationClock
from titan.backtesting.dataset import HistoricalDataset
from titan.backtesting.exceptions import EngineError
from titan.backtesting.metrics import MetricsEngine
from titan.backtesting.models import (
    BacktestBar,
    BacktestReport,
    BacktestStatus,
    EquityPoint,
)
from titan.backtesting.replay import ReplayEngine
from titan.backtesting.statistics import StatisticsEngine
from titan.paper.broker import PaperBroker
from titan.pipeline.pipeline import TradePipeline


@dataclass(slots=True)
class BacktestEngine:
    """Orchestrates a complete backtest run through the TITAN pipeline.

    Replays historical data bar-by-bar, feeding each bar through the
    Trade Pipeline with the Paper Broker for simulated execution. Collects
    pipeline reports, portfolio snapshots, and generates a comprehensive
    BacktestReport.

    Attributes:
        dataset: Historical market data to replay.
        pipeline: Trade Pipeline instance (with optional ExecutionOrchestrator).
        broker: PaperBroker instance for simulated execution.
        clock: SimulationClock controlling time progression.
        replay: ReplayEngine for chronological data access.
        statistics: StatisticsEngine for computing trade stats.
        metrics: MetricsEngine for computing performance metrics.
        risk_profile: Risk profile string passed to pipeline.
        total_capital: Starting capital for the backtest.
        collect_pipeline_reports: Whether to store all pipeline reports.
    """

    dataset: HistoricalDataset
    pipeline: TradePipeline = field(default_factory=TradePipeline)
    broker: PaperBroker = field(default_factory=lambda: PaperBroker())
    clock: SimulationClock = field(default_factory=SimulationClock)
    replay: ReplayEngine | None = field(default=None, init=False)
    statistics: StatisticsEngine = field(default_factory=StatisticsEngine)
    metrics_engine: MetricsEngine = field(default_factory=MetricsEngine)
    risk_profile: str = "MODERATE"
    total_capital: Decimal = Decimal("1000000")
    collect_pipeline_reports: bool = True

    _pipeline_reports: list[Mapping[str, Any]] = field(default_factory=list, init=False)
    _equity_curve: list[EquityPoint] = field(default_factory=list, init=False)
    _warnings: list[str] = field(default_factory=list, init=False)
    _errors: list[str] = field(default_factory=list, init=False)
    _bars_processed: int = field(default=0, init=False)
    _start_time: datetime | None = field(default=None, init=False)
    _end_time: datetime | None = field(default=None, init=False)

    def run(self) -> BacktestReport:
        """Execute the full backtest.

        Returns:
            A comprehensive BacktestReport.

        Raises:
            EngineError: If the backtest cannot start.
        """
        if not self.dataset.bars:
            raise EngineError("Dataset has no bars to backtest.")

        self._pipeline_reports.clear()
        self._equity_curve.clear()
        self._warnings.clear()
        self._errors.clear()
        self._bars_processed = 0
        self._start_time = None
        self._end_time = None

        self.broker.reset()
        self.statistics.reset()
        self.metrics_engine.reset()

        try:
            self.replay = ReplayEngine(dataset=self.dataset, clock=self.clock)
        except Exception as e:
            raise EngineError(f"Failed to initialize replay: {e}") from e

        if not self.broker.is_connected():
            self.broker.connect()

        self._start_time = datetime.now(timezone.utc)
        start_wall = perf_counter()

        backtest_bar = self.replay.start()
        self._process_bar(backtest_bar)

        while not self.replay.is_at_end:
            bar = self.replay.advance()
            if bar is None:
                break
            self._process_bar(bar)

        end_wall = perf_counter()
        self._end_time = datetime.now(timezone.utc)
        duration_seconds = end_wall - start_wall

        state = self.broker.portfolio.compute_state(
            self.broker.position_engine.open_positions(),
        )
        final_equity = state.equity
        total_pnl = final_equity - self.total_capital
        total_return = (
            total_pnl / self.total_capital
            if self.total_capital > Decimal("0")
            else Decimal("0")
        )

        statistics = self.statistics.compute()
        metrics = self.metrics_engine.compute(
            equity_curve=list(self._equity_curve),
            total_return=total_return,
        )

        return BacktestReport(
            backtest_id=str(uuid4()),
            symbol=self.dataset.symbol,
            exchange=self.dataset.exchange.value,
            status=BacktestStatus.COMPLETED,
            bars_processed=self._bars_processed,
            start_time=self._start_time,
            end_time=self._end_time,
            duration_seconds=duration_seconds,
            total_capital=self.total_capital,
            final_equity=final_equity,
            total_pnl=total_pnl,
            total_return=total_return,
            statistics=statistics,
            metrics=metrics,
            equity_curve=tuple(self._equity_curve),
            pipeline_reports=tuple(self._pipeline_reports),
            warnings=tuple(self._warnings),
            errors=tuple(self._errors),
        )

    def _process_bar(self, bar: BacktestBar) -> None:
        """Process a single bar through the pipeline."""
        current_price = ReplayEngine.current_price(bar)
        self.broker.set_price(bar.symbol, current_price)

        market_data = self.replay.get_market_data() if self.replay else None

        try:
            report = self.pipeline.run(
                symbol=bar.symbol,
                exchange=bar.exchange,
                market_data=market_data,
                entry_price=float(current_price),
                underlying_price=float(current_price),
                total_capital=float(self.total_capital),
                abort_on_fatal=False,
            )
        except Exception as e:
            self._errors.append(
                f"Bar {self._bars_processed} ({bar.bar.timestamp}): "
                f"Pipeline error: {e}"
            )
            report = None

        self._bars_processed += 1

        if report is not None and self.collect_pipeline_reports:
            self._pipeline_reports.append(
                {
                    "bar_index": self._bars_processed - 1,
                    "timestamp": bar.bar.timestamp.isoformat(),
                    "status": report.status.value,
                    "decision_action": report.decision_action,
                    "orders_submitted": report.orders_submitted,
                    "orders_accepted": report.orders_accepted,
                    "orders_rejected": report.orders_rejected,
                    "warnings": list(report.warnings),
                    "errors": list(report.errors),
                }
            )

        state = self.broker.portfolio.compute_state(
            self.broker.position_engine.open_positions(),
        )
        peak = max(
            (ep.equity for ep in self._equity_curve),
            default=self.total_capital,
        )
        current_equity = state.equity
        drawdown = (
            (peak - current_equity) / peak if peak > Decimal("0") else Decimal("0")
        )

        equity_point = EquityPoint(
            timestamp=bar.bar.timestamp,
            equity=state.equity,
            cash=state.cash,
            drawdown=drawdown,
        )
        self._equity_curve.append(equity_point)

        if report is not None:
            for w in report.warnings:
                self._warnings.append(f"Bar {self._bars_processed - 1}: {w}")
            for err in report.errors:
                self._errors.append(f"Bar {self._bars_processed - 1}: {err}")

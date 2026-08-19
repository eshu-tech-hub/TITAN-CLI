from datetime import UTC, datetime
from decimal import Decimal

import pytest

from titan.backtesting.clock import SimulationClock
from titan.backtesting.dataset import HistoricalDataset
from titan.backtesting.engine import BacktestEngine
from titan.backtesting.exceptions import (
    BacktestError,
    ClockError,
    DatasetError,
    DatasetValidationError,
    EngineError,
    MetricsError,
    ReplayError,
)
from titan.backtesting.metrics import MetricsEngine
from titan.backtesting.models import (
    BacktestBar,
    BacktestExplanation,
    BacktestMetrics,
    BacktestReport,
    BacktestStatistics,
    BacktestStatus,
    EquityPoint,
    EventSnapshot,
    HistoricalBar,
    NewsSnapshot,
    OptionSnapshot,
)
from titan.backtesting.replay import ReplayEngine
from titan.backtesting.report import generate_evidence, generate_explanation
from titan.backtesting.statistics import StatisticsEngine
from titan.brokers.models import Candle, Exchange
from titan.core.evidence.models import EvidenceCategory

# ── Helpers ───────────────────────────────────────────────────────


def make_bar(
    timestamp: datetime | None = None,
    open: str = "100.0",
    high: str = "105.0",
    low: str = "95.0",
    close: str = "102.0",
    volume: int = 1000,
) -> HistoricalBar:
    return HistoricalBar(
        timestamp=timestamp or datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
        open=Decimal(open),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=volume,
    )


def make_dataset(
    n_bars: int = 5,
    symbol: str = "TEST",
    exchange: Exchange = Exchange.NSE,
) -> HistoricalDataset:
    bars: list[HistoricalBar] = []
    for i in range(n_bars):
        bars.append(
            make_bar(
                timestamp=datetime(2026, 1, 1, 9, 15 + i, tzinfo=UTC),
                close=str(100.0 + i),
            )
        )
    return HistoricalDataset(symbol=symbol, exchange=exchange, bars=bars)


# ── Exceptions ────────────────────────────────────────────────────


class TestBacktestExceptions:
    def test_backtest_error(self) -> None:
        assert issubclass(DatasetError, BacktestError)
        assert issubclass(DatasetValidationError, DatasetError)
        assert issubclass(ClockError, BacktestError)
        assert issubclass(ReplayError, BacktestError)
        assert issubclass(EngineError, BacktestError)
        assert issubclass(MetricsError, BacktestError)

    def test_exception_instantiation(self) -> None:
        assert str(BacktestError("test")) == "test"
        assert str(DatasetError("bad data")) == "bad data"
        assert str(EngineError("engine fail")) == "engine fail"


# ── Models ─────────────────────────────────────────────────────────


class TestHistoricalBar:
    def test_default_construction(self) -> None:
        bar = make_bar()
        assert bar.close == Decimal("102.0")
        assert bar.volume == 1000

    def test_is_frozen(self) -> None:
        bar = make_bar()
        with pytest.raises(AttributeError):
            bar.close = Decimal(200)  # type: ignore[misc]

    def test_open_interest_optional(self) -> None:
        bar = make_bar()
        assert bar.open_interest is None
        bar2 = HistoricalBar(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal(100),
            high=Decimal(110),
            low=Decimal(90),
            close=Decimal(105),
            volume=1000,
            open_interest=500,
        )
        assert bar2.open_interest == 500


class TestBacktestStatistics:
    def test_default_construction(self) -> None:
        s = BacktestStatistics()
        assert s.total_trades == 0
        assert s.win_rate == 0.0
        assert s.profit_factor == 0.0

    def test_is_frozen(self) -> None:
        s = BacktestStatistics()
        with pytest.raises(AttributeError):
            s.total_trades = 10  # type: ignore[misc]

    def test_with_values(self) -> None:
        s = BacktestStatistics(
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            win_rate=0.7,
            profit_factor=2.5,
            expectancy=Decimal("150.00"),
        )
        assert s.total_trades == 10
        assert s.win_rate == 0.7
        assert s.profit_factor == 2.5


class TestBacktestMetrics:
    def test_default_construction(self) -> None:
        m = BacktestMetrics()
        assert m.sharpe_ratio == 0.0
        assert m.sortino_ratio == 0.0

    def test_is_frozen(self) -> None:
        m = BacktestMetrics()
        with pytest.raises(AttributeError):
            m.sharpe_ratio = 1.5  # type: ignore[misc]


class TestBacktestReport:
    def test_default_construction(self) -> None:
        report = BacktestReport(
            backtest_id="test-1",
            symbol="TEST",
            exchange="nse",
            status=BacktestStatus.COMPLETED,
            bars_processed=100,
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 1, 2, tzinfo=UTC),
            duration_seconds=10.5,
            total_capital=Decimal(100000),
            final_equity=Decimal(105000),
            total_pnl=Decimal(5000),
            total_return=Decimal("0.05"),
            statistics=BacktestStatistics(),
            metrics=BacktestMetrics(),
        )
        assert report.bars_processed == 100
        assert report.total_pnl == Decimal(5000)

    def test_is_frozen(self) -> None:
        report = BacktestReport(
            backtest_id="test-2",
            symbol="TEST",
            exchange="nse",
            status=BacktestStatus.PENDING,
            bars_processed=0,
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 1, 1, tzinfo=UTC),
            duration_seconds=0.0,
            total_capital=Decimal(100000),
            final_equity=Decimal(100000),
            total_pnl=Decimal(0),
            total_return=Decimal(0),
            statistics=BacktestStatistics(),
            metrics=BacktestMetrics(),
        )
        with pytest.raises(AttributeError):
            report.total_pnl = Decimal(100)  # type: ignore[misc]


class TestBacktestStatus:
    def test_enum_values(self) -> None:
        assert BacktestStatus.PENDING.value == "pending"
        assert BacktestStatus.RUNNING.value == "running"
        assert BacktestStatus.COMPLETED.value == "completed"
        assert BacktestStatus.FAILED.value == "failed"
        assert BacktestStatus.ABORTED.value == "aborted"


class TestEquityPoint:
    def test_construction(self) -> None:
        ep = EquityPoint(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            equity=Decimal(100000),
            cash=Decimal(50000),
        )
        assert ep.equity == Decimal(100000)
        assert ep.drawdown == Decimal(0)

    def test_is_frozen(self) -> None:
        ep = EquityPoint(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            equity=Decimal(100000),
            cash=Decimal(50000),
        )
        with pytest.raises(AttributeError):
            ep.equity = Decimal(200000)  # type: ignore[misc]


class TestBacktestExplanation:
    def test_default_construction(self) -> None:
        expl = BacktestExplanation()
        assert expl.dataset == ""
        assert expl.summary == ""

    def test_with_data(self) -> None:
        expl = BacktestExplanation(
            dataset="Symbol: TEST on nse, 100 bars",
            simulation="Processed 100 bars in 0.5s",
            performance="Win rate: 60.0%",
            risk="Sharpe: 1.5",
            portfolio="Capital: 100000 -> 105000",
            summary="Backtest completed: P&L=5000",
        )
        assert expl.performance == "Win rate: 60.0%"
        assert expl.summary == "Backtest completed: P&L=5000"


class TestOptionSnapshot:
    def test_construction(self) -> None:
        snap = OptionSnapshot(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            symbol="NIFTY",
            expiry="2026-01-30",
            strike=Decimal(20000),
            option_type="CE",
            open=Decimal(100),
            high=Decimal(110),
            low=Decimal(90),
            close=Decimal(105),
            volume=1000,
            open_interest=5000,
        )
        assert snap.option_type == "CE"
        assert snap.strike == Decimal(20000)

    def test_is_frozen(self) -> None:
        snap = OptionSnapshot(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            symbol="NIFTY",
            expiry="2026-01-30",
            strike=Decimal(20000),
            option_type="CE",
            open=Decimal(100),
            high=Decimal(110),
            low=Decimal(90),
            close=Decimal(105),
            volume=1000,
            open_interest=5000,
        )
        with pytest.raises(AttributeError):
            snap.option_type = "PE"  # type: ignore[misc]


class TestNewsSnapshot:
    def test_construction(self) -> None:
        snap = NewsSnapshot(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            headline="Market up",
            sentiment=0.5,
            source="Reuters",
            symbols=("NIFTY",),
        )
        assert snap.headline == "Market up"
        assert snap.sentiment == 0.5


class TestEventSnapshot:
    def test_construction(self) -> None:
        snap = EventSnapshot(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            event_type="earnings",
            description="Q4 earnings report",
            importance=5,
            symbols=("TEST",),
        )
        assert snap.event_type == "earnings"
        assert snap.importance == 5


# ── Dataset ───────────────────────────────────────────────────────


class TestHistoricalDataset:
    def test_create_from_bars(self) -> None:
        ds = make_dataset(n_bars=3)
        assert len(ds) == 3
        assert ds.symbol == "TEST"
        assert ds.exchange == Exchange.NSE

    def test_empty_bars_raises(self) -> None:
        with pytest.raises(DatasetValidationError):
            HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=[])

    def test_empty_symbol_raises(self) -> None:
        bar = make_bar()
        with pytest.raises(DatasetValidationError):
            HistoricalDataset(symbol="", exchange=Exchange.NSE, bars=[bar])

    def test_negative_price_raises(self) -> None:
        bar = HistoricalBar(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal(-1),
            high=Decimal(10),
            low=Decimal(-1),
            close=Decimal(10),
            volume=100,
        )
        with pytest.raises(DatasetValidationError):
            HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=[bar])

    def test_high_low_violation_raises(self) -> None:
        bar = HistoricalBar(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal(100),
            high=Decimal(95),
            low=Decimal(100),
            close=Decimal(100),
            volume=100,
        )
        with pytest.raises(DatasetValidationError):
            HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=[bar])

    def test_negative_volume_raises(self) -> None:
        bar = HistoricalBar(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal(100),
            high=Decimal(110),
            low=Decimal(90),
            close=Decimal(105),
            volume=-1,
        )
        with pytest.raises(DatasetValidationError):
            HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=[bar])

    def test_non_ascending_timestamps_raises(self) -> None:
        bars = [
            make_bar(timestamp=datetime(2026, 1, 1, 9, 16, tzinfo=UTC)),
            make_bar(timestamp=datetime(2026, 1, 1, 9, 15, tzinfo=UTC)),
        ]
        with pytest.raises(DatasetValidationError):
            HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=bars)

    def test_properties(self) -> None:
        ds = make_dataset(n_bars=3)
        assert ds.bar_count == 3
        assert len(ds.closes) == 3
        assert len(ds.highs) == 3
        assert len(ds.volumes) == 3
        assert ds.start_time == ds.bars[0].timestamp
        assert ds.end_time == ds.bars[-1].timestamp

    def test_iteration(self) -> None:
        ds = make_dataset(n_bars=3)
        count = 0
        for bar in ds:
            count += 1
            assert isinstance(bar, HistoricalBar)
        assert count == 3

    def test_indexing(self) -> None:
        ds = make_dataset(n_bars=3)
        assert ds[0].close == Decimal("100.0")
        assert ds[2].close == Decimal("102.0")

    def test_from_broker_candles(self) -> None:
        candles = [
            Candle(
                datetime=datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
                open=Decimal(100),
                high=Decimal(105),
                low=Decimal(95),
                close=Decimal(102),
                volume=1000,
                oi=500,
            ),
        ]
        ds = HistoricalDataset.from_broker_candles("TEST", Exchange.NSE, candles)
        assert len(ds) == 1
        assert ds.bars[0].open_interest == 500

    def test_to_broker_candles(self) -> None:
        ds = make_dataset(n_bars=2)
        candles = ds.to_broker_candles()
        assert len(candles) == 2
        assert isinstance(candles[0], Candle)

    def test_resample(self) -> None:
        bars: list[HistoricalBar] = []
        for i in range(10):
            bars.append(
                make_bar(
                    timestamp=datetime(2026, 1, 1, 9, 15 + i, tzinfo=UTC),
                    high=str(105 + i),
                    low=str(95 - i),
                    close=str(102 + i),
                )
            )
        ds = HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=bars)
        resampled = ds.resample(interval_minutes=5)
        assert len(resampled) < len(ds)

    def test_resample_invalid_interval(self) -> None:
        ds = make_dataset(n_bars=3)
        with pytest.raises(DatasetValidationError):
            ds.resample(interval_minutes=0)


# ── Simulation Clock ──────────────────────────────────────────────


class TestSimulationClock:
    def test_initialize(self) -> None:
        clock = SimulationClock()
        times = [
            datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
        ]
        clock.initialize(total_bars=2, start_time=times[0], bar_times=times)
        assert clock.current_index == 0
        assert clock.current_time == times[0]
        assert not clock.is_paused
        assert not clock.is_at_end

    def test_initialize_zero_bars_raises(self) -> None:
        clock = SimulationClock()
        with pytest.raises(ClockError):
            clock.initialize(total_bars=0, start_time=datetime.now(), bar_times=[])

    def test_initialize_mismatched_length_raises(self) -> None:
        clock = SimulationClock()
        times = [datetime(2026, 1, 1, tzinfo=UTC)]
        with pytest.raises(ClockError):
            clock.initialize(total_bars=5, start_time=times[0], bar_times=times)

    def test_next_bar(self) -> None:
        clock = SimulationClock()
        times = [
            datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
        ]
        clock.initialize(total_bars=2, start_time=times[0], bar_times=times)
        assert clock.next_bar()
        assert clock.current_index == 1
        assert clock.current_time == times[1]
        assert clock.is_at_end

    def test_next_bar_at_end(self) -> None:
        clock = SimulationClock()
        times = [datetime(2026, 1, 1, 9, 15, tzinfo=UTC)]
        clock.initialize(total_bars=1, start_time=times[0], bar_times=times)
        assert not clock.next_bar()

    def test_previous_bar(self) -> None:
        clock = SimulationClock()
        times = [
            datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
        ]
        clock.initialize(total_bars=2, start_time=times[0], bar_times=times)
        clock.next_bar()
        assert clock.previous_bar()
        assert clock.current_index == 0

    def test_previous_at_start(self) -> None:
        clock = SimulationClock()
        times = [datetime(2026, 1, 1, 9, 15, tzinfo=UTC)]
        clock.initialize(total_bars=1, start_time=times[0], bar_times=times)
        assert not clock.previous_bar()

    def test_seek(self) -> None:
        clock = SimulationClock()
        times = [
            datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 17, tzinfo=UTC),
        ]
        clock.initialize(total_bars=3, start_time=times[0], bar_times=times)
        clock.seek(2)
        assert clock.current_index == 2
        assert clock.current_time == times[2]

    def test_seek_out_of_range_raises(self) -> None:
        clock = SimulationClock()
        times = [datetime(2026, 1, 1, 9, 15, tzinfo=UTC)]
        clock.initialize(total_bars=1, start_time=times[0], bar_times=times)
        with pytest.raises(ClockError):
            clock.seek(5)

    def test_pause_resume(self) -> None:
        clock = SimulationClock()
        times = [
            datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
        ]
        clock.initialize(total_bars=2, start_time=times[0], bar_times=times)
        clock.pause()
        assert clock.is_paused
        assert clock.next_bar()
        assert clock.current_index == 0
        clock.resume()
        assert not clock.is_paused
        assert clock.next_bar()
        assert clock.current_index == 1

    def test_progress(self) -> None:
        clock = SimulationClock()
        times = [
            datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 17, tzinfo=UTC),
        ]
        clock.initialize(total_bars=3, start_time=times[0], bar_times=times)
        assert clock.progress == 0.0
        clock.next_bar()
        assert clock.progress == 0.5
        clock.next_bar()
        assert clock.progress == 1.0

    def test_reset(self) -> None:
        clock = SimulationClock()
        times = [
            datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
        ]
        clock.initialize(total_bars=2, start_time=times[0], bar_times=times)
        clock.next_bar()
        clock.reset()
        assert clock.current_index == 0
        assert clock.current_time == times[0]


# ── Replay Engine ─────────────────────────────────────────────────


class TestReplayEngine:
    def test_initialization(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        assert engine.current_index == 0
        assert not engine.is_at_end

    def test_empty_dataset_raises(self) -> None:
        ds = HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=[make_bar()])
        ds.bars.clear()
        with pytest.raises(ReplayError):
            ReplayEngine(dataset=ds)  # type: ignore[arg-type]

    def test_start_returns_first_bar(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        bar = engine.start()
        assert isinstance(bar, BacktestBar)
        assert bar.symbol == "TEST"
        assert bar.exchange == Exchange.NSE

    def test_start_twice_raises(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        engine.start()
        with pytest.raises(ReplayError):
            engine.start()

    def test_advance_before_start_raises(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        with pytest.raises(ReplayError):
            engine.advance()

    def test_advance_through_bars(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        engine.start()
        bar2 = engine.advance()
        assert bar2 is not None
        assert bar2.bar.close == Decimal("101.0")
        bar3 = engine.advance()
        assert bar3 is not None
        assert bar3.bar.close == Decimal("102.0")
        assert engine.advance() is None

    def test_is_at_end(self) -> None:
        ds = make_dataset(n_bars=2)
        engine = ReplayEngine(dataset=ds)
        engine.start()
        assert not engine.is_at_end
        engine.advance()
        assert engine.is_at_end

    def test_seek(self) -> None:
        ds = make_dataset(n_bars=5)
        engine = ReplayEngine(dataset=ds)
        bar = engine.seek(3)
        assert bar.bar.close == Decimal("103.0")
        assert engine.current_index == 3

    def test_reset(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        engine.start()
        engine.advance()
        engine.reset()
        assert engine.current_bar is None
        assert engine.current_index == 0

    def test_get_market_data(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        assert len(engine.get_market_data()) == 0
        engine.start()
        md = engine.get_market_data()
        assert len(md) == 1
        assert md.closes[0] == 100.0

    def test_get_market_data_before_start(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = ReplayEngine(dataset=ds)
        md = engine.get_market_data()
        assert len(md) == 0

    def test_get_bars_since(self) -> None:
        ds = make_dataset(n_bars=5)
        engine = ReplayEngine(dataset=ds)
        engine.start()
        engine.advance()
        engine.advance()
        window = engine.get_bars_since(lookback=2)
        assert len(window) == 2

    def test_progress(self) -> None:
        ds = make_dataset(n_bars=4)
        engine = ReplayEngine(dataset=ds)
        engine.start()
        assert engine.progress == 0.0
        engine.advance()
        assert engine.progress == pytest.approx(1 / 3)
        engine.advance()
        assert engine.progress == pytest.approx(2 / 3)
        engine.advance()
        assert engine.progress == 1.0

    def test_historical_bar_to_market(self) -> None:
        bar = make_bar()
        mc = ReplayEngine.historical_bar_to_market(bar)
        assert mc.close == 102.0
        assert mc.volume == 1000

    def test_current_price(self) -> None:
        ds = make_dataset(n_bars=1)
        engine = ReplayEngine(dataset=ds)
        bar = engine.start()
        price = ReplayEngine.current_price(bar)
        assert price == Decimal("100.0")


# ── Statistics Engine ─────────────────────────────────────────────


class TestStatisticsEngine:
    def test_initial_empty(self) -> None:
        se = StatisticsEngine()
        stats = se.compute()
        assert stats.total_trades == 0

    def test_single_winning_trade(self) -> None:
        se = StatisticsEngine()
        se.record_trade(Decimal(100))
        stats = se.compute()
        assert stats.total_trades == 1
        assert stats.winning_trades == 1
        assert stats.win_rate == 1.0

    def test_single_losing_trade(self) -> None:
        se = StatisticsEngine()
        se.record_trade(Decimal(-50))
        stats = se.compute()
        assert stats.total_trades == 1
        assert stats.losing_trades == 1
        assert stats.loss_rate == 1.0

    def test_profit_factor(self) -> None:
        se = StatisticsEngine()
        se.record_trades([Decimal(200), Decimal(-50), Decimal(100)])
        stats = se.compute()
        assert stats.total_trades == 3
        assert stats.winning_trades == 2
        assert stats.profit_factor == pytest.approx(6.0)

    def test_expectancy(self) -> None:
        se = StatisticsEngine()
        se.record_trades([Decimal(100), Decimal(-30), Decimal(50)])
        stats = se.compute()
        assert stats.expectancy == Decimal("40.00")

    def test_max_consecutive_wins(self) -> None:
        se = StatisticsEngine()
        se.record_trades(
            [
                Decimal(100),
                Decimal(50),
                Decimal(-30),
                Decimal(20),
                Decimal(10),
                Decimal(-10),
            ]
        )
        stats = se.compute()
        assert stats.max_consecutive_wins == 2

    def test_max_consecutive_losses(self) -> None:
        se = StatisticsEngine()
        se.record_trades(
            [
                Decimal(-10),
                Decimal(-20),
                Decimal(100),
                Decimal(-5),
                Decimal(-5),
            ]
        )
        stats = se.compute()
        assert stats.max_consecutive_losses == 2

    def test_max_drawdown(self) -> None:
        se = StatisticsEngine()
        se.record_trades(
            [
                Decimal(100),
                Decimal(-50),
                Decimal(200),
                Decimal(-100),
            ]
        )
        stats = se.compute()
        assert stats.max_drawdown > Decimal(0)

    def test_recovery_factor(self) -> None:
        se = StatisticsEngine()
        se.record_trades([Decimal(200), Decimal(-50)])
        stats = se.compute()
        assert stats.recovery_factor > 0

    def test_averages(self) -> None:
        se = StatisticsEngine()
        se.record_trades([Decimal(100), Decimal(-50), Decimal(200), Decimal(-30)])
        stats = se.compute()
        assert stats.average_gain == Decimal("150.00")
        assert stats.average_loss == Decimal("40.00")

    def test_reset(self) -> None:
        se = StatisticsEngine()
        se.record_trade(Decimal(100))
        se.reset()
        stats = se.compute()
        assert stats.total_trades == 0


# ── Metrics Engine ────────────────────────────────────────────────


class TestMetricsEngine:
    def test_initial_empty(self) -> None:
        me = MetricsEngine()
        metrics = me.compute()
        assert metrics.sharpe_ratio == 0.0

    def test_insufficient_data(self) -> None:
        me = MetricsEngine()
        curve = [
            EquityPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                equity=Decimal(100000),
                cash=Decimal(100000),
            ),
        ]
        metrics = me.compute(equity_curve=curve)
        assert metrics.sharpe_ratio == 0.0

    def test_basic_metrics(self) -> None:
        me = MetricsEngine()
        curve = [
            EquityPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                equity=Decimal(100000),
                cash=Decimal(100000),
            ),
            EquityPoint(
                timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                equity=Decimal(101000),
                cash=Decimal(99000),
            ),
            EquityPoint(
                timestamp=datetime(2026, 1, 3, tzinfo=UTC),
                equity=Decimal(102000),
                cash=Decimal(98000),
            ),
        ]
        metrics = me.compute(equity_curve=curve)
        assert metrics.daily_return > 0
        assert metrics.annualized_return > 0
        assert metrics.sharpe_ratio != 0.0

    def test_negative_return(self) -> None:
        me = MetricsEngine()
        curve = [
            EquityPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                equity=Decimal(100000),
                cash=Decimal(100000),
            ),
            EquityPoint(
                timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                equity=Decimal(99000),
                cash=Decimal(99000),
            ),
        ]
        metrics = me.compute(equity_curve=curve)
        assert metrics.daily_return < 0

    def test_max_drawdown(self) -> None:
        curve = [
            EquityPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                equity=Decimal(100000),
                cash=Decimal(100000),
            ),
            EquityPoint(
                timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                equity=Decimal(110000),
                cash=Decimal(100000),
            ),
            EquityPoint(
                timestamp=datetime(2026, 1, 3, tzinfo=UTC),
                equity=Decimal(95000),
                cash=Decimal(90000),
            ),
            EquityPoint(
                timestamp=datetime(2026, 1, 4, tzinfo=UTC),
                equity=Decimal(105000),
                cash=Decimal(100000),
            ),
        ]
        dd = MetricsEngine._compute_max_drawdown(curve)
        assert dd > Decimal(0)

    def test_record_equity(self) -> None:
        me = MetricsEngine()
        ep = EquityPoint(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            equity=Decimal(100000),
            cash=Decimal(100000),
        )
        me.record_equity(ep)
        assert len(me._equity_points) == 1

    def test_record_equity_many(self) -> None:
        me = MetricsEngine()
        points = [
            EquityPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                equity=Decimal(100000),
                cash=Decimal(100000),
            ),
            EquityPoint(
                timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                equity=Decimal(101000),
                cash=Decimal(99000),
            ),
        ]
        me.record_equity_many(points)
        assert len(me._equity_points) == 2

    def test_reset(self) -> None:
        me = MetricsEngine()
        me.record_equity(
            EquityPoint(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                equity=Decimal(100000),
                cash=Decimal(100000),
            )
        )
        me.reset()
        assert len(me._equity_points) == 0


# ── Evidence & Explanation Generation ─────────────────────────────


class TestEvidenceGeneration:
    def test_generate_evidence_default(self) -> None:
        report = BacktestReport(
            backtest_id="test",
            symbol="TEST",
            exchange="nse",
            status=BacktestStatus.COMPLETED,
            bars_processed=0,
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 1, 1, tzinfo=UTC),
            duration_seconds=0.0,
            total_capital=Decimal(100000),
            final_equity=Decimal(100000),
            total_pnl=Decimal(0),
            total_return=Decimal(0),
            statistics=BacktestStatistics(),
            metrics=BacktestMetrics(),
        )
        evidence = generate_evidence(report)
        assert evidence.category == EvidenceCategory.SYSTEM
        assert evidence.source == "titan.backtesting"

    def test_generate_evidence_profitable(self) -> None:
        report = BacktestReport(
            backtest_id="test",
            symbol="TEST",
            exchange="nse",
            status=BacktestStatus.COMPLETED,
            bars_processed=100,
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 1, 2, tzinfo=UTC),
            duration_seconds=1.5,
            total_capital=Decimal(100000),
            final_equity=Decimal(105000),
            total_pnl=Decimal(5000),
            total_return=Decimal("0.05"),
            statistics=BacktestStatistics(total_trades=10, win_rate=0.6),
            metrics=BacktestMetrics(sharpe_ratio=1.5),
        )
        evidence = generate_evidence(report)
        assert evidence.category == EvidenceCategory.SYSTEM
        assert "5000" in str(evidence.reasons)

    def test_generate_evidence_loss(self) -> None:
        report = BacktestReport(
            backtest_id="test",
            symbol="TEST",
            exchange="nse",
            status=BacktestStatus.COMPLETED,
            bars_processed=50,
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 1, 2, tzinfo=UTC),
            duration_seconds=1.0,
            total_capital=Decimal(100000),
            final_equity=Decimal(95000),
            total_pnl=Decimal(-5000),
            total_return=Decimal("-0.05"),
            statistics=BacktestStatistics(),
            metrics=BacktestMetrics(),
        )
        evidence = generate_evidence(report)
        assert "-5000" in str(evidence.reasons)

    def test_generate_explanation_default(self) -> None:
        report = BacktestReport(
            backtest_id="test",
            symbol="TEST",
            exchange="nse",
            status=BacktestStatus.COMPLETED,
            bars_processed=0,
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 1, 1, tzinfo=UTC),
            duration_seconds=0.0,
            total_capital=Decimal(100000),
            final_equity=Decimal(100000),
            total_pnl=Decimal(0),
            total_return=Decimal(0),
            statistics=BacktestStatistics(),
            metrics=BacktestMetrics(),
        )
        expl = generate_explanation(report)
        assert isinstance(expl, BacktestExplanation)
        assert expl.dataset != ""

    def test_generate_explanation_with_trades(self) -> None:
        report = BacktestReport(
            backtest_id="test",
            symbol="TEST",
            exchange="nse",
            status=BacktestStatus.COMPLETED,
            bars_processed=100,
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 1, 2, tzinfo=UTC),
            duration_seconds=2.0,
            total_capital=Decimal(100000),
            final_equity=Decimal(110000),
            total_pnl=Decimal(10000),
            total_return=Decimal("0.10"),
            statistics=BacktestStatistics(
                total_trades=20, winning_trades=12, win_rate=0.6, profit_factor=2.0
            ),
            metrics=BacktestMetrics(
                sharpe_ratio=1.5, sortino_ratio=2.0, volatility=0.15
            ),
        )
        expl = generate_explanation(report)
        assert "20" in expl.performance
        assert "SHARPE" in expl.risk.upper() or "Sharpe" in expl.risk


# ── Backtest Engine ───────────────────────────────────────────────


class TestBacktestEngine:
    def test_empty_dataset_raises(self) -> None:
        ds = HistoricalDataset(symbol="TEST", exchange=Exchange.NSE, bars=[make_bar()])
        ds.bars.clear()
        engine = BacktestEngine(dataset=ds)  # type: ignore[arg-type]
        with pytest.raises(EngineError):
            engine.run()

    def test_backtest_with_data(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds)
        report = engine.run()
        assert report.status == BacktestStatus.COMPLETED
        assert report.bars_processed == 3
        assert report.symbol == "TEST"
        assert report.total_capital == Decimal(1000000)

    def test_equity_curve_generated(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds)
        report = engine.run()
        assert len(report.equity_curve) == 3

    def test_pipeline_reports_collected(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds, collect_pipeline_reports=True)
        report = engine.run()
        assert len(report.pipeline_reports) > 0

    def test_pipeline_reports_disabled(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds, collect_pipeline_reports=False)
        report = engine.run()
        assert len(report.pipeline_reports) == 0

    def test_custom_capital(self) -> None:
        ds = make_dataset(n_bars=2)
        engine = BacktestEngine(dataset=ds, total_capital=Decimal(500000))
        report = engine.run()
        assert report.total_capital == Decimal(500000)

    def test_statistics_in_report(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds)
        report = engine.run()
        assert isinstance(report.statistics, BacktestStatistics)

    def test_metrics_in_report(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds)
        report = engine.run()
        assert isinstance(report.metrics, BacktestMetrics)

    def test_custom_pipeline(self) -> None:
        from titan.pipeline.pipeline import TradePipeline

        ds = make_dataset(n_bars=2)
        pipeline = TradePipeline()
        engine = BacktestEngine(dataset=ds, pipeline=pipeline)
        report = engine.run()
        assert report.status == BacktestStatus.COMPLETED

    def test_broker_connectivity(self) -> None:
        from titan.paper.broker import PaperBroker

        ds = make_dataset(n_bars=2)
        broker = PaperBroker(initial_cash=Decimal(500000))
        engine = BacktestEngine(
            dataset=ds,
            broker=broker,
            total_capital=Decimal(500000),
        )
        report = engine.run()
        assert report.total_capital == Decimal(500000)
        assert broker.is_connected()

    def test_multiple_runs(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds)
        report1 = engine.run()
        assert report1.bars_processed == 3
        report2 = engine.run()
        assert report2.bars_processed == 3

    def test_duration_positive(self) -> None:
        ds = make_dataset(n_bars=3)
        engine = BacktestEngine(dataset=ds)
        report = engine.run()
        assert report.duration_seconds > 0

    def test_custom_risk_profile(self) -> None:
        ds = make_dataset(n_bars=2)
        engine = BacktestEngine(dataset=ds, risk_profile="AGGRESSIVE")
        report = engine.run()
        assert report.status == BacktestStatus.COMPLETED


# ── BacktestBar Model ─────────────────────────────────────────────


class TestBacktestBar:
    def test_construction(self) -> None:
        bar = make_bar()
        bbar = BacktestBar(bar=bar, symbol="TEST", exchange=Exchange.NSE)
        assert bbar.bar.close == Decimal("102.0")
        assert bbar.symbol == "TEST"

    def test_with_snapshots(self) -> None:
        bar = make_bar()
        opt = OptionSnapshot(
            timestamp=bar.timestamp,
            symbol="NIFTY",
            expiry="2026-01-30",
            strike=Decimal(20000),
            option_type="CE",
            open=Decimal(100),
            high=Decimal(110),
            low=Decimal(90),
            close=Decimal(105),
            volume=1000,
            open_interest=5000,
        )
        news = NewsSnapshot(
            timestamp=bar.timestamp,
            headline="Test news",
        )
        event = EventSnapshot(
            timestamp=bar.timestamp,
            event_type="test",
        )
        bbar = BacktestBar(
            bar=bar,
            symbol="TEST",
            exchange=Exchange.NSE,
            option_snapshots=(opt,),
            news_snapshots=(news,),
            event_snapshots=(event,),
        )
        assert len(bbar.option_snapshots) == 1
        assert len(bbar.news_snapshots) == 1
        assert len(bbar.event_snapshots) == 1

    def test_is_frozen(self) -> None:
        bar = make_bar()
        bbar = BacktestBar(bar=bar, symbol="TEST", exchange=Exchange.NSE)
        with pytest.raises(AttributeError):
            bbar.symbol = "OTHER"  # type: ignore[misc]

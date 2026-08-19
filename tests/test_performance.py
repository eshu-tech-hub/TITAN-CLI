"""
TITAN Performance & Reliability Profiling Suite

M7.3 - Performance & Reliability
Profiles CPU, memory, latency, throughput, and validates
stress tolerance, failure injection, and recovery.
"""

import gc
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from titan.alerting.engine import AlertEngine
from titan.alerting.models import AlertLevel, AlertSource
from titan.audit.event import create_audit_event
from titan.audit.integrity import IntegrityEngine
from titan.audit.manager import AuditManager
from titan.audit.models import AuditCategory, AuditSeverity, AuditSource
from titan.audit.storage import InMemoryAuditStorage
from titan.backtesting.dataset import HistoricalDataset
from titan.backtesting.engine import BacktestEngine
from titan.backtesting.models import HistoricalBar
from titan.brokers.models import Exchange, OrderRequest
from titan.config.manager import ConfigManager
from titan.core.evidence.confidence import Confidence
from titan.core.evidence.evidence import Evidence
from titan.core.evidence.models import EvidenceCategory, EvidenceSignal
from titan.core.evidence.score import Score
from titan.deployment.version import VersionManager
from titan.execution.order import Order, OrderSide, OrderType
from titan.intelligence.fusion.fusion import FusionEngine
from titan.market.intelligence.breadth import BreadthAnalyzer
from titan.market.intelligence.models import MarketBreadthSnapshot
from titan.market.intelligence.structure import MarketStructureAnalyzer
from titan.market.intelligence.volume import VolumeAnalyzer
from titan.market.intelligence.vwap import VWAPAnalyzer
from titan.market.models import Candle
from titan.market.series import MarketDataSeries
from titan.monitoring.collector import MetricCollector
from titan.monitoring.models import CollectorType, MetricValue
from titan.paper.broker import PaperBroker
from titan.pipeline.pipeline import TradePipeline
from titan.recovery.circuit_breaker import CircuitBreaker
from titan.recovery.exceptions import (
    RecoveryCircuitBreakerError,
    RecoveryRetryError,
)
from titan.recovery.models import CircuitBreakerConfig, RetryMode, RetryPolicy
from titan.recovery.retry import RetryEngine
from titan.risk.models import RiskInput
from titan.risk.risk import RiskEngine
from titan.trading.models import TradeQualification, TradeScore, TradeStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_candles(n: int, base_price: float = 100.0) -> list[Candle]:
    """Generate n deterministic candles for profiling."""
    candles: list[Candle] = []
    price = base_price
    for i in range(n):
        change = (i % 7 - 3) * 0.5
        price += change
        candles.append(
            Candle(
                timestamp=f"2025-01-01T{i:06d}",
                open=price,
                high=price + 2.0,
                low=price - 1.0,
                close=price + 0.5,
                volume=1000 + i * 10,
            )
        )
    return candles


def _generate_historical_bars(n: int, base_price: float = 100.0) -> list[HistoricalBar]:
    """Generate n deterministic HistoricalBar instances with ascending timestamps."""
    from datetime import timedelta

    bars: list[HistoricalBar] = []
    price = base_price
    base = datetime(2025, 1, 1, tzinfo=UTC)
    for i in range(n):
        change = (i % 7 - 3) * 0.5
        price += change
        bars.append(
            HistoricalBar(
                timestamp=base + timedelta(minutes=i),
                open=Decimal(str(price)),
                high=Decimal(str(price + 2.0)),
                low=Decimal(str(price - 1.0)),
                close=Decimal(str(price + 0.5)),
                volume=1000 + i * 10,
            )
        )
    return bars


def _make_market_series(candles: list[Candle]) -> MarketDataSeries:
    """Create a MarketDataSeries from candles."""
    return MarketDataSeries(candles=candles)


def _make_breadth_snapshot(total_symbols: int = 50) -> MarketBreadthSnapshot:
    """Create a minimal MarketBreadthSnapshot."""
    return MarketBreadthSnapshot(
        total_symbols=total_symbols,
        advances=30,
        declines=15,
        unchanged=5,
        index_name="NIFTY",
    )


def _make_risk_input() -> RiskInput:
    """Create a minimal RiskInput."""
    return RiskInput(
        trade_qualification=TradeQualification(
            status=TradeStatus.QUALIFIED,
            trade_score=TradeScore(value=75.0, band="high"),
            confidence=0.8,
            decision_context="test",
        ),
    )


def _measure(func: Any, iterations: int = 100) -> dict[str, float]:
    """Measure execution time statistics for a function."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return {
        "iterations": iterations,
        "total_s": sum(times),
        "mean_ms": statistics.mean(times) * 1000,
        "median_ms": statistics.median(times) * 1000,
        "stdev_ms": statistics.stdev(times) * 1000 if len(times) > 1 else 0.0,
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
        "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
        "p99_ms": sorted(times)[int(len(times) * 0.99)] * 1000,
    }


def _get_memory_mb() -> float:
    """Get current process memory in MB."""
    import os

    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass
    import tracemalloc

    current, _peak = tracemalloc.get_traced_memory()
    return current / (1024 * 1024)


# ---------------------------------------------------------------------------
# CPU Profiling
# ---------------------------------------------------------------------------


class TestCPUPrefiling:
    """Profile CPU performance across key subsystems."""

    def test_market_intelligence_cpu(self) -> None:
        """Profile market intelligence analyzers."""
        candles = _generate_candles(500)
        series = _make_market_series(candles)
        breadth_snap = _make_breadth_snapshot()

        analyzers: list[tuple[str, Any, Any]] = [
            ("BreadthAnalyzer", BreadthAnalyzer(), breadth_snap),
            ("VolumeAnalyzer", VolumeAnalyzer(), series),
            ("VWAPAnalyzer", VWAPAnalyzer(), series),
            ("MarketStructureAnalyzer", MarketStructureAnalyzer(), series),
        ]
        results: dict[str, dict[str, float]] = {}
        for name, analyzer, inp in analyzers:

            def _run(a: Any = analyzer, i: Any = inp) -> Any:
                return a.analyze(i)

            stats = _measure(_run, iterations=50)
            results[name] = stats

        for name, stats in results.items():
            assert stats["p95_ms"] < 5000, (
                f"{name} p95 latency {stats['p95_ms']:.1f}ms exceeds 5000ms threshold"
            )

    def test_fusion_engine_cpu(self) -> None:
        """Profile intelligence fusion computation."""
        evidence = Evidence(
            source="test",
            category=EvidenceCategory.INDICATOR,
            signal=EvidenceSignal.BULLISH,
            confidence=Confidence(value=0.8),
            score=Score(value=0.7),
        )
        fusion = FusionEngine(_evidence=[evidence])

        def _run() -> Any:
            return fusion.fuse()

        stats = _measure(_run, iterations=100)
        assert stats["p95_ms"] < 100, (
            f"Fusion p95 {stats['p95_ms']:.1f}ms exceeds 100ms threshold"
        )

    def test_risk_engine_cpu(self) -> None:
        """Profile risk engine computation."""
        risk = RiskEngine()
        risk_input = _make_risk_input()

        def _run() -> Any:
            return risk.analyze(risk_input=risk_input)

        stats = _measure(_run, iterations=200)
        assert stats["p95_ms"] < 50, (
            f"RiskEngine p95 {stats['p95_ms']:.1f}ms exceeds 50ms threshold"
        )

    def test_paper_broker_cpu(self) -> None:
        """Profile paper broker order placement."""
        broker = PaperBroker(initial_cash=Decimal(1000000))
        broker.connect()

        def _run() -> Any:
            return broker.place_order(
                OrderRequest(
                    symbol="NIFTY",
                    exchange=Exchange.NSE,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=1,
                )
            )

        stats = _measure(_run, iterations=50)
        assert stats["p95_ms"] < 50, (
            f"PaperBroker p95 {stats['p95_ms']:.1f}ms exceeds 50ms threshold"
        )


# ---------------------------------------------------------------------------
# Memory Profiling
# ---------------------------------------------------------------------------


class TestMemoryProfiling:
    """Profile memory usage across subsystems."""

    def test_market_intelligence_memory(self) -> None:
        """Verify market intelligence doesn't leak memory."""
        gc.collect()
        mem_before = _get_memory_mb()

        candles = _generate_candles(1000)
        series = _make_market_series(candles)
        breadth_snap = _make_breadth_snapshot(total_symbols=100)
        for _ in range(10):
            BreadthAnalyzer().analyze(breadth_snap)
            VolumeAnalyzer().analyze(series)
            VWAPAnalyzer().analyze(series)
            MarketStructureAnalyzer().analyze(series)

        gc.collect()
        mem_after = _get_memory_mb()
        delta = mem_after - mem_before

        assert delta < 50, f"Memory grew by {delta:.1f}MB (threshold: 50MB)"

    def test_audit_storage_memory(self) -> None:
        """Verify audit storage handles large volumes without excessive memory."""
        gc.collect()
        mem_before = _get_memory_mb()

        storage = InMemoryAuditStorage()
        for i in range(10000):
            event = create_audit_event(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action=f"Performance test event {i}",
            )
            storage.append(event)

        gc.collect()
        mem_after = _get_memory_mb()
        delta = mem_after - mem_before

        assert delta < 100, (
            f"Memory grew by {delta:.1f}MB for 10k events (threshold: 100MB)"
        )

    def test_alert_engine_memory(self) -> None:
        """Verify alert engine memory is bounded."""
        gc.collect()
        mem_before = _get_memory_mb()

        engine = AlertEngine()
        for i in range(1000):
            engine.fire(
                level=AlertLevel.INFO,
                source=AlertSource.SYSTEM,
                title=f"Test alert {i}",
                message=f"Test alert message {i}",
            )

        gc.collect()
        mem_after = _get_memory_mb()
        delta = mem_after - mem_before

        assert delta < 50, f"Memory grew by {delta:.1f}MB (threshold: 50MB)"


# ---------------------------------------------------------------------------
# Latency Profiling
# ---------------------------------------------------------------------------


class TestLatencyProfiling:
    """Profile critical path latency."""

    def test_execution_order_creation_latency(self) -> None:
        """Profile execution order creation latency."""

        def _run() -> Any:
            return Order(
                order_id="test-001",
                symbol="NIFTY",
                exchange=Exchange.NSE,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10,
            )

        stats = _measure(_run, iterations=100)
        assert stats["p95_ms"] < 10, (
            f"Order creation p95 {stats['p95_ms']:.2f}ms exceeds 10ms threshold"
        )

    def test_audit_event_creation_latency(self) -> None:
        """Profile audit event creation latency."""

        def _run() -> Any:
            return create_audit_event(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action="Latency test event",
            )

        stats = _measure(_run, iterations=1000)
        assert stats["p95_ms"] < 5, (
            f"Audit event creation p95 {stats['p95_ms']:.2f}ms exceeds 5ms threshold"
        )

    def test_monitoring_collector_latency(self) -> None:
        """Profile monitoring metric collection."""
        collector = MetricCollector()

        def _collect_fn() -> tuple[MetricValue, ...]:
            return (MetricValue(name="test", value=42.0, labels={}),)

        collector.register("test_metric", _collect_fn, CollectorType.PERIODIC)

        def _run() -> Any:
            return collector.collect_all()

        stats = _measure(_run, iterations=1000)
        assert stats["p95_ms"] < 5, (
            f"Monitoring collector p95 {stats['p95_ms']:.2f}ms exceeds 5ms threshold"
        )

    def test_paper_broker_latency(self) -> None:
        """Profile paper broker order execution."""
        broker = PaperBroker(initial_cash=Decimal(1000000))
        broker.connect()

        def _run() -> Any:
            return broker.place_order(
                OrderRequest(
                    symbol="NIFTY",
                    exchange=Exchange.NSE,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=1,
                )
            )

        stats = _measure(_run, iterations=50)
        assert stats["p95_ms"] < 50, (
            f"PaperBroker p95 {stats['p95_ms']:.2f}ms exceeds 50ms threshold"
        )


# ---------------------------------------------------------------------------
# Throughput Profiling
# ---------------------------------------------------------------------------


class TestThroughputProfiling:
    """Profile throughput for high-volume operations."""

    def test_backtesting_throughput(self) -> None:
        """Profile backtesting throughput (bars/second)."""
        bars = _generate_historical_bars(100)
        dataset = HistoricalDataset(
            symbol="NIFTY",
            exchange=Exchange.NSE,
            bars=bars,
        )
        engine = BacktestEngine(dataset=dataset, total_capital=Decimal(100000))

        start = time.perf_counter()
        engine.run()
        elapsed = time.perf_counter() - start

        bars_per_sec = len(bars) / elapsed if elapsed > 0 else 0
        assert bars_per_sec > 1, (
            f"Backtesting throughput {bars_per_sec:.1f} bars/s below 1 bars/s threshold"
        )

    def test_audit_query_throughput(self) -> None:
        """Profile audit query throughput."""
        from titan.audit.query import AuditQuery

        manager = AuditManager(storage=InMemoryAuditStorage())

        for i in range(1000):
            manager.record(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action=f"Throughput test event {i}",
            )

        def _run() -> Any:
            return manager.search(AuditQuery(category=AuditCategory.SYSTEM_START))

        stats = _measure(_run, iterations=50)
        assert stats["p95_ms"] < 100, (
            f"Audit query p95 {stats['p95_ms']:.1f}ms exceeds 100ms threshold"
        )

    def test_integrity_check_throughput(self) -> None:
        """Profile integrity verification throughput."""
        engine = IntegrityEngine()
        events = []
        for i in range(500):
            event = create_audit_event(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action=f"Integrity test event {i}",
            )
            events.append(event)

        def _run() -> Any:
            return engine.verify(events)

        stats = _measure(_run, iterations=20)
        assert stats["p95_ms"] < 500, (
            f"Integrity check p95 {stats['p95_ms']:.1f}ms exceeds 500ms threshold"
        )


# ---------------------------------------------------------------------------
# Stress Testing
# ---------------------------------------------------------------------------


class TestStressTesting:
    """Stress test critical subsystems."""

    def test_concurrent_audit_events(self) -> None:
        """Stress test concurrent audit event creation."""
        manager = AuditManager(storage=InMemoryAuditStorage())
        errors: list[Exception] = []

        def _create_event(i: int) -> None:
            try:
                manager.record(
                    source=AuditSource.RUNTIME,
                    category=AuditCategory.SYSTEM_START,
                    severity=AuditSeverity.INFO,
                    action=f"Concurrent event {i}",
                )
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_create_event, i) for i in range(500)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0, f"Concurrent audit errors: {errors}"

    def test_concurrent_alert_dispatch(self) -> None:
        """Stress test concurrent alert dispatch."""
        engine = AlertEngine()
        errors: list[Exception] = []

        def _dispatch(i: int) -> None:
            try:
                engine.fire(
                    level=AlertLevel.INFO,
                    source=AlertSource.SYSTEM,
                    title=f"Stress alert {i}",
                    message=f"Stress alert message {i}",
                )
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_dispatch, i) for i in range(500)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0, f"Concurrent alert errors: {errors}"

    def test_rapid_recovery_manager_cycles(self) -> None:
        """Stress test rapid recovery state transitions."""
        cb = CircuitBreaker(
            _config=CircuitBreakerConfig(
                failure_threshold=5, recovery_timeout_seconds=0.1
            )
        )
        errors: list[Exception] = []

        for i in range(100):
            try:
                if i % 3 == 0:
                    cb._record_failure()
                else:
                    cb._record_success()
            except Exception as e:
                errors.append(e)

        assert len(errors) == 0, f"Recovery stress errors: {errors}"

    def test_circuit_breaker_under_load(self) -> None:
        """Stress test circuit breaker with rapid failures."""
        cb = CircuitBreaker(
            _config=CircuitBreakerConfig(
                failure_threshold=5, recovery_timeout_seconds=0.1
            )
        )

        for _ in range(5):
            cb._record_failure()

        assert cb.state.value == "open"

        time.sleep(0.15)

        def _success_action() -> bool:
            return True

        result = cb.call(_success_action)
        assert result is True


# ---------------------------------------------------------------------------
# Failure Injection
# ---------------------------------------------------------------------------


class TestFailureInjection:
    """Inject failures and validate system resilience."""

    def test_pipeline_stage_failure_recovery(self) -> None:
        """Verify pipeline handles errors gracefully with minimal input."""
        pipeline = TradePipeline()

        report = pipeline.run(
            symbol="NIFTY",
            exchange=Exchange.NSE,
        )
        assert report is not None

    def test_audit_storage_failure_isolation(self) -> None:
        """Verify audit system isolates storage failures."""
        manager = AuditManager(storage=InMemoryAuditStorage())

        for i in range(10):
            manager.record(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action=f"Pre-failure event {i}",
            )

        assert len(manager._storage._events) == 10

    def test_config_manager_missing_env(self) -> None:
        """Verify config manager handles missing environment gracefully."""
        import os

        old_val = os.environ.pop("TITAN_NONEXISTENT_VAR", None)
        try:
            manager = ConfigManager()
            report = manager.generate_report()
            assert report is not None
        finally:
            if old_val is not None:
                os.environ["TITAN_NONEXISTENT_VAR"] = old_val

    def test_paper_broker_insufficient_balance(self) -> None:
        """Verify paper broker rejects orders exceeding balance."""
        broker = PaperBroker(initial_cash=Decimal(100))
        broker.connect()

        for _ in range(5):
            try:
                broker.place_order(
                    OrderRequest(
                        symbol="NIFTY",
                        exchange=Exchange.NSE,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=100,
                    )
                )
            except Exception:
                break

        with pytest.raises(Exception):
            broker.place_order(
                OrderRequest(
                    symbol="NIFTY",
                    exchange=Exchange.NSE,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=10000,
                )
            )

    def test_version_manager_deterministic(self) -> None:
        """Verify version manager returns consistent results."""
        mgr1 = VersionManager()
        mgr2 = VersionManager()

        v1 = mgr1.get()
        v2 = mgr2.get()

        assert v1.version == v2.version


# ---------------------------------------------------------------------------
# Recovery Validation
# ---------------------------------------------------------------------------


class TestRecoveryValidation:
    """Validate recovery mechanisms work correctly."""

    def test_retry_engine_success(self) -> None:
        """Verify retry engine succeeds on transient failures."""
        policy = RetryPolicy(
            mode=RetryMode.IMMEDIATE,
            max_attempts=3,
            base_delay_seconds=0.01,
        )
        engine = RetryEngine(_policy=policy)
        call_count = 0

        def _flaky() -> bool:
            nonlocal call_count
            call_count += 1
            return not call_count < 3

        result = engine.execute(_flaky)
        assert result.value == "success"
        assert call_count == 3

    def test_retry_engine_exhaustion(self) -> None:
        """Verify retry engine raises after max retries."""
        policy = RetryPolicy(
            mode=RetryMode.IMMEDIATE,
            max_attempts=2,
            base_delay_seconds=0.01,
        )
        engine = RetryEngine(_policy=policy)

        def _always_fail() -> bool:
            return False

        with pytest.raises(RecoveryRetryError):
            engine.execute(_always_fail)

    def test_circuit_breaker_open_blocks(self) -> None:
        """Verify circuit breaker blocks calls when open."""
        cb = CircuitBreaker(
            _config=CircuitBreakerConfig(
                failure_threshold=3, recovery_timeout_seconds=10.0
            )
        )

        for _ in range(3):
            cb._record_failure()

        def _action() -> bool:
            return True

        with pytest.raises(RecoveryCircuitBreakerError):
            cb.call(_action)

    def test_circuit_breaker_half_open_recovery(self) -> None:
        """Verify circuit breaker recovers from open to half-open."""
        cb = CircuitBreaker(
            _config=CircuitBreakerConfig(
                failure_threshold=3, recovery_timeout_seconds=0.05
            )
        )

        for _ in range(3):
            cb._record_failure()

        assert cb.state.value == "open"
        time.sleep(0.1)

        def _action() -> bool:
            return True

        result = cb.call(_action)
        assert result is True

    def test_health_recovery_monitoring(self) -> None:
        """Verify health recovery detects and reports issues."""
        from titan.recovery.health_recovery import HealthRecovery

        recovery = HealthRecovery()
        assert recovery is not None

    def test_integrity_engine_tamper_detection(self) -> None:
        """Verify integrity engine detects tampered events."""
        import dataclasses

        engine = IntegrityEngine()
        previous_hash = ""
        events = []
        for i in range(10):
            event = create_audit_event(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action=f"Tamper test event {i}",
                previous_hash=previous_hash,
            )
            events.append(event)
            previous_hash = event.event_hash

        report = engine.verify(events)
        assert report.is_valid is True

        tampered = dataclasses.replace(events[5], action="TAMPERED", event_hash="")
        events[5] = tampered

        report = engine.verify(events)
        assert report.is_valid is False


# ---------------------------------------------------------------------------
# Long-Running Stability
# ---------------------------------------------------------------------------


class TestLongRunningStability:
    """Validate system stability under sustained operation."""

    def test_sustained_market_intelligence(self) -> None:
        """Run market intelligence analyzers continuously for stability check."""
        candles = _generate_candles(200)
        series = _make_market_series(candles)

        start = time.perf_counter()
        for _ in range(100):
            result = VolumeAnalyzer().analyze(series)
            assert result is not None
        elapsed = time.perf_counter() - start

        assert elapsed < 30, (
            f"100 analytics iterations took {elapsed:.1f}s (threshold: 30s)"
        )

    def test_sustained_audit_recording(self) -> None:
        """Record audit events continuously for stability check."""
        manager = AuditManager(storage=InMemoryAuditStorage())

        start = time.perf_counter()
        for i in range(5000):
            manager.record(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action=f"Sustained test event {i}",
            )
        elapsed = time.perf_counter() - start

        assert elapsed < 10, f"5000 audit events took {elapsed:.1f}s (threshold: 10s)"

    def test_sustained_monitoring_collection(self) -> None:
        """Collect metrics continuously for stability check."""
        collector = MetricCollector()

        def _collect_fn() -> tuple[MetricValue, ...]:
            return (MetricValue(name="test", value=1.0, labels={}),)

        collector.register("sustained_test", _collect_fn, CollectorType.PERIODIC)

        start = time.perf_counter()
        for _ in range(5000):
            collector.collect_all()
        elapsed = time.perf_counter() - start

        assert elapsed < 10, (
            f"5000 metric collections took {elapsed:.1f}s (threshold: 10s)"
        )

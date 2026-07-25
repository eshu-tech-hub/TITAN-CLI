from __future__ import annotations

from datetime import datetime, timezone

import pytest

from titan.monitoring.collector import MetricCollector
from titan.monitoring.dashboard import MonitoringDashboard
from titan.monitoring.exceptions import (
    MonitoringCollectionError,
    MonitoringDashboardError,
    MonitoringError,
    MonitoringExportError,
    MonitoringHealthError,
    MonitoringInputError,
    MonitoringStorageError,
)
from titan.monitoring.health import HealthEngine
from titan.monitoring.manager import MonitoringManager
from titan.monitoring.metrics import MetricAggregator, MetricsEngine, MetricsRegistry
from titan.monitoring.models import (
    DashboardStatus,
    HealthStatus,
    MetricSnapshot,
    MetricType,
    MetricUnit,
    MetricValue,
    MonitoringReport,
    Subsystem,
    SubsystemHealth,
    SystemHealth,
    TelemetrySnapshot,
)
from titan.monitoring.telemetry import TelemetryManager

# ── Fixtures ──


def make_metric(
    name: str = "test_metric",
    value: float = 42.0,
    type: MetricType = MetricType.GAUGE,
    unit: MetricUnit = MetricUnit.COUNT,
    tags: dict | None = None,
) -> MetricValue:
    return MetricValue(
        name=name,
        value=value,
        type=type,
        unit=unit,
        tags=tags or {},
    )


def make_subsystem_health(
    subsystem: Subsystem = Subsystem.MARKET,
    status: HealthStatus = HealthStatus.HEALTHY,
) -> SubsystemHealth:
    return SubsystemHealth(
        subsystem=subsystem,
        status=status,
        last_check=datetime.now(timezone.utc),
    )


# ── Model Tests ──


class TestMetricValue:
    def test_defaults(self) -> None:
        m = MetricValue(name="cpu", value=50.0)
        assert m.name == "cpu"
        assert m.value == 50.0
        assert m.type == MetricType.GAUGE
        assert m.unit == MetricUnit.NONE
        assert m.tags == {}
        assert isinstance(m.timestamp, datetime)

    def test_frozen(self) -> None:
        m = MetricValue(name="mem", value=1024.0)
        with pytest.raises(AttributeError):
            m.value = 2048.0  # type: ignore[misc]

    def test_with_tags(self) -> None:
        m = MetricValue(
            name="latency",
            value=150.0,
            type=MetricType.HISTOGRAM,
            unit=MetricUnit.MILLISECONDS,
            tags={"service": "pipeline"},
        )
        assert m.tags["service"] == "pipeline"

    def test_counter_type(self) -> None:
        m = MetricValue(
            name="orders",
            value=5.0,
            type=MetricType.COUNTER,
            unit=MetricUnit.COUNT,
        )
        assert m.type == MetricType.COUNTER


class TestMetricSnapshot:
    def test_defaults(self) -> None:
        s = MetricSnapshot()
        assert s.metrics == ()
        assert isinstance(s.timestamp, datetime)
        assert s.source == "unknown"

    def test_with_metrics(self) -> None:
        m1 = make_metric(name="cpu")
        m2 = make_metric(name="mem")
        s = MetricSnapshot(metrics=(m1, m2))
        assert len(s.metrics) == 2


class TestSubsystemHealth:
    def test_defaults(self) -> None:
        h = SubsystemHealth(subsystem=Subsystem.MARKET)
        assert h.status == HealthStatus.HEALTHY
        assert h.message == ""
        assert h.failures == 0

    def test_critical(self) -> None:
        h = SubsystemHealth(
            subsystem=Subsystem.BROKER,
            status=HealthStatus.CRITICAL,
            message="Connection lost",
            failures=5,
        )
        assert h.status == HealthStatus.CRITICAL
        assert h.failures == 5

    def test_frozen(self) -> None:
        h = SubsystemHealth(subsystem=Subsystem.RISK)
        with pytest.raises(AttributeError):
            h.subsystem = Subsystem.MARKET  # type: ignore[misc]


class TestSystemHealth:
    def test_defaults(self) -> None:
        s = SystemHealth()
        assert s.subsystems == ()
        assert s.overall == HealthStatus.HEALTHY
        assert s.healthy_count == 0

    def test_with_subsystems_healthy(self) -> None:
        subs = (
            make_subsystem_health(Subsystem.MARKET, HealthStatus.HEALTHY),
            make_subsystem_health(Subsystem.BROKER, HealthStatus.HEALTHY),
        )
        s = SystemHealth(subsystems=subs, overall=HealthStatus.HEALTHY, healthy_count=2)
        assert s.healthy_count == 2
        assert s.overall == HealthStatus.HEALTHY


class TestHealthStatus:
    def test_enum_values(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.CRITICAL.value == "critical"
        assert HealthStatus.OFFLINE.value == "offline"


class TestSubsystem:
    def test_enum_values(self) -> None:
        assert Subsystem.MARKET.value == "market"
        assert Subsystem.BROKER.value == "broker"
        assert Subsystem.MONITORING.value == "monitoring"


class TestMetricType:
    def test_enum_values(self) -> None:
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.COUNTER.value == "counter"


class TestDashboardStatus:
    def test_defaults(self) -> None:
        s = DashboardStatus()
        assert s.metric_summaries == ()
        assert s.recent_failures == ()
        assert s.active_collectors == 0


class TestMonitoringReport:
    def test_defaults(self) -> None:
        r = MonitoringReport()
        assert r.metrics == ()
        assert r.warnings == ()
        assert r.recommendations == ()


class TestTelemetrySnapshot:
    def test_defaults(self) -> None:
        s = TelemetrySnapshot()
        assert s.metrics == ()
        assert s.health is None


# ── Exception Tests ──


class TestExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(MonitoringInputError, MonitoringError)
        assert issubclass(MonitoringCollectionError, MonitoringError)
        assert issubclass(MonitoringStorageError, MonitoringError)
        assert issubclass(MonitoringHealthError, MonitoringError)
        assert issubclass(MonitoringDashboardError, MonitoringError)
        assert issubclass(MonitoringExportError, MonitoringError)
        assert issubclass(MonitoringInputError, ValueError)

    def test_raise(self) -> None:
        with pytest.raises(MonitoringError):
            raise MonitoringCollectionError("collection failed")
        with pytest.raises(MonitoringError):
            raise MonitoringHealthError("health failed")


# ── MetricsRegistry Tests ──


class TestMetricsRegistry:
    def test_record_and_snapshot(self) -> None:
        reg = MetricsRegistry()
        reg.record(make_metric(name="cpu", value=50.0))
        reg.record(make_metric(name="mem", value=1024.0))
        snap = reg.snapshot()
        assert len(snap.metrics) == 2

    def test_latest(self) -> None:
        reg = MetricsRegistry()
        reg.record(make_metric(name="cpu", value=50.0))
        reg.record(make_metric(name="cpu", value=75.0))
        latest = reg.latest("cpu")
        assert latest is not None
        assert latest.value == 75.0

    def test_latest_missing(self) -> None:
        reg = MetricsRegistry()
        assert reg.latest("nonexistent") is None

    def test_latest_values(self) -> None:
        reg = MetricsRegistry()
        reg.record(make_metric(name="cpu", value=50.0))
        reg.record(make_metric(name="mem", value=1024.0))
        vals = reg.latest_values()
        assert vals["cpu"] == 50.0
        assert vals["mem"] == 1024.0

    def test_range(self) -> None:
        reg = MetricsRegistry()
        reg.record(make_metric(name="cpu", value=50.0))
        reg.record(make_metric(name="cpu", value=75.0))
        result = reg.range("cpu", datetime(1970, 1, 1, tzinfo=timezone.utc))
        assert len(result) == 2

    def test_clear(self) -> None:
        reg = MetricsRegistry()
        reg.record(make_metric(name="cpu", value=50.0))
        reg.clear()
        assert reg.count() == 0

    def test_count(self) -> None:
        reg = MetricsRegistry()
        reg.record(make_metric(name="cpu", value=50.0))
        reg.record(make_metric(name="mem", value=1024.0))
        assert reg.count() == 2

    def test_metric_names(self) -> None:
        reg = MetricsRegistry()
        reg.record(make_metric(name="cpu"))
        reg.record(make_metric(name="mem"))
        names = reg.metric_names()
        assert "cpu" in names
        assert "mem" in names

    def test_record_many(self) -> None:
        reg = MetricsRegistry()
        reg.record_many(
            (
                make_metric(name="cpu", value=50.0),
                make_metric(name="mem", value=1024.0),
            )
        )
        assert reg.count() == 2


# ── MetricAggregator Tests ──


class TestMetricAggregator:
    def test_aggregate_empty(self) -> None:
        agg = MetricAggregator()
        result = agg.aggregate("nonexistent")
        assert result["current"] == 0.0

    def test_aggregate(self) -> None:
        agg = MetricAggregator()
        agg.record(make_metric(name="latency", value=10.0))
        agg.record(make_metric(name="latency", value=20.0))
        agg.record(make_metric(name="latency", value=30.0))
        result = agg.aggregate("latency")
        assert result["current"] == 30.0
        assert result["min"] == 10.0
        assert result["max"] == 30.0
        assert result["avg"] == 20.0
        assert result["count"] == 3.0

    def test_snapshot(self) -> None:
        agg = MetricAggregator()
        agg.record(make_metric(name="cpu", value=50.0))
        snap = agg.snapshot()
        assert len(snap.metrics) == 1

    def test_clear(self) -> None:
        agg = MetricAggregator()
        agg.record(make_metric(name="cpu", value=50.0))
        agg.clear()
        assert agg.aggregate("cpu")["count"] == 0.0


# ── MetricsEngine Tests ──


class TestMetricsEngine:
    def test_collect_all(self) -> None:
        engine = MetricsEngine()

        def collect_cpu() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu", value=50.0),)

        engine.register_collector("cpu", collect_cpu)
        snap = engine.collect_all()
        assert len(snap.metrics) == 1
        assert snap.metrics[0].name == "cpu"

    def test_collector_failure(self) -> None:
        engine = MetricsEngine()

        def failing() -> tuple[MetricValue, ...]:
            msg = "collector failure"
            raise RuntimeError(msg)

        engine.register_collector("failing", failing)
        with pytest.raises(MonitoringCollectionError):
            engine.collect_all()

    def test_register_unregister(self) -> None:
        engine = MetricsEngine()

        def dummy() -> tuple[MetricValue, ...]:
            return (make_metric(name="dummy"),)

        engine.register_collector("dummy", dummy)
        engine.unregister_collector("dummy")
        snap = engine.collect_all()
        assert len(snap.metrics) == 0

    def test_aggregate(self) -> None:
        engine = MetricsEngine()
        engine._aggregator.record(make_metric(name="ping", value=1.0))
        result = engine.aggregate("ping")
        assert result["current"] == 1.0


# ── HealthEngine Tests ──


class TestHealthEngine:
    def test_register(self) -> None:
        engine = HealthEngine()
        h = engine.register(Subsystem.MARKET)
        assert h.subsystem == Subsystem.MARKET
        assert h.status == HealthStatus.HEALTHY

    def test_register_duplicate(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        with pytest.raises(MonitoringHealthError):
            engine.register(Subsystem.MARKET)

    def test_unregister(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        engine.unregister(Subsystem.MARKET)
        assert engine.get(Subsystem.MARKET) is None

    def test_unregister_missing(self) -> None:
        engine = HealthEngine()
        with pytest.raises(MonitoringHealthError):
            engine.unregister(Subsystem.MARKET)

    def test_report(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        h = engine.report(
            Subsystem.MARKET, HealthStatus.WARNING, message="high latency"
        )
        assert h.status == HealthStatus.WARNING
        assert h.message == "high latency"

    def test_report_unregistered(self) -> None:
        engine = HealthEngine()
        with pytest.raises(MonitoringHealthError):
            engine.report(Subsystem.MARKET, HealthStatus.WARNING)

    def test_get(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.BROKER)
        h = engine.get(Subsystem.BROKER)
        assert h is not None
        assert h.subsystem == Subsystem.BROKER

    def test_get_missing(self) -> None:
        engine = HealthEngine()
        assert engine.get(Subsystem.MARKET) is None

    def test_all_health(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        engine.register(Subsystem.BROKER)
        all_h = engine.all_health()
        assert len(all_h) == 2

    def test_evaluate_all_healthy(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        engine.register(Subsystem.BROKER)
        result = engine.evaluate()
        assert result.overall == HealthStatus.HEALTHY
        assert result.healthy_count == 2

    def test_evaluate_with_warning(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        engine.register(Subsystem.BROKER)
        engine.report(Subsystem.BROKER, HealthStatus.WARNING, message="slow")
        result = engine.evaluate()
        assert result.overall == HealthStatus.WARNING

    def test_evaluate_with_critical(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        engine.register(Subsystem.BROKER)
        engine.report(Subsystem.BROKER, HealthStatus.CRITICAL)
        result = engine.evaluate()
        assert result.overall == HealthStatus.CRITICAL

    def test_evaluate_with_offline(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        engine.register(Subsystem.BROKER, HealthStatus.OFFLINE)
        result = engine.evaluate()
        assert result.overall == HealthStatus.CRITICAL

    def test_reset(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        engine.reset()
        assert engine.evaluate().healthy_count == 0

    def test_is_registered(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        assert engine.is_registered(Subsystem.MARKET)
        assert not engine.is_registered(Subsystem.BROKER)

    def test_healthy_sets_last_healthy(self) -> None:
        engine = HealthEngine()
        engine.register(Subsystem.MARKET)
        h = engine.report(Subsystem.MARKET, HealthStatus.HEALTHY)
        assert h.last_healthy is not None


# ── Collector Tests ──


class TestMetricCollector:
    def test_register(self) -> None:
        c = MetricCollector()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu"),)

        desc = c.register("cpu", collect)
        assert desc.name == "cpu"

    def test_register_duplicate(self) -> None:
        c = MetricCollector()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu"),)

        c.register("cpu", collect)
        with pytest.raises(MonitoringCollectionError):
            c.register("cpu", collect)

    def test_unregister(self) -> None:
        c = MetricCollector()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu"),)

        c.register("cpu", collect)
        c.unregister("cpu")
        assert len(c.descriptors()) == 0

    def test_unregister_missing(self) -> None:
        c = MetricCollector()
        with pytest.raises(MonitoringCollectionError):
            c.unregister("nonexistent")

    def test_collect_all(self) -> None:
        c = MetricCollector()

        def collect_cpu() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu", value=50.0),)

        def collect_mem() -> tuple[MetricValue, ...]:
            return (make_metric(name="mem", value=1024.0),)

        c.register("cpu", collect_cpu)
        c.register("mem", collect_mem)
        snap = c.collect_all()
        assert len(snap.metrics) == 2

    def test_collect_one(self) -> None:
        c = MetricCollector()

        def collect_cpu() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu", value=50.0),)

        c.register("cpu", collect_cpu)
        metrics = c.collect_one("cpu")
        assert len(metrics) == 1
        assert metrics[0].name == "cpu"

    def test_collect_one_missing(self) -> None:
        c = MetricCollector()
        with pytest.raises(MonitoringCollectionError):
            c.collect_one("nonexistent")

    def test_enable_disable(self) -> None:
        c = MetricCollector()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu"),)

        c.register("cpu", collect)
        c.disable("cpu")
        snap = c.collect_all()
        assert len(snap.metrics) == 0
        c.enable("cpu")
        snap = c.collect_all()
        assert len(snap.metrics) == 1

    def test_start_stop(self) -> None:
        c = MetricCollector()
        c.start()
        assert c.is_running()
        c.stop()
        assert not c.is_running()

    def test_total_and_failed_collections(self) -> None:
        c = MetricCollector()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu"),)

        c.register("cpu", collect)
        c.collect_all()
        assert c.total_collections == 1
        assert c.failed_collections == 0

    def test_failed_collection_tracking(self) -> None:
        c = MetricCollector()

        def failing() -> tuple[MetricValue, ...]:
            msg = "fail"
            raise RuntimeError(msg)

        c.register("fail", failing)
        c.collect_all()
        assert c.failed_collections == 1
        assert c.total_collections == 1

    def test_reset(self) -> None:
        c = MetricCollector()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu"),)

        c.register("cpu", collect)
        c.collect_all()
        c.reset()
        assert c.total_collections == 0
        assert len(c.descriptors()) == 0


# ── TelemetryManager Tests ──


class TestTelemetryManager:
    def test_record_metric(self) -> None:
        tm = TelemetryManager()
        tm.record_metric(make_metric(name="cpu", value=50.0))
        snap = tm.current_status()
        assert len(snap.metrics) == 1

    def test_record_metrics(self) -> None:
        tm = TelemetryManager()
        tm.record_metrics(
            (
                make_metric(name="cpu", value=50.0),
                make_metric(name="mem", value=1024.0),
            )
        )
        snap = tm.current_status()
        assert len(snap.metrics) == 2

    def test_report_health(self) -> None:
        tm = TelemetryManager()
        tm.report_health(Subsystem.MARKET, "healthy")
        assert tm._health.is_registered(Subsystem.MARKET)

    def test_report_health_with_status(self) -> None:
        tm = TelemetryManager()
        tm.report_health(Subsystem.MARKET, "warning", message="high latency")
        health = tm._health.get(Subsystem.MARKET)
        assert health is not None
        assert health.status == HealthStatus.WARNING

    def test_collect_snapshot(self) -> None:
        tm = TelemetryManager()
        tm.record_metric(make_metric(name="cpu", value=50.0))
        snap = tm.collect_snapshot()
        assert snap.health is not None
        assert len(snap.metrics) == 1

    def test_latest_snapshot(self) -> None:
        tm = TelemetryManager()
        assert tm.latest_snapshot() is None
        tm.collect_snapshot()
        assert tm.latest_snapshot() is not None

    def test_snapshots(self) -> None:
        tm = TelemetryManager()
        tm.collect_snapshot()
        tm.collect_snapshot()
        snaps = tm.snapshots()
        assert len(snaps) == 2

    def test_register_exporter(self) -> None:
        tm = TelemetryManager()
        exported: list[TelemetrySnapshot] = []

        def exporter(snap: TelemetrySnapshot) -> None:
            exported.append(snap)

        tm.register_exporter(exporter)
        tm.collect_snapshot()
        assert len(exported) == 1

    def test_unregister_exporter(self) -> None:
        tm = TelemetryManager()
        exported: list[TelemetrySnapshot] = []

        def exporter(snap: TelemetrySnapshot) -> None:
            exported.append(snap)

        tm.register_exporter(exporter)
        tm.unregister_exporter(exporter)
        tm.collect_snapshot()
        assert len(exported) == 0

    def test_reset(self) -> None:
        tm = TelemetryManager()
        tm.record_metric(make_metric(name="cpu", value=50.0))
        tm.reset()
        snap = tm.current_status()
        assert len(snap.metrics) == 0

    def test_clear_snapshots(self) -> None:
        tm = TelemetryManager()
        tm.collect_snapshot()
        tm.clear_snapshots()
        assert tm.latest_snapshot() is None


# ── Dashboard Tests ──


class TestMonitoringDashboard:
    def test_status_defaults(self) -> None:
        dash = MonitoringDashboard()
        status = dash.status()
        assert status.system_health is not None
        assert status.metric_summaries == ()

    def test_status_with_metrics(self) -> None:
        dash = MonitoringDashboard()
        dash._metrics.record(make_metric(name="cpu", value=50.0))
        dash._metrics.record(make_metric(name="cpu", value=75.0))
        status = dash.status()
        assert len(status.metric_summaries) == 1
        summary = status.metric_summaries[0]
        assert summary.name == "cpu"
        assert summary.current == 75.0
        assert summary.min == 50.0
        assert summary.max == 75.0

    def test_record_failure(self) -> None:
        dash = MonitoringDashboard()
        dash.record_failure("broker connection lost")
        assert "broker connection lost" in dash.recent_failures()

    def test_recent_failures_limit(self) -> None:
        dash = MonitoringDashboard()
        for i in range(150):
            dash.record_failure(f"failure {i}")
        failures = dash.recent_failures(200)
        assert len(failures) == 100

    def test_subsystem_health(self) -> None:
        dash = MonitoringDashboard()
        dash._health.register(Subsystem.MARKET)
        h = dash.subsystem_health("market")
        assert h is not None
        assert h.subsystem == Subsystem.MARKET

    def test_subsystem_health_missing(self) -> None:
        dash = MonitoringDashboard()
        assert dash.subsystem_health("nonexistent") is None

    def test_metric_summary(self) -> None:
        dash = MonitoringDashboard()
        dash._metrics.record(make_metric(name="cpu", value=50.0))
        summary = dash.metric_summary("cpu")
        assert summary is not None
        assert summary.name == "cpu"
        assert summary.current == 50.0

    def test_metric_summary_missing(self) -> None:
        dash = MonitoringDashboard()
        assert dash.metric_summary("nonexistent") is None

    def test_trend_increasing(self) -> None:
        dash = MonitoringDashboard()
        dash._metrics.record(make_metric(name="cpu", value=50.0))
        dash._metrics.record(make_metric(name="cpu", value=75.0))
        dash._metrics.record(make_metric(name="cpu", value=100.0))
        summary = dash.metric_summary("cpu")
        assert summary is not None
        assert summary.trend == "increasing"

    def test_trend_decreasing(self) -> None:
        dash = MonitoringDashboard()
        dash._metrics.record(make_metric(name="cpu", value=100.0))
        dash._metrics.record(make_metric(name="cpu", value=75.0))
        dash._metrics.record(make_metric(name="cpu", value=50.0))
        summary = dash.metric_summary("cpu")
        assert summary is not None
        assert summary.trend == "decreasing"

    def test_trend_stable(self) -> None:
        dash = MonitoringDashboard()
        dash._metrics.record(make_metric(name="cpu", value=50.0))
        dash._metrics.record(make_metric(name="cpu", value=51.0))
        dash._metrics.record(make_metric(name="cpu", value=50.0))
        summary = dash.metric_summary("cpu")
        assert summary is not None
        assert summary.trend == "stable"

    def test_reset(self) -> None:
        dash = MonitoringDashboard()
        dash.record_failure("error")
        dash.reset()
        assert dash.recent_failures() == ()


# ── MonitoringManager Tests ──


class TestMonitoringManager:
    def test_initialization(self) -> None:
        mgr = MonitoringManager()
        assert mgr.telemetry is not None
        assert mgr.collector is not None
        assert mgr.dashboard is not None
        assert mgr.metrics is not None
        assert mgr.health is not None

    def test_register_subsystem(self) -> None:
        mgr = MonitoringManager()
        mgr.register_subsystem(Subsystem.MARKET)
        assert mgr.health.is_registered(Subsystem.MARKET)

    def test_register_collector(self) -> None:
        mgr = MonitoringManager()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu", value=50.0),)

        mgr.register_collector("cpu", collect)
        descriptors = mgr.collector.descriptors()
        assert len(descriptors) == 1

    def test_collect_snapshot(self) -> None:
        mgr = MonitoringManager()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu", value=50.0),)

        mgr.register_collector("cpu", collect)
        snap = mgr.collect_snapshot()
        assert snap.health is not None

    def test_dashboard_status(self) -> None:
        mgr = MonitoringManager()
        status = mgr.dashboard_status()
        assert isinstance(status, DashboardStatus)

    def test_generate_report(self) -> None:
        mgr = MonitoringManager()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu", value=50.0),)

        mgr.register_collector("cpu", collect)
        report = mgr.generate_report()
        assert isinstance(report, MonitoringReport)
        assert report.collector_count >= 1

    def test_report_with_critical_health(self) -> None:
        mgr = MonitoringManager()
        mgr.register_subsystem(Subsystem.BROKER)
        mgr.health.report(Subsystem.BROKER, HealthStatus.CRITICAL, message="down")
        report = mgr.generate_report()
        assert len(report.warnings) > 0
        assert len(report.recommendations) > 0

    def test_start_stop(self) -> None:
        mgr = MonitoringManager()
        mgr.start()
        assert mgr.collector.is_running()
        mgr.stop()
        assert not mgr.collector.is_running()

    def test_reset(self) -> None:
        mgr = MonitoringManager()

        def collect() -> tuple[MetricValue, ...]:
            return (make_metric(name="cpu", value=50.0),)

        mgr.register_collector("cpu", collect)
        mgr.collect_snapshot()
        mgr.reset()
        assert mgr.health.is_registered(Subsystem.MONITORING)
        assert len(mgr.collector.descriptors()) == 0

    def test_monitoring_self_health(self) -> None:
        mgr = MonitoringManager()
        assert mgr.health.is_registered(Subsystem.MONITORING)
        h = mgr.health.get(Subsystem.MONITORING)
        assert h is not None
        assert h.status == HealthStatus.HEALTHY


# ── Serialization / Frozen Tests ──


class TestFrozenInstances:
    def test_metric_value_frozen(self) -> None:
        m = MetricValue(name="test", value=1.0)
        with pytest.raises(AttributeError):
            m.value = 2.0  # type: ignore[misc]

    def test_snapshot_frozen(self) -> None:
        s = MetricSnapshot()
        with pytest.raises(AttributeError):
            s.metrics = ()  # type: ignore[misc]

    def test_subsystem_health_frozen(self) -> None:
        h = SubsystemHealth(subsystem=Subsystem.MARKET)
        with pytest.raises(AttributeError):
            h.subsystem = Subsystem.BROKER  # type: ignore[misc]

    def test_dashboard_status_frozen(self) -> None:
        s = DashboardStatus()
        with pytest.raises(AttributeError):
            s.active_collectors = 5  # type: ignore[misc]


# ── Dependency Injection Tests ──


class TestDependencyInjection:
    def test_health_engine_injection(self) -> None:
        engine = HealthEngine()
        tm = TelemetryManager(_health=engine)
        assert tm._health is engine

    def test_metrics_registry_injection(self) -> None:
        registry = MetricsRegistry()
        tm = TelemetryManager(_metrics=registry)
        assert tm._metrics is registry

    def test_telemetry_injection(self) -> None:
        tm = TelemetryManager()
        collector = MetricCollector()
        dash = MonitoringDashboard()
        mgr = MonitoringManager(_telemetry=tm, _collector=collector, _dashboard=dash)
        assert mgr._telemetry is tm
        assert mgr._collector is collector
        assert mgr._dashboard is dash

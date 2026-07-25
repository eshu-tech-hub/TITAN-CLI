from __future__ import annotations

import os
import tempfile
import threading
from datetime import datetime, timezone

import pytest

from titan.audit.event import (
    compute_event_hash,
    compute_event_hash_from_dict,
    create_audit_event,
    validate_event,
)
from titan.audit.exceptions import (
    AuditError,
    EventValidationError,
    HashChainError,
    IntegrityError,
    QueryError,
    SequenceError,
    StorageError,
)
from titan.audit.integrity import (
    IntegrityEngine,
    IntegrityReport,
    IntegrityViolation,
)
from titan.audit.manager import AuditManager
from titan.audit.models import (
    AuditCategory,
    AuditEvent,
    AuditReport,
    AuditResult,
    AuditSeverity,
    AuditSource,
)
from titan.audit.query import AuditQuery, AuditQueryEngine
from titan.audit.storage import (
    AuditStorage,
    InMemoryAuditStorage,
    JsonLinesAuditStorage,
)

# ── Helpers ──


def _make_event(
    *,
    sequence_number: int = 1,
    source: AuditSource = AuditSource.RUNTIME,
    category: AuditCategory = AuditCategory.SYSTEM_START,
    severity: AuditSeverity = AuditSeverity.INFO,
    action: str = "system.start",
    result: AuditResult = AuditResult.SUCCESS,
    previous_hash: str = "",
    event_hash: str = "",
    metadata: dict | None = None,
    **overrides: str,
) -> AuditEvent:
    """Build an AuditEvent for testing without going through the factory."""
    event = AuditEvent(
        event_id=overrides.get("event_id", "evt-test-001"),
        timestamp=datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
        sequence_number=sequence_number,
        source=source,
        category=category,
        severity=severity,
        action=action,
        result=result,
        correlation_id=overrides.get("correlation_id", ""),
        pipeline_id=overrides.get("pipeline_id", ""),
        trade_id=overrides.get("trade_id", ""),
        order_id=overrides.get("order_id", ""),
        position_id=overrides.get("position_id", ""),
        runtime_id=overrides.get("runtime_id", ""),
        user_id=overrides.get("user_id", ""),
        previous_hash=previous_hash,
        metadata=metadata or {},
    )
    if not event_hash:
        event_hash = compute_event_hash(event)
    return AuditEvent(
        event_id=event.event_id,
        timestamp=event.timestamp,
        sequence_number=event.sequence_number,
        source=event.source,
        category=event.category,
        severity=event.severity,
        action=event.action,
        result=event.result,
        correlation_id=event.correlation_id,
        pipeline_id=event.pipeline_id,
        trade_id=event.trade_id,
        order_id=event.order_id,
        position_id=event.position_id,
        runtime_id=event.runtime_id,
        user_id=event.user_id,
        event_hash=event_hash,
        previous_hash=previous_hash,
        metadata=event.metadata,
    )


def _make_chained_events(count: int = 3) -> list[AuditEvent]:
    """Build a valid chain of events with correct hash linkage."""
    events: list[AuditEvent] = []
    prev_hash = ""
    for i in range(count):
        event = _make_event(sequence_number=i + 1, previous_hash=prev_hash)
        prev_hash = event.event_hash
        events.append(event)
    return events


# ── Models ──


class TestAuditSource:
    def test_enum_values(self) -> None:
        assert AuditSource.CONFIGURATION.value == "configuration"
        assert AuditSource.RUNTIME.value == "runtime"
        assert AuditSource.BROKER.value == "broker"
        assert AuditSource.USER.value == "user"

    def test_all_sources_exist(self) -> None:
        sources = list(AuditSource)
        assert len(sources) == 15


class TestAuditCategory:
    def test_enum_values(self) -> None:
        assert AuditCategory.CONFIG_CHANGE.value == "config_change"
        assert AuditCategory.ORDER_PLACED.value == "order_placed"
        assert AuditCategory.RISK_BREACH.value == "risk_breach"

    def test_all_categories_exist(self) -> None:
        categories = list(AuditCategory)
        assert len(categories) == 28


class TestAuditSeverity:
    def test_enum_values(self) -> None:
        assert AuditSeverity.DEBUG.value == "debug"
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditResult:
    def test_enum_values(self) -> None:
        assert AuditResult.SUCCESS.value == "success"
        assert AuditResult.FAILURE.value == "failure"
        assert AuditResult.PARTIAL.value == "partial"
        assert AuditResult.SKIPPED.value == "skipped"
        assert AuditResult.UNKNOWN.value == "unknown"


class TestAuditEvent:
    def test_frozen(self) -> None:
        event = _make_event()
        with pytest.raises(AttributeError):
            event.action = "new.action"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        event = _make_event(
            pipeline_id="pl-001",
            trade_id="tr-xyz",
            metadata={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_id"] == "evt-test-001"
        assert d["source"] == "runtime"
        assert d["category"] == "system_start"
        assert d["severity"] == "info"
        assert d["pipeline_id"] == "pl-001"
        assert d["trade_id"] == "tr-xyz"
        assert d["metadata"]["key"] == "value"
        assert "timestamp" in d

    def test_from_dict_round_trip(self) -> None:
        event = _make_event(pipeline_id="pl-rt")
        d = event.to_dict()
        restored = AuditEvent.from_dict(d)
        assert restored.event_id == event.event_id
        assert restored.source == event.source
        assert restored.category == event.category
        assert restored.severity == event.severity
        assert restored.pipeline_id == "pl-rt"
        assert restored.event_hash == event.event_hash

    def test_defaults(self) -> None:
        event = _make_event()
        assert event.correlation_id == ""
        assert event.pipeline_id == ""
        assert event.trade_id == ""
        assert event.order_id == ""
        assert event.position_id == ""
        assert event.runtime_id == ""
        assert event.user_id == ""
        assert event.metadata == {}


class TestAuditReport:
    def test_defaults(self) -> None:
        report = AuditReport()
        assert report.total_events == 0
        assert report.integrity_status == "unknown"
        assert report.verification_failures == 0
        assert report.events_by_source == {}
        assert report.first_event_time is None


# ── Exceptions ──


class TestExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(EventValidationError, AuditError)
        assert issubclass(StorageError, AuditError)
        assert issubclass(IntegrityError, AuditError)
        assert issubclass(QueryError, AuditError)
        assert issubclass(SequenceError, AuditError)
        assert issubclass(HashChainError, IntegrityError)
        assert issubclass(AuditError, Exception)


# ── Event creation & validation ──


class TestEventCreation:
    def test_create_audit_event(self) -> None:
        event = create_audit_event(
            source=AuditSource.EXECUTION,
            category=AuditCategory.ORDER_PLACED,
            severity=AuditSeverity.INFO,
            action="order.place",
        )
        assert event.event_id
        assert event.source == AuditSource.EXECUTION
        assert event.category == AuditCategory.ORDER_PLACED
        assert event.event_hash != ""
        assert event.timestamp.tzinfo is not None

    def test_create_with_explicit_id(self) -> None:
        event = create_audit_event(
            source=AuditSource.RISK,
            category=AuditCategory.RISK_BREACH,
            severity=AuditSeverity.WARNING,
            action="risk.breach",
            event_id="custom-id-001",
        )
        assert event.event_id == "custom-id-001"

    def test_create_with_metadata(self) -> None:
        event = create_audit_event(
            source=AuditSource.PIPELINE,
            category=AuditCategory.PIPELINE_EXECUTED,
            severity=AuditSeverity.INFO,
            action="pipeline.run",
            metadata={"symbols": ["RELIANCE", "TCS"]},
        )
        assert event.metadata["symbols"] == ["RELIANCE", "TCS"]

    def test_create_with_previous_hash(self) -> None:
        event1 = create_audit_event(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="start",
        )
        event2 = create_audit_event(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_STOP,
            severity=AuditSeverity.INFO,
            action="stop",
            previous_hash=event1.event_hash,
        )
        assert event2.previous_hash == event1.event_hash

    def test_invalid_event_raises(self) -> None:
        with pytest.raises(EventValidationError):
            create_audit_event(
                source=AuditSource.USER,
                category=AuditCategory.USER_ACTION,
                severity=AuditSeverity.INFO,
                action="",  # empty action
            )


class TestEventValidation:
    def test_valid_event(self) -> None:
        event = _make_event()
        errors = validate_event(event)
        assert errors == []

    def test_empty_event_id(self) -> None:
        event = AuditEvent(
            event_id="",
            timestamp=datetime.now(timezone.utc),
            sequence_number=1,
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="test",
            result=AuditResult.SUCCESS,
        )
        errors = validate_event(event)
        assert any("event_id" in e for e in errors)

    def test_empty_action(self) -> None:
        event = AuditEvent(
            event_id="evt-001",
            timestamp=datetime.now(timezone.utc),
            sequence_number=1,
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="",
            result=AuditResult.SUCCESS,
        )
        errors = validate_event(event)
        assert any("action" in e for e in errors)

    def test_negative_sequence(self) -> None:
        event = AuditEvent(
            event_id="evt-001",
            timestamp=datetime.now(timezone.utc),
            sequence_number=-1,
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="test",
            result=AuditResult.SUCCESS,
        )
        errors = validate_event(event)
        assert any("sequence_number" in e for e in errors)

    def test_naive_timestamp(self) -> None:
        event = AuditEvent(
            event_id="evt-001",
            timestamp=datetime(2026, 1, 1),  # type: ignore[arg-type]
            sequence_number=1,
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="test",
            result=AuditResult.SUCCESS,
        )
        errors = validate_event(event)
        assert any("timestamp" in e for e in errors)


class TestEventHashing:
    def test_deterministic(self) -> None:
        event = _make_event()
        h1 = compute_event_hash(event)
        h2 = compute_event_hash(event)
        assert h1 == h2

    def test_different_events_different_hashes(self) -> None:
        e1 = _make_event(action="action.a")
        e2 = _make_event(action="action.b")
        assert compute_event_hash(e1) != compute_event_hash(e2)

    def test_hash_from_dict_matches(self) -> None:
        event = _make_event()
        d = event.to_dict()
        h1 = compute_event_hash(event)
        h2 = compute_event_hash_from_dict(d)
        assert h1 == h2

    def test_hash_length(self) -> None:
        event = _make_event()
        h = compute_event_hash(event)
        assert len(h) == 64  # SHA-256 hex digest


# ── Storage ──


class TestInMemoryAuditStorage:
    def test_append_and_load(self) -> None:
        storage = InMemoryAuditStorage()
        event = _make_event()
        storage.append(event)
        loaded = storage.load_all()
        assert len(loaded) == 1
        assert loaded[0].event_id == event.event_id

    def test_count(self) -> None:
        storage = InMemoryAuditStorage()
        assert storage.count() == 0
        storage.append(_make_event(sequence_number=1))
        storage.append(_make_event(sequence_number=2))
        assert storage.count() == 2

    def test_append_batch(self) -> None:
        storage = InMemoryAuditStorage()
        events = [_make_event(sequence_number=i) for i in range(5)]
        storage.append_batch(events)
        assert storage.count() == 5

    def test_clear(self) -> None:
        storage = InMemoryAuditStorage()
        storage.append(_make_event())
        assert storage.count() == 1
        storage.clear()
        assert storage.count() == 0

    def test_returns_copy(self) -> None:
        storage = InMemoryAuditStorage()
        storage.append(_make_event())
        loaded1 = storage.load_all()
        loaded2 = storage.load_all()
        assert loaded1 is not loaded2
        assert loaded1 == loaded2

    def test_thread_safety(self) -> None:
        storage = InMemoryAuditStorage()
        errors: list[Exception] = []

        def writer(n: int) -> None:
            try:
                for i in range(100):
                    storage.append(_make_event(sequence_number=n * 100 + i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert storage.count() == 400


class TestJsonLinesAuditStorage:
    def test_append_and_load(self, tmp_path: object) -> None:
        path = tmp_path / "audit.jsonl"  # type: ignore[operator]
        storage = JsonLinesAuditStorage(path)
        event = _make_event()
        storage.append(event)
        loaded = storage.load_all()
        assert len(loaded) == 1
        assert loaded[0].event_id == event.event_id

    def test_append_batch(self, tmp_path: object) -> None:
        path = tmp_path / "batch.jsonl"  # type: ignore[operator]
        storage = JsonLinesAuditStorage(path)
        events = [_make_event(sequence_number=i) for i in range(3)]
        storage.append_batch(events)
        assert storage.count() == 3

    def test_count(self, tmp_path: object) -> None:
        path = tmp_path / "count.jsonl"  # type: ignore[operator]
        storage = JsonLinesAuditStorage(path)
        assert storage.count() == 0
        storage.append(_make_event(sequence_number=1))
        storage.append(_make_event(sequence_number=2))
        assert storage.count() == 2

    def test_clear(self, tmp_path: object) -> None:
        path = tmp_path / "clear.jsonl"  # type: ignore[operator]
        storage = JsonLinesAuditStorage(path)
        storage.append(_make_event())
        storage.clear()
        assert storage.count() == 0

    def test_persistence(self, tmp_path: object) -> None:
        path = tmp_path / "persist.jsonl"  # type: ignore[operator]
        storage1 = JsonLinesAuditStorage(path)
        storage1.append(_make_event(sequence_number=1))
        storage1.append(_make_event(sequence_number=2))

        storage2 = JsonLinesAuditStorage(path)
        assert storage2.count() == 2
        loaded = storage2.load_all()
        assert loaded[0].sequence_number == 1

    def test_creates_parent_dirs(self, tmp_path: object) -> None:
        path = tmp_path / "nested" / "deep" / "audit.jsonl"  # type: ignore[operator]
        storage = JsonLinesAuditStorage(path)
        storage.append(_make_event())
        assert storage.count() == 1

    def test_corrupt_line_raises(self, tmp_path: object) -> None:
        path = tmp_path / "corrupt.jsonl"  # type: ignore[operator]
        path.write_text("not valid json\n", encoding="utf-8")
        storage = JsonLinesAuditStorage(path)
        with pytest.raises(StorageError, match="Corrupt line"):
            storage.load_all()

    def test_skips_blank_lines(self, tmp_path: object) -> None:
        path = tmp_path / "blanks.jsonl"  # type: ignore[operator]
        path.write_text("\n\n\n", encoding="utf-8")
        storage = JsonLinesAuditStorage(path)
        assert storage.count() == 0


# ── Integrity ──


class TestIntegrityEngine:
    def test_verify_valid_chain(self) -> None:
        engine = IntegrityEngine()
        events = _make_chained_events(5)
        report = engine.verify(events)
        assert report.is_valid
        assert report.total_events == 5
        assert report.valid_events == 5
        assert report.violation_count == 0

    def test_verify_empty(self) -> None:
        engine = IntegrityEngine()
        report = engine.verify([])
        assert report.is_valid
        assert report.total_events == 0

    def test_detect_hash_mismatch(self) -> None:
        engine = IntegrityEngine()
        events = _make_chained_events(3)

        tampered = AuditEvent(
            event_id=events[1].event_id,
            timestamp=events[1].timestamp,
            sequence_number=events[1].sequence_number,
            source=events[1].source,
            category=events[1].category,
            severity=events[1].severity,
            action="tampered.action",
            result=events[1].result,
            event_hash=events[1].event_hash,
            previous_hash=events[1].previous_hash,
        )

        modified_events = [events[0], tampered, events[2]]
        report = engine.verify(modified_events)
        assert not report.is_valid
        assert report.violation_count >= 1

    def test_detect_chain_break(self) -> None:
        engine = IntegrityEngine()
        events = _make_chained_events(3)

        broken = AuditEvent(
            event_id="evt-broken",
            timestamp=events[1].timestamp,
            sequence_number=events[1].sequence_number,
            source=events[1].source,
            category=events[1].category,
            severity=events[1].severity,
            action=events[1].action,
            result=events[1].result,
            event_hash=events[1].event_hash,
            previous_hash="wrong_previous_hash",
        )

        report = engine.verify([events[0], broken, events[2]])
        assert not report.is_valid

    def test_violation_details(self) -> None:
        engine = IntegrityEngine()
        events = _make_chained_events(2)

        tampered = AuditEvent(
            event_id=events[0].event_id,
            timestamp=events[0].timestamp,
            sequence_number=events[0].sequence_number,
            source=events[0].source,
            category=events[0].category,
            severity=events[0].severity,
            action="tampered",
            result=events[0].result,
            event_hash=events[0].event_hash,
            previous_hash="",
        )

        report = engine.verify([tampered, events[1]])
        assert not report.is_valid
        violation = report.violations[0]
        assert isinstance(violation, IntegrityViolation)
        assert violation.violation_type == "hash_mismatch"


class TestIntegrityReport:
    def test_is_valid_clean(self) -> None:
        report = IntegrityReport(total_events=5, valid_events=5, chain_valid=True)
        assert report.is_valid
        assert report.violation_count == 0

    def test_is_invalid_with_violations(self) -> None:
        violation = IntegrityViolation(
            sequence_number=1,
            event_id="evt-001",
            violation_type="hash_mismatch",
            expected="aaa",
            actual="bbb",
            description="test",
        )
        report = IntegrityReport(
            total_events=5,
            valid_events=4,
            violations=(violation,),
            chain_valid=False,
        )
        assert not report.is_valid
        assert report.violation_count == 1


# ── Query Engine ──


class TestAuditQuery:
    def test_defaults(self) -> None:
        q = AuditQuery()
        assert q.source is None
        assert q.category is None
        assert q.severity is None
        assert q.time_from is None


class TestAuditQueryEngine:
    def _setup_engine(
        self, events: list[AuditEvent] | None = None
    ) -> tuple[AuditQueryEngine, InMemoryAuditStorage]:
        storage = InMemoryAuditStorage()
        if events:
            storage.append_batch(events)
        return AuditQueryEngine(storage), storage

    def test_query_all(self) -> None:
        events = _make_chained_events(5)
        engine, _ = self._setup_engine(events)
        result = engine.query(AuditQuery())
        assert len(result) == 5

    def test_query_by_source(self) -> None:
        events = [
            _make_event(source=AuditSource.RUNTIME, action="runtime.a"),
            _make_event(source=AuditSource.EXECUTION, action="exec.a"),
            _make_event(source=AuditSource.RUNTIME, action="runtime.b"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_source(AuditSource.RUNTIME)
        assert len(result) == 2

    def test_query_by_category(self) -> None:
        events = [
            _make_event(category=AuditCategory.ORDER_PLACED, action="a"),
            _make_event(category=AuditCategory.ORDER_FILLED, action="b"),
            _make_event(category=AuditCategory.ORDER_PLACED, action="c"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_category(AuditCategory.ORDER_PLACED)
        assert len(result) == 2

    def test_query_by_severity(self) -> None:
        events = [
            _make_event(severity=AuditSeverity.INFO, action="a"),
            _make_event(severity=AuditSeverity.ERROR, action="b"),
            _make_event(severity=AuditSeverity.WARNING, action="c"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_severity(AuditSeverity.ERROR)
        assert len(result) == 1

    def test_query_by_trade_id(self) -> None:
        events = [
            _make_event(trade_id="tr-001", action="a"),
            _make_event(trade_id="tr-002", action="b"),
            _make_event(trade_id="tr-001", action="c"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_trade_id("tr-001")
        assert len(result) == 2

    def test_query_by_order_id(self) -> None:
        events = [
            _make_event(order_id="ord-001", action="a"),
            _make_event(order_id="ord-002", action="b"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_order_id("ord-001")
        assert len(result) == 1

    def test_query_by_pipeline_id(self) -> None:
        events = [
            _make_event(pipeline_id="pl-001", action="a"),
            _make_event(pipeline_id="pl-002", action="b"),
            _make_event(pipeline_id="pl-001", action="c"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_pipeline_id("pl-001")
        assert len(result) == 2

    def test_query_by_runtime_id(self) -> None:
        events = [
            _make_event(runtime_id="rt-001", action="a"),
            _make_event(runtime_id="rt-002", action="b"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_runtime_id("rt-001")
        assert len(result) == 1

    def test_query_by_correlation_id(self) -> None:
        events = [
            _make_event(correlation_id="corr-abc", action="a"),
            _make_event(correlation_id="corr-xyz", action="b"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query_by_correlation_id("corr-abc")
        assert len(result) == 1

    def test_query_time_range(self) -> None:
        t1 = datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 7, 10, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
        e1 = AuditEvent(
            event_id="e1",
            timestamp=t1,
            sequence_number=1,
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
            result=AuditResult.SUCCESS,
        )
        e2 = AuditEvent(
            event_id="e2",
            timestamp=t2,
            sequence_number=2,
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="b",
            result=AuditResult.SUCCESS,
        )
        e3 = AuditEvent(
            event_id="e3",
            timestamp=t3,
            sequence_number=3,
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="c",
            result=AuditResult.SUCCESS,
        )
        engine, _ = self._setup_engine([e1, e2, e3])
        result = engine.query_time_range(t1, t2)
        assert len(result) == 2

    def test_query_combined_filters(self) -> None:
        events = [
            _make_event(
                source=AuditSource.EXECUTION,
                severity=AuditSeverity.INFO,
                trade_id="tr-001",
                action="a",
            ),
            _make_event(
                source=AuditSource.EXECUTION,
                severity=AuditSeverity.ERROR,
                trade_id="tr-001",
                action="b",
            ),
            _make_event(
                source=AuditSource.RISK,
                severity=AuditSeverity.INFO,
                trade_id="tr-001",
                action="c",
            ),
        ]
        engine, _ = self._setup_engine(events)
        q = AuditQuery(source=AuditSource.EXECUTION, severity=AuditSeverity.INFO)
        result = engine.query(q)
        assert len(result) == 1
        assert result[0].action == "a"

    def test_count_with_query(self) -> None:
        events = [
            _make_event(source=AuditSource.RUNTIME, action="a"),
            _make_event(source=AuditSource.EXECUTION, action="b"),
        ]
        engine, _ = self._setup_engine(events)
        assert engine.count(AuditQuery(source=AuditSource.RUNTIME)) == 1

    def test_count_no_query(self) -> None:
        engine, storage = self._setup_engine()
        storage.append_batch(_make_chained_events(3))
        assert engine.count() == 3

    def test_query_by_sequence_range(self) -> None:
        events = [
            _make_event(sequence_number=1),
            _make_event(sequence_number=2),
            _make_event(sequence_number=3),
            _make_event(sequence_number=4),
        ]
        engine, _ = self._setup_engine(events)
        q = AuditQuery(sequence_from=2, sequence_to=3)
        result = engine.query(q)
        assert len(result) == 2

    def test_query_by_user_id(self) -> None:
        events = [
            _make_event(user_id="user-admin", action="a"),
            _make_event(user_id="user-viewer", action="b"),
        ]
        engine, _ = self._setup_engine(events)
        result = engine.query(AuditQuery(user_id="user-admin"))
        assert len(result) == 1


# ── AuditManager ──


class TestAuditManager:
    def test_record_event(self) -> None:
        manager = AuditManager()
        event = manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="system.start",
        )
        assert event.event_id
        assert event.sequence_number == 1
        assert event.source == AuditSource.RUNTIME
        assert event.event_hash != ""

    def test_sequential_numbering(self) -> None:
        manager = AuditManager()
        e1 = manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
        )
        e2 = manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_STOP,
            severity=AuditSeverity.INFO,
            action="b",
        )
        e3 = manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.ERROR,
            severity=AuditSeverity.ERROR,
            action="c",
        )
        assert e1.sequence_number == 1
        assert e2.sequence_number == 2
        assert e3.sequence_number == 3

    def test_hash_chain(self) -> None:
        manager = AuditManager()
        e1 = manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
        )
        e2 = manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_STOP,
            severity=AuditSeverity.INFO,
            action="b",
        )
        assert e2.previous_hash == e1.event_hash
        assert manager.last_hash == e2.event_hash

    def test_integrity_after_recording(self) -> None:
        manager = AuditManager()
        for i in range(10):
            manager.record(
                source=AuditSource.RUNTIME,
                category=AuditCategory.HEALTH_CHECK,
                severity=AuditSeverity.INFO,
                action=f"health.{i}",
            )
        report = manager.verify_integrity()
        assert report.is_valid
        assert report.total_events == 10

    def test_event_count(self) -> None:
        manager = AuditManager()
        assert manager.event_count == 0
        manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
        )
        assert manager.event_count == 1

    def test_sequence_counter(self) -> None:
        manager = AuditManager()
        assert manager.sequence_counter == 0
        manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
        )
        assert manager.sequence_counter == 1

    def test_generate_report(self) -> None:
        manager = AuditManager()
        for _ in range(5):
            manager.record(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action="start",
            )
        manager.record(
            source=AuditSource.EXECUTION,
            category=AuditCategory.ORDER_PLACED,
            severity=AuditSeverity.WARNING,
            action="order.place",
        )
        report = manager.generate_report()
        assert report.total_events == 6
        assert report.events_by_source["runtime"] == 5
        assert report.events_by_source["execution"] == 1
        assert report.events_by_severity["info"] == 5
        assert report.events_by_severity["warning"] == 1
        assert report.integrity_status == "valid"
        assert report.first_event_time is not None
        assert report.last_event_time is not None

    def test_generate_report_empty(self) -> None:
        manager = AuditManager()
        report = manager.generate_report()
        assert report.total_events == 0
        assert report.integrity_status == "empty"

    def test_record_with_all_fields(self) -> None:
        manager = AuditManager()
        event = manager.record(
            source=AuditSource.EXECUTION,
            category=AuditCategory.ORDER_FILLED,
            severity=AuditSeverity.INFO,
            action="order.fill",
            result=AuditResult.SUCCESS,
            correlation_id="corr-001",
            pipeline_id="pl-001",
            trade_id="tr-001",
            order_id="ord-001",
            position_id="pos-001",
            runtime_id="rt-001",
            user_id="user-001",
            metadata={"price": 100.50, "qty": 10},
        )
        assert event.correlation_id == "corr-001"
        assert event.pipeline_id == "pl-001"
        assert event.trade_id == "tr-001"
        assert event.order_id == "ord-001"
        assert event.position_id == "pos-001"
        assert event.runtime_id == "rt-001"
        assert event.user_id == "user-001"
        assert event.metadata["price"] == 100.50

    def test_search_shorthand(self) -> None:
        manager = AuditManager()
        manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
        )
        manager.record(
            source=AuditSource.EXECUTION,
            category=AuditCategory.ORDER_PLACED,
            severity=AuditSeverity.WARNING,
            action="b",
        )
        result = manager.search(AuditQuery(source=AuditSource.EXECUTION))
        assert len(result) == 1

    def test_record_batch(self) -> None:
        manager = AuditManager()
        batch = [
            {
                "source": "runtime",
                "category": "system_start",
                "severity": "info",
                "action": "a",
            },
            {
                "source": "execution",
                "category": "order_placed",
                "severity": "warning",
                "action": "b",
            },
            {
                "source": "risk",
                "category": "risk_breach",
                "severity": "error",
                "action": "c",
            },
        ]
        recorded = manager.record_batch(batch)
        assert len(recorded) == 3
        assert recorded[0].sequence_number == 1
        assert recorded[2].sequence_number == 3
        assert recorded[1].previous_hash == recorded[0].event_hash

    def test_custom_storage(self) -> None:
        storage = InMemoryAuditStorage()
        manager = AuditManager(storage=storage)
        manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
        )
        assert storage.count() == 1

    def test_query_engine_accessible(self) -> None:
        manager = AuditManager()
        manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="a",
        )
        result = manager.query.query(AuditQuery())
        assert len(result) == 1

    def test_thread_safety_record(self) -> None:
        manager = AuditManager()
        errors: list[Exception] = []

        def recorder(n: int) -> None:
            try:
                for i in range(50):
                    manager.record(
                        source=AuditSource.RUNTIME,
                        category=AuditCategory.HEALTH_CHECK,
                        severity=AuditSeverity.INFO,
                        action=f"health.{n}.{i}",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=recorder, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert manager.event_count == 200
        report = manager.verify_integrity()
        assert report.is_valid


# ── Dependency Injection ──


class TestDependencyInjection:
    def test_custom_storage_backend(self) -> None:
        class DummyStorage(AuditStorage):
            def __init__(self) -> None:
                self.events: list[AuditEvent] = []

            def append(self, event: AuditEvent) -> None:
                self.events.append(event)

            def append_batch(self, events: list[AuditEvent]) -> None:
                self.events.extend(events)

            def load_all(self) -> list[AuditEvent]:
                return list(self.events)

            def count(self) -> int:
                return len(self.events)

            def clear(self) -> None:
                self.events.clear()

        storage = DummyStorage()
        manager = AuditManager(storage=storage)
        manager.record(
            source=AuditSource.RUNTIME,
            category=AuditCategory.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="test",
        )
        assert len(storage.events) == 1

    def test_manager_with_jsonl_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "audit.jsonl")
            storage = JsonLinesAuditStorage(path)
            manager = AuditManager(storage=storage)
            manager.record(
                source=AuditSource.RUNTIME,
                category=AuditCategory.SYSTEM_START,
                severity=AuditSeverity.INFO,
                action="start",
            )
            manager.record(
                source=AuditSource.EXECUTION,
                category=AuditCategory.ORDER_PLACED,
                severity=AuditSeverity.WARNING,
                action="order.place",
            )

            manager2 = AuditManager(storage=JsonLinesAuditStorage(path))
            assert manager2.event_count == 2
            report = manager2.verify_integrity()
            assert report.is_valid

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from titan.logging.context import LoggingContext
from titan.logging.exceptions import (
    HandlerRegistrationError,
    LoggingError,
)
from titan.logging.formatter import (
    CompactFormatter,
    ConsoleFormatter,
    JSONFormatter,
)
from titan.logging.handlers import (
    ConsoleHandler,
    FileHandler,
    JSONFileHandler,
)
from titan.logging.logger import StructuredLogger
from titan.logging.manager import LoggerManager
from titan.logging.models import (
    FormatterType,
    HandlerConfig,
    HandlerType,
    LogEntry,
    LogLevel,
    LoggingConfig,
    LoggingReport,
)

# ── LogLevel ──


class TestLogLevel:
    def test_enum_values(self) -> None:
        assert LogLevel.TRACE.value == "TRACE"
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_to_int(self) -> None:
        assert LogLevel.TRACE.to_int() == 5
        assert LogLevel.DEBUG.to_int() == 10
        assert LogLevel.INFO.to_int() == 20
        assert LogLevel.WARNING.to_int() == 30
        assert LogLevel.ERROR.to_int() == 40
        assert LogLevel.CRITICAL.to_int() == 50

    def test_from_int(self) -> None:
        assert LogLevel.from_int(5) == LogLevel.TRACE
        assert LogLevel.from_int(10) == LogLevel.DEBUG
        assert LogLevel.from_int(20) == LogLevel.INFO
        assert LogLevel.from_int(30) == LogLevel.WARNING
        assert LogLevel.from_int(40) == LogLevel.ERROR
        assert LogLevel.from_int(50) == LogLevel.CRITICAL
        assert LogLevel.from_int(60) == LogLevel.CRITICAL
        assert LogLevel.from_int(0) == LogLevel.TRACE


# ── LogEntry ──


class TestLogEntry:
    def test_defaults(self) -> None:
        ts = datetime.now(timezone.utc)
        entry = LogEntry(
            timestamp=ts,
            level=LogLevel.INFO,
            module="test_module",
            component="test_component",
            message="test message",
        )
        assert entry.timestamp == ts
        assert entry.level == LogLevel.INFO
        assert entry.module == "test_module"
        assert entry.message == "test message"
        assert entry.metadata == {}
        assert entry.exception is None
        assert entry.duration_ms is None
        assert entry.pipeline_id is None

    def test_frozen(self) -> None:
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            module="m",
            component="c",
            message="test",
        )
        with pytest.raises(AttributeError):
            entry.level = LogLevel.ERROR  # type: ignore[misc]

    def test_with_all_fields(self) -> None:
        ts = datetime.now(timezone.utc)
        entry = LogEntry(
            timestamp=ts,
            level=LogLevel.ERROR,
            module="execution",
            component="order_manager",
            message="Order failed",
            metadata={"order_type": "LIMIT"},
            exception="TimeoutError",
            duration_ms=1500.5,
            pipeline_id="pl-001",
            correlation_id="corr-abc",
            trade_id="tr-xyz",
            order_id="ord-123",
            position_id="pos-456",
            runtime_id="rt-789",
            request_id="req-000",
        )
        assert entry.pipeline_id == "pl-001"
        assert entry.correlation_id == "corr-abc"
        assert entry.trade_id == "tr-xyz"
        assert entry.order_id == "ord-123"
        assert entry.position_id == "pos-456"
        assert entry.runtime_id == "rt-789"
        assert entry.request_id == "req-000"
        assert entry.duration_ms == 1500.5


# ── LoggingConfig ──


class TestLoggingConfig:
    def test_defaults(self) -> None:
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert len(config.handlers) == 2

    def test_custom_config(self) -> None:
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            handlers=(
                HandlerConfig(
                    handler_type=HandlerType.CONSOLE,
                    level=LogLevel.DEBUG,
                ),
            ),
            component="titan_test",
        )
        assert config.level == LogLevel.DEBUG
        assert len(config.handlers) == 1


# ── LoggingReport ──


class TestLoggingReport:
    def test_defaults(self) -> None:
        report = LoggingReport(
            level=LogLevel.INFO,
            component_count=3,
            handlers=(),
        )
        assert report.level == LogLevel.INFO
        assert report.component_count == 3
        assert report.dropped_messages == 0


# ── Exceptions ──


class TestLoggingExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(HandlerRegistrationError, LoggingError)
        assert issubclass(LoggingError, Exception)


# ── LoggingContext ──


class TestLoggingContext:
    def teardown_method(self) -> None:
        LoggingContext.clear()

    def test_bind_and_current(self) -> None:
        LoggingContext.bind(pipeline_id="pl-001", trade_id="tr-xyz")
        ctx = LoggingContext.current()
        assert ctx["pipeline_id"] == "pl-001"
        assert ctx["trade_id"] == "tr-xyz"

    def test_current_empty_by_default(self) -> None:
        LoggingContext.clear()
        ctx = LoggingContext.current()
        assert ctx == {}

    def test_get_single_key(self) -> None:
        LoggingContext.bind(correlation_id="corr-123")
        assert LoggingContext.get("correlation_id") == "corr-123"
        assert LoggingContext.get("nonexistent") is None

    def test_scope_restores_context(self) -> None:
        LoggingContext.bind(pipeline_id="pl-original")
        with LoggingContext.scope(pipeline_id="pl-override"):
            assert LoggingContext.get("pipeline_id") == "pl-override"
        assert LoggingContext.get("pipeline_id") == "pl-original"

    def test_scope_nested(self) -> None:
        LoggingContext.bind(pipeline_id="pl-1")
        with LoggingContext.scope(trade_id="tr-1"):
            assert LoggingContext.get("pipeline_id") == "pl-1"
            assert LoggingContext.get("trade_id") == "tr-1"
            with LoggingContext.scope(trade_id="tr-2"):
                assert LoggingContext.get("trade_id") == "tr-2"
            assert LoggingContext.get("trade_id") == "tr-1"
        assert LoggingContext.get("trade_id") is None

    def test_clear(self) -> None:
        LoggingContext.bind(pipeline_id="pl-001")
        LoggingContext.clear()
        assert LoggingContext.current() == {}

    def test_extra_metadata(self) -> None:
        LoggingContext.bind(extra={"user": "test"})
        ctx = LoggingContext.current()
        assert ctx["user"] == "test"

    def test_custom_extra_key(self) -> None:
        LoggingContext.bind(custom_key="custom_value")
        ctx = LoggingContext.current()
        assert ctx["custom_key"] == "custom_value"


# ── Formatters ──


class TestConsoleFormatter:
    def test_format_info(self) -> None:
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.INFO,
            module="test",
            component="comp",
            message="hello",
        )
        fmt = ConsoleFormatter(colorize=False)
        result = fmt.format(entry)
        assert "2026-07-08 12:00:00" in result
        assert "INFO" in result
        assert "hello" in result

    def test_format_with_context(self) -> None:
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.WARNING,
            module="risk",
            component="risk_manager",
            message="Drawdown limit approaching",
            pipeline_id="pl-001",
            trade_id="tr-xyz",
            duration_ms=50.5,
        )
        fmt = ConsoleFormatter(colorize=False)
        result = fmt.format(entry)
        assert "pipeline=pl-001" in result
        assert "trade=tr-xyz" in result
        assert "duration=50.5ms" in result

    def test_format_with_exception(self) -> None:
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.ERROR,
            module="execution",
            component="executor",
            message="Failed",
            exception="ConnectionError",
        )
        fmt = ConsoleFormatter(colorize=False)
        result = fmt.format(entry)
        assert "exception=ConnectionError" in result


class TestJSONFormatter:
    def test_format(self) -> None:
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.INFO,
            module="test",
            component="comp",
            message="hello",
        )
        fmt = JSONFormatter()
        result = fmt.format(entry)
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello"
        assert parsed["component"] == "comp"
        assert parsed["module"] == "test"

    def test_format_with_all_fields(self) -> None:
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.ERROR,
            module="execution",
            component="order_manager",
            message="Order failed",
            metadata={"order_type": "LIMIT"},
            exception="TimeoutError",
            duration_ms=1500.5,
            pipeline_id="pl-001",
            correlation_id="corr-abc",
            trade_id="tr-xyz",
            order_id="ord-123",
            position_id="pos-456",
            runtime_id="rt-789",
            request_id="req-000",
        )
        fmt = JSONFormatter()
        result = fmt.format(entry)
        parsed = json.loads(result)
        assert parsed["pipeline_id"] == "pl-001"
        assert parsed["correlation_id"] == "corr-abc"
        assert parsed["duration_ms"] == 1500.5
        assert parsed["metadata"]["order_type"] == "LIMIT"


class TestCompactFormatter:
    def test_format(self) -> None:
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.INFO,
            module="test",
            component="comp",
            message="hello",
        )
        fmt = CompactFormatter()
        result = fmt.format(entry)
        assert result.startswith("12:00:00")
        assert "I" in result
        assert "comp" in result
        assert "hello" in result


# ── ConsoleHandler ──


class TestConsoleHandler:
    def test_emit_info(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.CONSOLE,
        )
        handler = ConsoleHandler(config)
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.INFO,
            module="test",
            component="comp",
            message="test",
        )
        handler.emit(entry)
        assert handler.dropped == 0

    def test_below_level_dropped(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.ERROR,
            formatter=FormatterType.CONSOLE,
        )
        handler = ConsoleHandler(config)
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.INFO,
            module="test",
            component="comp",
            message="test",
        )
        handler.emit(entry)
        assert handler.dropped == 1

    def test_output_capture(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.COMPACT,
        )
        handler = ConsoleHandler(config)
        entry = LogEntry(
            timestamp=datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.INFO,
            module="test",
            component="comp",
            message="hello",
        )
        handler.emit(entry)
        output = handler._stdout.getvalue()
        assert "hello" in output


# ── FileHandler ──


class TestFileHandler:
    def test_requires_file_path(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.FILE,
            level=LogLevel.DEBUG,
        )
        with pytest.raises(HandlerRegistrationError):
            FileHandler(config)


# ── JSONFileHandler ──


class TestJSONFileHandler:
    def test_requires_file_path(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.JSON_FILE,
            level=LogLevel.DEBUG,
        )
        with pytest.raises(HandlerRegistrationError):
            JSONFileHandler(config)


# ── StructuredLogger ──


class TestStructuredLogger:
    def test_create_logger(self) -> None:
        logger = StructuredLogger("test_module", "test_component")
        assert logger.module == "test_module"
        assert logger.component == "test_component"

    def test_log_methods(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.TRACE,
            formatter=FormatterType.CONSOLE,
        )
        handler = ConsoleHandler(config)
        logger = StructuredLogger("test", "comp", handlers=[handler])

        logger.trace("trace msg")
        assert handler.dropped == 0

        logger.debug("debug msg")
        assert handler.dropped == 0

        logger.info("info msg")
        assert handler.dropped == 0

        logger.warning("warning msg")
        assert handler.dropped == 0

        logger.error("error msg")
        assert handler.dropped == 0

        logger.critical("critical msg")
        assert handler.dropped == 0

    def test_log_with_metadata(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.COMPACT,
        )
        handler = ConsoleHandler(config)
        logger = StructuredLogger("test", "comp", handlers=[handler])

        logger.info("order placed", order_id="ord-123", side="BUY")
        assert handler.dropped == 0

    def test_log_with_exception(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.COMPACT,
        )
        handler = ConsoleHandler(config)
        logger = StructuredLogger("test", "comp", handlers=[handler])

        try:
            raise ValueError("test error")
        except ValueError as e:
            logger.error("operation failed", exc_info=e)

        assert handler.dropped == 0

    def test_duration_method(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.CONSOLE,
        )
        handler = ConsoleHandler(config)
        logger = StructuredLogger("test", "comp", handlers=[handler])

        logger.duration("request completed", duration_ms=150.5)
        output = handler._stdout.getvalue()
        assert "duration=150.5ms" in output

    def test_exception_method(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.COMPACT,
        )
        handler = ConsoleHandler(config)
        logger = StructuredLogger("test", "comp", handlers=[handler])

        try:
            raise RuntimeError("runtime failure")
        except RuntimeError as e:
            logger.exception("caught exception", exc_info=e)

        assert handler.dropped == 0


# ── LoggerManager ──


class TestLoggerManager:
    def teardown_method(self) -> None:
        LoggerManager.reset_instance()

    def test_singleton(self) -> None:
        m1 = LoggerManager.instance()
        m2 = LoggerManager.instance()
        assert m1 is m2

    def test_get_logger(self) -> None:
        manager = LoggerManager()
        logger = manager.get_logger("execution", "order_manager")
        assert logger.module == "execution"
        assert logger.component == "order_manager"

    def test_get_logger_default_component(self) -> None:
        manager = LoggerManager()
        logger = manager.get_logger("execution")
        assert logger.module == "execution"
        assert logger.component == "execution"

    def test_get_or_create_logger(self) -> None:
        manager = LoggerManager()
        logger = manager.get_or_create_logger("risk", "risk_manager")
        assert logger.module == "risk"

    def test_logger_exists(self) -> None:
        manager = LoggerManager()
        assert not manager.logger_exists("nonexistent")
        manager.get_logger("exists", "test")
        assert manager.logger_exists("exists", "test")

    def test_configure(self) -> None:
        manager = LoggerManager()
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            handlers=(
                HandlerConfig(
                    handler_type=HandlerType.CONSOLE,
                    level=LogLevel.DEBUG,
                    formatter=FormatterType.COMPACT,
                ),
            ),
            component="titan_test",
        )
        manager.configure(config)
        report = manager.generate_report()
        assert report.level == LogLevel.DEBUG
        assert len(report.handlers) == 1

    def test_configure_sets_logger_handlers(self) -> None:
        manager = LoggerManager()
        config = LoggingConfig(
            level=LogLevel.INFO,
            handlers=(
                HandlerConfig(
                    handler_type=HandlerType.CONSOLE,
                    level=LogLevel.DEBUG,
                    formatter=FormatterType.COMPACT,
                ),
            ),
        )
        manager.configure(config)
        logger = manager.get_logger("test", "tester")
        logger.info("after configure")
        assert sum(h.dropped for h in manager.handlers()) == 0

    def test_configure_from_dict(self) -> None:
        manager = LoggerManager()
        manager.configure_from_dict(
            {
                "level": "DEBUG",
                "handlers": [
                    {
                        "type": "console",
                        "level": "DEBUG",
                        "formatter": "compact",
                    }
                ],
            }
        )
        report = manager.generate_report()
        assert report.level == LogLevel.DEBUG

    def test_generate_report(self) -> None:
        manager = LoggerManager()
        config = LoggingConfig(
            level=LogLevel.WARNING,
            handlers=(
                HandlerConfig(
                    handler_type=HandlerType.CONSOLE,
                    level=LogLevel.ERROR,
                    formatter=FormatterType.JSON,
                ),
            ),
        )
        manager.configure(config)
        report = manager.generate_report()
        assert report.level == LogLevel.WARNING
        assert report.component_count == 0

        manager.get_logger("a", "b")
        report2 = manager.generate_report()
        assert report2.component_count == 1

    def test_reconfigure(self) -> None:
        manager = LoggerManager()
        config1 = LoggingConfig(
            level=LogLevel.DEBUG,
            handlers=(
                HandlerConfig(
                    handler_type=HandlerType.CONSOLE,
                    level=LogLevel.DEBUG,
                    formatter=FormatterType.CONSOLE,
                ),
            ),
        )
        manager.configure(config1)
        assert manager.generate_report().level == LogLevel.DEBUG

        config2 = LoggingConfig(
            level=LogLevel.ERROR,
            handlers=(),
        )
        manager.reconfigure(config2)
        assert manager.generate_report().level == LogLevel.ERROR


# ── Module-level convenience ──


class TestModuleLevel:
    def teardown_method(self) -> None:
        LoggerManager.reset_instance()

    def test_get_logger_convenience(self) -> None:
        from titan.logging import get_logger, configure

        config = LoggingConfig(
            level=LogLevel.DEBUG,
            handlers=(
                HandlerConfig(
                    handler_type=HandlerType.CONSOLE,
                    level=LogLevel.DEBUG,
                    formatter=FormatterType.COMPACT,
                ),
            ),
        )
        configure(config)
        logger = get_logger("test", "comp")
        assert logger.module == "test"

    def test_configure_and_report(self) -> None:
        from titan.logging import configure, generate_report

        config = LoggingConfig(
            level=LogLevel.INFO,
            handlers=(),
        )
        configure(config)
        report = generate_report()
        assert report.level == LogLevel.INFO


# ── Context propagation through logger ──


class TestContextPropagation:
    def teardown_method(self) -> None:
        LoggingContext.clear()
        LoggerManager.reset_instance()

    def test_context_in_log_entry(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.CONSOLE,
        )
        handler = ConsoleHandler(config)
        logger = StructuredLogger("test", "comp", handlers=[handler])

        LoggingContext.bind(pipeline_id="pl-ctx-001", trade_id="tr-ctx-xyz")
        logger.info("context test")

        output = handler._stdout.getvalue()
        assert "pipeline=pl-ctx-001" in output
        assert "trade=tr-ctx-xyz" in output

    def test_context_scope_isolation(self) -> None:
        config = HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.CONSOLE,
        )
        handler = ConsoleHandler(config)
        logger = StructuredLogger("test", "comp", handlers=[handler])

        LoggingContext.bind(pipeline_id="pl-outer")

        with LoggingContext.scope(pipeline_id="pl-inner"):
            logger.info("inside scope")
        logger.info("outside scope")

        output = handler._stdout.getvalue()
        assert "pipeline=pl-inner" in output
        assert "pipeline=pl-outer" in output

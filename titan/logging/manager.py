from __future__ import annotations

from threading import Lock
from typing import Any

from titan.logging.handlers import (
    ConsoleHandler,
    FileHandler,
    Handler,
    JSONFileHandler,
)
from titan.logging.logger import StructuredLogger
from titan.logging.models import (
    FormatterType,
    HandlerConfig,
    HandlerType,
    LogLevel,
    LoggingConfig,
    LoggingReport,
)


class LoggerManager:
    """Central logger registry and configuration manager.

    All TITAN modules obtain their loggers through this manager::

        manager = LoggerManager()
        manager.configure(config)

        logger = manager.get_logger("execution", "order_manager")
        logger.info("System started")
    """

    _instance: LoggerManager | None = None
    _instance_lock = Lock()

    def __init__(self) -> None:
        self._loggers: dict[str, StructuredLogger] = {}
        self._handlers: list[Handler] = []
        self._config: LoggingConfig = LoggingConfig()
        self._configured: bool = False
        self._lock = Lock()

    # ── Singleton ──

    @classmethod
    def instance(cls) -> LoggerManager:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    # ── Configuration ──

    def configure(self, config: LoggingConfig) -> None:
        with self._lock:
            self._handlers = self._build_handlers(config)
            self._config = config
            self._configured = True
            self._update_existing_loggers()

    def configure_from_dict(self, data: dict[str, Any]) -> None:
        level = LogLevel(data.get("level", "INFO"))
        raw_handlers = data.get("handlers")
        handlers: tuple[HandlerConfig, ...] = ()
        if raw_handlers:
            handler_configs = []
            for h in raw_handlers:
                handler_configs.append(
                    HandlerConfig(
                        handler_type=HandlerType(h.get("type", "console")),
                        level=LogLevel(h.get("level", "DEBUG")),
                        formatter=FormatterType(h.get("formatter", "console")),
                        file_path=h.get("file_path", ""),
                        max_size_mb=h.get("max_size_mb", 100),
                        backup_count=h.get("backup_count", 5),
                    )
                )
            handlers = tuple(handler_configs)
        component = data.get("component", "titan")
        cfg = LoggingConfig(level=level, handlers=handlers, component=component)
        self.configure(cfg)

    def reconfigure(self, config: LoggingConfig) -> None:
        with self._lock:
            self._handlers.clear()
            self._handlers = self._build_handlers(config)
            self._config = config
            self._update_existing_loggers()

    # ── Logger access ──

    def get_logger(
        self,
        module: str,
        component: str | None = None,
    ) -> StructuredLogger:
        key = f"{module}:{component or module}"
        with self._lock:
            if key not in self._loggers:
                logger = StructuredLogger(
                    module=module,
                    component=component or module,
                    handlers=list(self._handlers),
                )
                self._loggers[key] = logger
            return self._loggers[key]

    def get_or_create_logger(
        self,
        module: str,
        component: str | None = None,
    ) -> StructuredLogger:
        return self.get_logger(module, component)

    def logger_exists(self, module: str, component: str | None = None) -> bool:
        key = f"{module}:{component or module}"
        return key in self._loggers

    # ── Reporting ──

    def generate_report(self) -> LoggingReport:
        level = self._config.level
        handler_configs = tuple(h.config for h in self._handlers)
        dropped = sum(h.dropped for h in self._handlers)
        return LoggingReport(
            level=level,
            component_count=len(self._loggers),
            handlers=handler_configs,
            dropped_messages=dropped,
        )

    def handlers(self) -> tuple[Handler, ...]:
        return tuple(self._handlers)

    def _update_existing_loggers(self) -> None:
        for logger in self._loggers.values():
            logger.remove_handlers()
            for handler in self._handlers:
                logger.add_handler(handler)

    @staticmethod
    def _build_handlers(config: LoggingConfig) -> list[Handler]:
        handlers: list[Handler] = []
        for hc in config.handlers:
            if hc.handler_type == HandlerType.CONSOLE:
                handlers.append(ConsoleHandler(hc))
            elif hc.handler_type == HandlerType.FILE:
                handlers.append(FileHandler(hc))
            elif hc.handler_type == HandlerType.JSON_FILE:
                handlers.append(JSONFileHandler(hc))
        return handlers


# ── Module-level convenience ──


_manager = LoggerManager()


def configure(config: LoggingConfig) -> None:
    _manager.configure(config)


def get_logger(
    module: str,
    component: str | None = None,
) -> StructuredLogger:
    return _manager.get_logger(module, component)


def generate_report() -> LoggingReport:
    return _manager.generate_report()

from __future__ import annotations

import io
import os
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from titan.logging.exceptions import HandlerRegistrationError
from titan.logging.formatter import (
    CompactFormatter,
    ConsoleFormatter,
    Formatter,
    JSONFormatter,
)
from titan.logging.models import (
    FormatterType,
    HandlerConfig,
    HandlerType,
    LogEntry,
    LogLevel,
)


class Handler(ABC):
    """Abstract base for all log handlers."""

    def __init__(self, config: HandlerConfig) -> None:
        self._config = config
        self._level = config.level
        self._formatter = self._create_formatter(config)
        self._dropped: int = 0
        self._lock = Lock()

    @abstractmethod
    def emit(self, entry: LogEntry) -> None: ...

    def should_emit(self, level: LogLevel) -> bool:
        return level.to_int() >= self._level.to_int()

    @property
    def config(self) -> HandlerConfig:
        return self._config

    @property
    def dropped(self) -> int:
        return self._dropped

    def _format(self, entry: LogEntry) -> str:
        return self._formatter.format(entry)

    @staticmethod
    def _create_formatter(config: HandlerConfig) -> Formatter:
        if config.formatter == FormatterType.JSON:
            return JSONFormatter()
        if config.formatter == FormatterType.COMPACT:
            return CompactFormatter()
        return ConsoleFormatter(colorize=config.colorize)


class ConsoleHandler(Handler):
    """Writes formatted log output to stdout or stderr.

    ERROR and CRITICAL levels go to stderr; everything else to stdout.
    """

    def __init__(self, config: HandlerConfig) -> None:
        super().__init__(config)
        self._stdout: io.StringIO = io.StringIO()
        self._stderr: io.StringIO = io.StringIO()

    def emit(self, entry: LogEntry) -> None:
        if not self.should_emit(entry.level):
            self._dropped += 1
            return
        line = self._format(entry) + "\n"
        if entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
            self._stderr.write(line)
        else:
            self._stdout.write(line)


class FileHandler(Handler):
    """Writes formatted log output to a file with optional rotation."""

    def __init__(self, config: HandlerConfig) -> None:
        super().__init__(config)
        if not config.file_path:
            raise HandlerRegistrationError("FileHandler requires a file_path")
        self._path = Path(config.file_path)
        self._max_bytes = config.max_size_mb * 1024 * 1024
        self._backup_count = config.backup_count
        self._encoding = config.encoding or "utf-8"
        self._bytes_written: int = 0
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _rotate_if_needed(self) -> None:
        if self._bytes_written < self._max_bytes:
            return
        self._rotate()
        self._bytes_written = 0

    def _rotate(self) -> None:
        for i in range(self._backup_count - 1, 0, -1):
            src = self._path.with_suffix(f".{i}.log")
            dst = self._path.with_suffix(f".{i + 1}.log")
            if src.exists():
                try:
                    os.replace(str(src), str(dst))
                except OSError:
                    pass
        primary = self._path.with_suffix(".1.log")
        try:
            os.replace(str(self._path), str(primary))
        except OSError:
            pass

    def emit(self, entry: LogEntry) -> None:
        if not self.should_emit(entry.level):
            self._dropped += 1
            return
        line = self._format(entry) + "\n"
        encoded = line.encode(self._encoding, errors="replace")
        with self._lock:
            self._rotate_if_needed()
            try:
                with open(self._path, "ab") as f:
                    f.write(encoded)
                self._bytes_written += len(encoded)
            except OSError:
                pass


class JSONFileHandler(Handler):
    """Writes JSON-formatted log entries to a file, one object per line."""

    def __init__(self, config: HandlerConfig) -> None:
        json_config = HandlerConfig(
            handler_type=HandlerType.JSON_FILE,
            level=config.level,
            formatter=FormatterType.JSON,
            file_path=config.file_path,
            max_size_mb=config.max_size_mb,
            backup_count=config.backup_count,
            encoding=config.encoding,
            colorize=False,
        )
        super().__init__(json_config)
        if not config.file_path:
            raise HandlerRegistrationError("JSONFileHandler requires a file_path")
        self._path = Path(config.file_path)
        self._max_bytes = config.max_size_mb * 1024 * 1024
        self._backup_count = config.backup_count
        self._encoding = config.encoding or "utf-8"
        self._bytes_written: int = 0
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _rotate_if_needed(self) -> None:
        if self._bytes_written < self._max_bytes:
            return
        for i in range(self._backup_count - 1, 0, -1):
            src = self._path.with_suffix(f".{i}.jsonl")
            dst = self._path.with_suffix(f".{i + 1}.jsonl")
            if src.exists():
                try:
                    os.replace(str(src), str(dst))
                except OSError:
                    pass
        primary = self._path.with_suffix(".1.jsonl")
        try:
            os.replace(str(self._path), str(primary))
        except OSError:
            pass
        self._bytes_written = 0

    def emit(self, entry: LogEntry) -> None:
        if not self.should_emit(entry.level):
            self._dropped += 1
            return
        line = self._format(entry) + "\n"
        encoded = line.encode(self._encoding, errors="replace")
        with self._lock:
            self._rotate_if_needed()
            try:
                with open(self._path, "ab") as f:
                    f.write(encoded)
                self._bytes_written += len(encoded)
            except OSError:
                pass

"""titan runtime - Transport abstractions for the runtime service."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from titan.runtime.models import RuntimeReport
    from titan.runtime.service import RuntimeService


class RuntimeTransport(abc.ABC):
    """Abstract interface for communicating with the RuntimeService.

    This interface defines the standard operations available for
    controlling and interrogating the TITAN runtime engine. Future
    implementations might include SocketTransport, RESTTransport, etc.
    """

    @abc.abstractmethod
    def start(self) -> None:
        """Start the runtime engine."""
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the runtime engine."""
        pass

    @abc.abstractmethod
    def restart(self) -> None:
        """Restart the runtime engine."""
        pass

    @abc.abstractmethod
    def status(self) -> RuntimeReport:
        """Get the current status of the runtime engine."""
        pass

    @abc.abstractmethod
    def enable_paper(self) -> None:
        """Enable paper trading mode."""
        pass

    @abc.abstractmethod
    def disable_paper(self) -> None:
        """Disable paper trading mode."""
        pass


class InProcessTransport(RuntimeTransport):
    """Direct, in-memory transport for the RuntimeService.

    Used when the caller and the RuntimeService reside within the
    same Python process, eliminating IPC overhead.
    """

    def __init__(self, service: RuntimeService):
        """Initialize with an active RuntimeService instance."""
        self.service = service

    def start(self) -> None:
        self.service.start()

    def stop(self) -> None:
        self.service.stop()

    def restart(self) -> None:
        self.service.restart()

    def status(self) -> RuntimeReport:
        return self.service.status()

    def enable_paper(self) -> None:
        self.service.enable_paper()

    def disable_paper(self) -> None:
        self.service.disable_paper()

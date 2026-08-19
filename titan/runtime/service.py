"""titan runtime - Pure application logic service layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from titan.runtime.models import RuntimeReport
    from titan.runtime.runtime import RuntimeEngine


class RuntimeService:
    """Pure application logic service wrapping the RuntimeEngine.

    This acts as the service owner, providing a clean interface
    for controlling the runtime engine without any networking
    or transport concerns.
    """

    def __init__(self, engine: RuntimeEngine):
        """Initialize the service with a RuntimeEngine instance."""
        self.engine = engine

    def start(self) -> None:
        """Start the runtime engine."""
        self.engine.start()

    def stop(self) -> None:
        """Stop the runtime engine."""
        self.engine.stop()

    def restart(self) -> None:
        """Restart the runtime engine."""
        self.engine.restart()

    def status(self) -> RuntimeReport:
        """Get the current status of the runtime engine."""
        return self.engine.generate_report()

    def enable_paper(self) -> None:
        """Enable paper trading.

        Currently a stub, to be implemented as needed when
        PaperBroker configurations are integrated.
        """
        # TODO: Implement paper trading enablement logic

    def disable_paper(self) -> None:
        """Disable paper trading."""
        # TODO: Implement paper trading disablement logic

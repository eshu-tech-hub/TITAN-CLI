"""Owned startup for detached TITAN runtime processes."""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from titan.runtime.exceptions import RuntimeError as TitanRuntimeError
from titan.runtime.local_transport import DEFAULT_PORT, LocalTransport
from titan.runtime.models import RuntimeStatus


@dataclass(frozen=True, slots=True)
class DetachedRuntimeLauncher:
    """Launch a runtime process and wait until its IPC service is ready."""

    port: int = DEFAULT_PORT
    readiness_timeout_seconds: float = 30.0
    poll_interval_seconds: float = 0.05

    def __post_init__(self) -> None:
        if not 0 < self.port < 65536:
            raise ValueError("port must be between 1 and 65535")
        if self.readiness_timeout_seconds <= 0:
            raise ValueError("readiness_timeout_seconds must be positive")
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")

    def launch(
        self,
        command: Sequence[str],
        *,
        log_path: Path,
    ) -> subprocess.Popen[bytes]:
        """Start *command* detached and verify its runtime service is running."""
        if not command:
            raise ValueError("A detached runtime command is required.")

        log_path.parent.mkdir(parents=True, exist_ok=True)
        creationflags = 0
        if sys.platform == "win32":
            creationflags = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )

        with log_path.open("ab") as log_file:
            process = subprocess.Popen(
                list(command),
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=log_file,
                close_fds=True,
                creationflags=creationflags,
            )

        try:
            self._wait_until_ready(process)
        except Exception:
            self._terminate(process)
            raise

        return process

    def _wait_until_ready(self, process: subprocess.Popen[bytes]) -> None:
        deadline = time.monotonic() + self.readiness_timeout_seconds
        last_error = "The runtime IPC service did not become available."

        while time.monotonic() < deadline:
            return_code = process.poll()
            if return_code is not None:
                raise TitanRuntimeError(
                    f"Detached runtime exited during startup with code {return_code}."
                )

            try:
                report = LocalTransport(port=self.port).status()
                if report.runtime_status == RuntimeStatus.RUNNING:
                    return
                last_error = f"Runtime reported {report.runtime_status.value}."
            except TitanRuntimeError as exc:
                last_error = str(exc)

            time.sleep(self.poll_interval_seconds)

        raise TitanRuntimeError(
            "Timed out waiting for detached runtime readiness: " + last_error
        )

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

from titan import __version__
from titan.deployment.models import VersionInfo


class VersionManager:
    """Collects and exposes TITAN version and build metadata.

    Provides a single source of truth for version information across
    CLI, Docker, systemd, and monitoring systems.
    """

    _instance: VersionManager | None = None

    def __init__(self) -> None:
        self._info = self._collect()

    @classmethod
    def instance(cls) -> VersionManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def get(self) -> VersionInfo:
        return self._info

    @property
    def version(self) -> str:
        return self._info.version

    @property
    def build_number(self) -> str:
        return self._info.build_number

    @property
    def git_commit(self) -> str:
        return self._info.git_commit

    def to_dict(self) -> dict[str, str]:
        return {
            "version": self._info.version,
            "build_number": self._info.build_number,
            "git_commit": self._info.git_commit,
            "git_branch": self._info.git_branch,
            "build_timestamp": self._info.build_timestamp,
            "python_version": self._info.python_version,
            "platform": self._info.platform,
            "machine": self._info.machine,
        }

    @staticmethod
    def _collect() -> VersionInfo:
        git_commit = VersionManager._git_commit()
        git_branch = VersionManager._git_branch()
        return VersionInfo(
            version=__version__,
            build_number=VersionManager._build_number(),
            git_commit=git_commit,
            git_branch=git_branch,
            build_timestamp=VersionManager._build_timestamp(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            platform=sys.platform,
            machine=platform.machine(),
        )

    @staticmethod
    def _git_commit() -> str:
        try:
            root = Path(__file__).resolve().parent.parent.parent
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return ""

    @staticmethod
    def _git_branch() -> str:
        try:
            root = Path(__file__).resolve().parent.parent.parent
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return ""

    @staticmethod
    def _build_number() -> str:
        import os

        return os.environ.get("TITAN_BUILD_NUMBER", "")

    @staticmethod
    def _build_timestamp() -> str:
        import os

        return os.environ.get("TITAN_BUILD_TIMESTAMP", "")

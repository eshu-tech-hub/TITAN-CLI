from __future__ import annotations

import os
import sys
from pathlib import Path

from titan.deployment.exceptions import EnvironmentError
from titan.deployment.models import DeploymentEnvironment, EnvironmentReport

REQUIRED_DIRECTORIES = ("data", "logs")
MIN_PYTHON_MAJOR = 3
MIN_PYTHON_MINOR = 12


class EnvironmentManager:
    """Validates and resolves the deployment environment.

    Ensures the runtime environment meets all prerequisites:
    correct Python version, required directories, broker configuration,
    and dependency availability.
    """

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self._root = Path(root_dir) if root_dir else Path.cwd()

    def resolve(self, profile: str | None = None) -> DeploymentEnvironment:
        """Resolve the active environment from profile or environment variable."""
        if profile:
            return self._map_profile(profile)

        env_var = os.environ.get("TITAN_ENVIRONMENT", "").lower()
        if env_var:
            try:
                return DeploymentEnvironment(env_var)
            except ValueError:
                raise EnvironmentError(
                    f"Invalid TITAN_ENVIRONMENT value: {env_var!r}. "
                    f"Valid: {[e.value for e in DeploymentEnvironment]}"
                )

        return DeploymentEnvironment.DEVELOPMENT

    def validate(self, environment: DeploymentEnvironment) -> EnvironmentReport:
        """Run full environment validation and return a report."""
        warnings: list[str] = []
        errors: list[str] = []

        config_loaded = True
        config_valid = True
        secrets_available = True
        dirs_ok = True
        python_ok = True
        deps_ok = True
        broker_ok = True

        python_ok, py_err = self._check_python()
        if py_err:
            errors.append(py_err)

        dirs_ok, dir_warns = self._check_directories()
        warnings.extend(dir_warns)

        deps_ok, dep_err = self._check_dependencies()
        if dep_err:
            errors.append(dep_err)

        config_loaded, config_valid, cfg_warns, cfg_errs = self._check_config()
        warnings.extend(cfg_warns)
        errors.extend(cfg_errs)

        secrets_available = self._check_secrets(environment)
        broker_ok = self._check_broker_config()

        return EnvironmentReport(
            environment=environment,
            config_loaded=config_loaded,
            config_valid=config_valid,
            secrets_available=secrets_available,
            directories_verified=dirs_ok,
            python_version_ok=python_ok,
            dependencies_ok=deps_ok,
            broker_configured=broker_ok,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    def ensure_directories(self) -> None:
        """Create required directories if they do not exist."""
        for dirname in REQUIRED_DIRECTORIES:
            directory = self._root / dirname
            directory.mkdir(parents=True, exist_ok=True)

        log_dir = self._root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

    def _check_python(self) -> tuple[bool, str]:
        if sys.version_info.major < MIN_PYTHON_MAJOR:
            return False, (
                f"Python {MIN_PYTHON_MAJOR}+ required, "
                f"found {sys.version_info.major}.{sys.version_info.minor}"
            )
        if (
            sys.version_info.major == MIN_PYTHON_MAJOR
            and sys.version_info.minor < MIN_PYTHON_MINOR
        ):
            return False, (
                f"Python {MIN_PYTHON_MAJOR}.{MIN_PYTHON_MINOR}+ required, "
                f"found {sys.version_info.major}.{sys.version_info.minor}"
            )
        return True, ""

    def _check_directories(self) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        all_ok = True
        for dirname in REQUIRED_DIRECTORIES:
            d = self._root / dirname
            if not d.exists():
                warnings.append(
                    f"Directory '{dirname}' does not exist (will be created)"
                )
                all_ok = False
        return all_ok, warnings

    def _check_dependencies(self) -> tuple[bool, str]:
        required = ["typer", "rich", "loguru"]
        missing: list[str] = []
        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        if missing:
            return False, f"Missing dependencies: {', '.join(missing)}"
        return True, ""

    def _check_config(self) -> tuple[bool, bool, list[str], list[str]]:
        warnings: list[str] = []
        errors: list[str] = []
        loaded = True
        valid = True

        env_file = self._root / ".env"
        if not env_file.exists():
            warnings.append(".env file not found (using defaults)")

        return loaded, valid, warnings, errors

    def _check_secrets(self, environment: DeploymentEnvironment) -> bool:
        if environment in (
            DeploymentEnvironment.DEVELOPMENT,
            DeploymentEnvironment.TESTING,
            DeploymentEnvironment.BACKTESTING,
        ):
            return True
        api_key = os.environ.get("TITAN_BROKER_API_KEY", "")
        return bool(api_key)

    def _check_broker_config(self) -> bool:
        provider = os.environ.get("TITAN_BROKER_PROVIDER", "paper")
        if provider == "paper":
            return True
        return bool(os.environ.get("TITAN_BROKER_API_KEY", ""))

    @staticmethod
    def _map_profile(profile: str) -> DeploymentEnvironment:
        mapping = {
            "development": DeploymentEnvironment.DEVELOPMENT,
            "dev": DeploymentEnvironment.DEVELOPMENT,
            "testing": DeploymentEnvironment.TESTING,
            "test": DeploymentEnvironment.TESTING,
            "paper": DeploymentEnvironment.PAPER_TRADING,
            "paper_trading": DeploymentEnvironment.PAPER_TRADING,
            "backtesting": DeploymentEnvironment.BACKTESTING,
            "backtest": DeploymentEnvironment.BACKTESTING,
            "production": DeploymentEnvironment.PRODUCTION,
            "prod": DeploymentEnvironment.PRODUCTION,
        }
        key = profile.lower().strip()
        if key in mapping:
            return mapping[key]
        raise EnvironmentError(
            f"Unknown profile: {profile!r}. Valid: {list(mapping.keys())}"
        )

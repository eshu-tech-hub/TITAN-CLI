from __future__ import annotations

from pathlib import Path
from typing import Any

from titan.config.exceptions import (
    ConfigError,
    ConfigLoadError,
    ConfigValidationError,
)
from titan.config.loader import load_env, load_json, load_yaml, merge_sources
from titan.config.models import (
    AppConfig,
    BrokerConfig,
    ConfigurationReport,
    ExecutionConfig,
    LoggingConfig,
    MonitoringConfig,
    RiskConfig,
    RuntimeConfig,
    TitanConfig,
)
from titan.config.profiles import profile_defaults
from titan.config.secrets import EnvironmentSecretsProvider, SecretsProvider
from titan.config.validator import validate


class ConfigManager:
    """Central configuration manager for the TITAN platform.

    Loads, validates, merges, and caches configuration from multiple
    sources. Provides immutable ``TitanConfig`` to all consumers.

    Source precedence (highest wins):
        1. Environment variables (``TITAN_*``)
        2. Config file (JSON or YAML) / dict loads
        3. Profile defaults
        4. Built-in defaults

    Usage::

        manager = ConfigManager()
        manager.load_file("config/production.yaml")
        manager.set_profile("production")
        config = manager.get_config()
    """

    def __init__(
        self,
        secrets_provider: SecretsProvider | None = None,
        env_prefix: str = "TITAN",
    ) -> None:
        self._secrets = secrets_provider or EnvironmentSecretsProvider()
        self._env_prefix = env_prefix
        self._profile: str = "development"
        self._sources: list[str] = []
        self._warnings: list[str] = []
        self._errors: list[str] = []
        self._raw: dict[str, Any] = {}
        self._config: TitanConfig | None = None
        self._loaded: bool = False
        self._frozen: bool = False

    # ── Public API ──────────────────────────────────────────────

    def set_profile(self, profile: str) -> None:
        """Set the active profile."""
        self._assert_mutable()
        profile_defaults(profile)
        self._profile = profile
        self._dirty()

    def load_file(self, path: str | Path) -> None:
        """Load a configuration file (JSON or YAML).

        The file extension determines the parser.
        """
        self._assert_mutable()
        p = Path(path)
        rp = str(p.resolve())

        if rp in self._sources:
            return

        if p.suffix.lower() in (".yaml", ".yml"):
            data = load_yaml(p)
        elif p.suffix.lower() == ".json":
            data = load_json(p)
        else:
            raise ConfigLoadError(
                f"Unsupported config file format: {p.suffix}. Use .yaml, .yml, or .json"
            )

        self._raw = merge_sources(self._raw, data)
        self._sources.append(rp)
        self._dirty()

    def load_dict(self, data: dict[str, Any], source: str = "<dict>") -> None:
        """Load configuration from an in-memory dictionary."""
        self._assert_mutable()
        if source not in self._sources:
            self._sources.append(source)
        self._raw = merge_sources(self._raw, data)
        self._dirty()

    def load_profile(self, profile: str) -> None:
        """Set profile."""
        self.set_profile(profile)

    def load_env(self) -> None:
        """Load configuration from environment variables."""
        self._assert_mutable()
        env_data = load_env(self._env_prefix)
        if env_data:
            self._raw = merge_sources(self._raw, env_data)
            source_tag = f"env:{self._env_prefix}_*"
            if source_tag not in self._sources:
                self._sources.append(source_tag)
            self._dirty()

    def reload(self) -> None:
        """Reload the configuration from all registered sources."""
        self._frozen = False
        self._loaded = False
        self._config = None
        sources = list(self._sources)
        profile = self._profile
        self._sources = []
        self._raw = {}
        self._warnings = []
        self._errors = []
        self._profile = profile

        for src in sources:
            if src.startswith("env:"):
                self.load_env()
            elif src.startswith("<"):
                continue
            else:
                try:
                    self.load_file(src)
                except ConfigLoadError:
                    pass

    def get_config(self) -> TitanConfig:
        """Get the validated, immutable configuration.

        Raises:
            ConfigValidationError: If the configuration has errors.
        """
        if not self._loaded:
            self._build()
        if self._errors:
            raise ConfigValidationError(
                f"Configuration has {len(self._errors)} error(s): "
                + "; ".join(self._errors[:5])
            )
        assert self._config is not None
        return self._config

    def generate_report(self) -> ConfigurationReport:
        """Generate a snapshot report of the configuration state."""
        if not self._loaded:
            try:
                self._build()
            except ConfigError:
                pass

        status = "valid"
        if self._errors:
            status = "invalid"
        elif self._warnings:
            status = "warnings"

        return ConfigurationReport(
            profile=self._profile,
            sources=tuple(self._sources),
            validation_status=status,
            warnings=tuple(self._warnings),
            errors=tuple(self._errors),
            config=self._config,
        )

    def secrets(self) -> SecretsProvider:
        """Access the secrets provider."""
        return self._secrets

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(self._sources)

    # ── Internal ────────────────────────────────────────────────

    def _dirty(self) -> None:
        self._loaded = False
        self._config = None

    def _build(self) -> None:
        """Build the final TitanConfig from all sources.

        Merge order (later overrides earlier):
            1. Built-in base defaults
            2. Profile-specific defaults
            3. User-loaded data (file / dict)
            4. Environment variables
        """
        merged: dict[str, Any] = {}
        base = _base_defaults()
        _deep_merge(merged, base)

        try:
            profile_overrides = profile_defaults(self._profile)
            _deep_merge(merged, profile_overrides)
        except ValueError:
            pass

        _deep_merge(merged, self._raw)

        self._warnings, self._errors = validate(merged)

        resolved = _resolve_secrets(self._secrets, merged)

        self._config = TitanConfig(
            profile=self._profile,
            app=AppConfig(**resolved.get("app", {})),
            broker=BrokerConfig(
                provider=resolved.get("broker", {}).get("provider", "angel_one"),
                exchange=resolved.get("broker", {}).get("exchange", "nse"),
                api_key=resolved.get("broker", {}).get("api_key", ""),
                client_id=resolved.get("broker", {}).get("client_id", ""),
                pin=resolved.get("broker", {}).get("pin", ""),
                totp_secret=resolved.get("broker", {}).get("totp_secret", ""),
                access_token=resolved.get("broker", {}).get("access_token", ""),
                paper_initial_cash=resolved.get("broker", {}).get(
                    "paper_initial_cash", 100000
                ),
                connection_timeout_seconds=resolved.get("broker", {}).get(
                    "connection_timeout_seconds", 30.0
                ),
                max_retries=resolved.get("broker", {}).get("max_retries", 3),
            ),
            runtime=RuntimeConfig(**resolved.get("runtime", {})),
            risk=RiskConfig(**resolved.get("risk", {})),
            execution=ExecutionConfig(**resolved.get("execution", {})),
            logging=LoggingConfig(**resolved.get("logging", {})),
            monitoring=MonitoringConfig(**resolved.get("monitoring", {})),
            custom=resolved.get("custom", {}),
        )
        self._loaded = True

    def _assert_mutable(self) -> None:
        if self._frozen:
            raise ConfigError("Configuration is frozen and cannot be modified.")


# ── Internal helpers ──


def _base_defaults() -> dict[str, Any]:
    return {
        "app": {
            "name": "TITAN",
            "version": "1.0.0",
            "environment": "development",
            "log_level": "INFO",
            "data_dir": "./data",
            "config_dir": "./config",
        },
        "broker": {
            "provider": "paper",
            "api_key": "",
            "client_id": "",
            "pin": "",
            "totp_secret": "",
            "access_token": "",
            "paper_initial_cash": 100000,
            "connection_timeout_seconds": 30.0,
            "max_retries": 3,
        },
        "runtime": {
            "pipeline_interval_seconds": 60.0,
            "heartbeat_interval_seconds": 10.0,
            "stream_enabled": False,
            "scheduler_enabled": True,
            "heartbeat_enabled": True,
            "max_pipeline_executions": 0,
        },
        "risk": {
            "max_position_size": 100000,
            "max_drawdown_percent": 20.0,
            "max_daily_loss": 50000,
            "max_leverage": 1.0,
            "margin_call_threshold_percent": 50.0,
            "stop_loss_percent": 5.0,
        },
        "execution": {
            "max_retries": 3,
            "retry_delay_seconds": 5.0,
            "order_timeout_seconds": 30.0,
            "default_slippage_percent": 0.1,
            "default_commission_flat": 10,
            "default_commission_percent": 0.01,
        },
        "logging": {
            "level": "INFO",
            "file": "./logs/titan.log",
            "max_size_mb": 100,
            "backup_count": 5,
            "format_template": "{time} | {level} | {name} | {message}",
        },
        "monitoring": {
            "enabled": False,
            "prometheus_port": 8000,
            "health_check_interval_seconds": 30.0,
        },
    }


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _resolve_secrets(
    secrets_provider: SecretsProvider, raw: dict[str, Any]
) -> dict[str, Any]:
    import copy

    result = copy.deepcopy(raw)
    _walk_and_resolve(secrets_provider, result)
    return result


_SECRET_PREFIX = "${"
_SECRET_SUFFIX = "}"


def _walk_and_resolve(secrets_provider: SecretsProvider, node: Any) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, str) and _is_secret_ref(value):
                secret_key = value[len(_SECRET_PREFIX) : -len(_SECRET_SUFFIX)]
                node[key] = secrets_provider.get(secret_key)
            else:
                _walk_and_resolve(secrets_provider, value)
    elif isinstance(node, list):
        for item in node:
            _walk_and_resolve(secrets_provider, item)


def _is_secret_ref(value: str) -> bool:
    return (
        value.startswith(_SECRET_PREFIX)
        and value.endswith(_SECRET_SUFFIX)
        and len(value) > len(_SECRET_PREFIX) + len(_SECRET_SUFFIX)
    )

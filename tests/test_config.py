from __future__ import annotations

import os
import tempfile
from decimal import Decimal

import pytest

from titan.config.exceptions import (
    ConfigError,
    ConfigLoadError,
    ConfigValidationError,
    SecretNotFoundError,
)
from titan.config.manager import ConfigManager
from titan.config.models import (
    AppConfig,
    BrokerConfig,
    ConfigurationReport,
    EnvironmentProfile,
    ExecutionConfig,
    LoggingConfig,
    LogLevel,
    MonitoringConfig,
    RiskConfig,
    RuntimeConfig,
    TitanConfig,
)
from titan.config.profiles import profile_defaults
from titan.config.secrets import (
    CompositeSecretsProvider,
    EncryptedFileSecretsProvider,
    EnvironmentSecretsProvider,
    InMemorySecretsProvider,
)

# ── Models ──


class TestEnvironmentProfile:
    def test_enum_values(self) -> None:
        assert EnvironmentProfile.DEVELOPMENT.value == "development"
        assert EnvironmentProfile.TESTING.value == "testing"
        assert EnvironmentProfile.PAPER_TRADING.value == "paper"
        assert EnvironmentProfile.BACKTESTING.value == "backtesting"
        assert EnvironmentProfile.PRODUCTION.value == "production"


class TestLogLevel:
    def test_enum_values(self) -> None:
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"


class TestAppConfig:
    def test_defaults(self) -> None:
        cfg = AppConfig()
        assert cfg.name == "TITAN"
        assert cfg.version == "1.0.0"
        assert cfg.environment == "development"
        assert cfg.log_level == "INFO"

    def test_frozen(self) -> None:
        cfg = AppConfig()
        with pytest.raises(AttributeError):
            cfg.name = "OTHER"  # type: ignore[misc]

    def test_custom_values(self) -> None:
        cfg = AppConfig(name="Custom", log_level="DEBUG", data_dir="/tmp/data")
        assert cfg.name == "Custom"
        assert cfg.log_level == "DEBUG"
        assert cfg.data_dir == "/tmp/data"


class TestBrokerConfig:
    def test_defaults(self) -> None:
        cfg = BrokerConfig()
        assert cfg.provider == "paper"
        assert cfg.paper_initial_cash == Decimal(100000)
        assert cfg.max_retries == 3

    def test_frozen(self) -> None:
        cfg = BrokerConfig()
        with pytest.raises(AttributeError):
            cfg.provider = "angel_one"  # type: ignore[misc]


class TestRuntimeConfig:
    def test_defaults(self) -> None:
        cfg = RuntimeConfig()
        assert cfg.pipeline_interval_seconds == 60.0
        assert cfg.heartbeat_interval_seconds == 10.0
        assert not cfg.stream_enabled
        assert cfg.scheduler_enabled


class TestRiskConfig:
    def test_defaults(self) -> None:
        cfg = RiskConfig()
        assert cfg.max_position_size == Decimal(100000)
        assert cfg.max_drawdown_percent == Decimal("20.0")
        assert cfg.max_leverage == Decimal("1.0")


class TestExecutionConfig:
    def test_defaults(self) -> None:
        cfg = ExecutionConfig()
        assert cfg.max_retries == 3
        assert cfg.default_slippage_percent == Decimal("0.1")


class TestLoggingConfig:
    def test_defaults(self) -> None:
        cfg = LoggingConfig()
        assert cfg.level == "INFO"
        assert cfg.max_size_mb == 100


class TestMonitoringConfig:
    def test_defaults(self) -> None:
        cfg = MonitoringConfig()
        assert not cfg.enabled
        assert cfg.prometheus_port == 8000


class TestTitanConfig:
    def test_defaults(self) -> None:
        cfg = TitanConfig()
        assert cfg.profile == "development"
        assert isinstance(cfg.app, AppConfig)
        assert isinstance(cfg.broker, BrokerConfig)
        assert isinstance(cfg.runtime, RuntimeConfig)
        assert isinstance(cfg.risk, RiskConfig)
        assert isinstance(cfg.execution, ExecutionConfig)
        assert isinstance(cfg.logging, LoggingConfig)
        assert isinstance(cfg.monitoring, MonitoringConfig)
        assert cfg.custom == {}

    def test_frozen(self) -> None:
        cfg = TitanConfig()
        with pytest.raises(AttributeError):
            cfg.profile = "production"  # type: ignore[misc]


class TestConfigurationReport:
    def test_defaults(self) -> None:
        report = ConfigurationReport(
            profile="development",
            sources=("defaults",),
            validation_status="valid",
            warnings=(),
            errors=(),
        )
        assert report.profile == "development"
        assert report.validation_status == "valid"
        assert report.config is None

    def test_with_config(self) -> None:
        tc = TitanConfig()
        report = ConfigurationReport(
            profile="development",
            sources=("file",),
            validation_status="valid",
            warnings=(),
            errors=(),
            config=tc,
        )
        assert report.config is not None
        assert report.config.profile == "development"


# ── Exceptions ──


class TestConfigExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(ConfigLoadError, ConfigError)
        assert issubclass(ConfigValidationError, ConfigError)
        assert issubclass(SecretNotFoundError, ConfigError)
        assert issubclass(ConfigError, Exception)

    def test_messages(self) -> None:
        assert str(ConfigError("fail")) == "fail"
        assert str(SecretNotFoundError("missing")) == "missing"


# ── Profiles ──


class TestProfiles:
    def test_development_defaults(self) -> None:
        d = profile_defaults("development")
        assert d["app"]["log_level"] == "DEBUG"
        assert d["runtime"]["pipeline_interval_seconds"] == 120.0

    def test_testing_defaults(self) -> None:
        d = profile_defaults("testing")
        assert d["broker"]["provider"] == "paper"
        assert d["runtime"]["pipeline_interval_seconds"] == 5.0
        assert d["runtime"]["heartbeat_interval_seconds"] == 2.0

    def test_paper_defaults(self) -> None:
        d = profile_defaults("paper")
        assert d["broker"]["provider"] == "paper"
        assert d["app"]["log_level"] == "INFO"

    def test_backtesting_defaults(self) -> None:
        d = profile_defaults("backtesting")
        assert not d["runtime"]["scheduler_enabled"]
        assert not d["runtime"]["stream_enabled"]

    def test_production_defaults(self) -> None:
        d = profile_defaults("production")
        assert d["runtime"]["stream_enabled"]
        assert d["risk"]["max_drawdown_percent"] == 10.0
        assert d["monitoring"]["enabled"]

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(ValueError):
            profile_defaults("nonexistent")


# ── Secrets ──


class TestInMemorySecretsProvider:
    def test_get_set(self) -> None:
        provider = InMemorySecretsProvider()
        provider.set("api_key", "secret123")
        assert provider.get("api_key") == "secret123"

    def test_get_missing_raises(self) -> None:
        provider = InMemorySecretsProvider()
        with pytest.raises(SecretNotFoundError):
            provider.get("missing_key")

    def test_get_or_none(self) -> None:
        provider = InMemorySecretsProvider({"key": "val"})
        assert provider.get_or_none("key") == "val"
        assert provider.get_or_none("missing") is None

    def test_clear(self) -> None:
        provider = InMemorySecretsProvider({"a": "1"})
        provider.clear()
        assert provider.get_or_none("a") is None


class TestEnvironmentSecretsProvider:
    def test_get_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TITAN_SECRET_API_KEY", "env-secret")
        provider = EnvironmentSecretsProvider(prefix="TITAN_SECRET")
        assert provider.get("api_key") == "env-secret"

    def test_get_missing_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TITAN_SECRET_MISSING", raising=False)
        provider = EnvironmentSecretsProvider(prefix="TITAN_SECRET")
        with pytest.raises(SecretNotFoundError):
            provider.get("missing")

    def test_get_or_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TITAN_SECRET_KEY", "value")
        provider = EnvironmentSecretsProvider(prefix="TITAN_SECRET")
        assert provider.get_or_none("key") == "value"
        assert provider.get_or_none("nope") is None


class TestEncryptedFileSecretsProvider:
    def test_get_raises(self) -> None:
        provider = EncryptedFileSecretsProvider()
        with pytest.raises(SecretNotFoundError):
            provider.get("anything")

    def test_get_or_none(self) -> None:
        provider = EncryptedFileSecretsProvider()
        assert provider.get_or_none("anything") is None


class TestCompositeSecretsProvider:
    def test_first_wins(self) -> None:
        p1 = InMemorySecretsProvider({"key": "from_p1"})
        p2 = InMemorySecretsProvider({"key": "from_p2"})
        composite = CompositeSecretsProvider([p1, p2])
        assert composite.get("key") == "from_p1"

    def test_fallback(self) -> None:
        p1 = InMemorySecretsProvider()
        p2 = InMemorySecretsProvider({"key": "from_p2"})
        composite = CompositeSecretsProvider([p1, p2])
        assert composite.get("key") == "from_p2"

    def test_all_missing_raises(self) -> None:
        p1 = InMemorySecretsProvider()
        p2 = InMemorySecretsProvider()
        composite = CompositeSecretsProvider([p1, p2])
        with pytest.raises(SecretNotFoundError):
            composite.get("missing")

    def test_get_or_none(self) -> None:
        p1 = InMemorySecretsProvider()
        p2 = InMemorySecretsProvider({"key": "val"})
        composite = CompositeSecretsProvider([p1, p2])
        assert composite.get_or_none("key") == "val"
        assert composite.get_or_none("nope") is None


# ── ConfigManager ──


class TestConfigManagerBasics:
    def test_default_config(self) -> None:
        manager = ConfigManager()
        config = manager.get_config()
        assert config.profile == "development"
        assert config.app.name == "TITAN"

    def test_profile_config_development(self) -> None:
        manager = ConfigManager()
        manager.load_profile("development")
        config = manager.get_config()
        assert config.app.log_level == "DEBUG"  # from profile

    def test_profile_config_production(self) -> None:
        manager = ConfigManager()
        manager.load_profile("production")
        config = manager.get_config()
        assert config.runtime.stream_enabled
        assert config.monitoring.enabled

    def test_profile_config_testing(self) -> None:
        manager = ConfigManager()
        manager.load_profile("testing")
        config = manager.get_config()
        assert config.broker.provider == "paper"
        assert config.runtime.pipeline_interval_seconds == 5.0

    def test_unknown_profile_raises(self) -> None:
        manager = ConfigManager()
        with pytest.raises(ValueError):
            manager.set_profile("nonexistent")

    def test_load_dict(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"app": {"log_level": "DEBUG"}})
        config = manager.get_config()
        assert config.app.log_level == "DEBUG"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TITAN_APP__LOG_LEVEL", "ERROR")
        manager = ConfigManager()
        manager.load_env()
        config = manager.get_config()
        assert config.app.log_level == "ERROR"

    def test_load_env_last_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TITAN_APP__LOG_LEVEL", "CRITICAL")
        manager = ConfigManager()
        manager.load_dict({"app": {"log_level": "WARNING"}})
        manager.load_env()
        config = manager.get_config()
        assert config.app.log_level == "CRITICAL"  # env loaded last wins

    def test_load_twice_does_not_duplicate_source(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"app": {"log_level": "INFO"}}, source="test")
        assert len(manager.sources) == 1
        manager.load_dict({"app": {"log_level": "DEBUG"}}, source="test")
        assert len(manager.sources) == 1  # no duplicate

    def test_generate_report_default(self) -> None:
        manager = ConfigManager()
        report = manager.generate_report()
        assert report.profile == "development"
        assert report.validation_status == "valid"
        assert report.config is not None

    def test_report_with_config(self) -> None:
        manager = ConfigManager()
        manager.load_profile("production")
        report = manager.generate_report()
        assert report.config is not None
        assert report.config.profile == "production"
        assert report.config.runtime.stream_enabled


class TestConfigManagerLoadFile:
    def test_load_json(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"app": {"log_level": "WARNING"}}')
            tmp = f.name
        try:
            manager = ConfigManager()
            manager.load_file(tmp)
            config = manager.get_config()
            assert config.app.log_level == "WARNING"
        finally:
            os.unlink(tmp)

    def test_load_yaml_raises_if_no_pyyaml(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("app:\n  log_level: WARNING\n")
            tmp = f.name
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigLoadError):
                manager.load_file(tmp)
        finally:
            os.unlink(tmp)

    def test_unsupported_format_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("[app]\nlog_level = 'WARNING'\n")
            tmp = f.name
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigLoadError):
                manager.load_file(tmp)
        finally:
            os.unlink(tmp)

    def test_missing_file_raises(self) -> None:
        manager = ConfigManager()
        with pytest.raises(ConfigLoadError):
            manager.load_file("/nonexistent/config.json")


class TestConfigManagerMerge:
    def test_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TITAN_APP__LOG_LEVEL", "CRITICAL")
        manager = ConfigManager()
        manager.load_dict({"app": {"log_level": "WARNING"}})
        manager.load_env()
        config = manager.get_config()
        assert config.app.log_level == "CRITICAL"  # env loaded last wins

    def test_profile_plus_dict(self) -> None:
        manager = ConfigManager()
        manager.load_profile("production")
        manager.load_dict({"risk": {"max_drawdown_percent": 5.0}})
        config = manager.get_config()
        assert config.risk.max_drawdown_percent == Decimal("5.0")  # dict wins
        assert config.runtime.stream_enabled  # from profile


class TestConfigManagerSecrets:
    def test_secret_placeholder_resolved(self) -> None:
        secrets = InMemorySecretsProvider({"broker.api_key": "resolved-key"})
        manager = ConfigManager(secrets_provider=secrets)
        manager.load_dict({"broker": {"api_key": "${broker.api_key}"}})
        config = manager.get_config()
        assert config.broker.api_key == "resolved-key"

    def test_secret_placeholder_no_provider_raises(self) -> None:
        secrets = InMemorySecretsProvider()
        manager = ConfigManager(secrets_provider=secrets)
        manager.load_dict({"broker": {"api_key": "${missing.secret}"}})
        with pytest.raises(SecretNotFoundError):
            manager.get_config()

    def test_secrets_provider_access(self) -> None:
        secrets = InMemorySecretsProvider({"test": "value"})
        manager = ConfigManager(secrets_provider=secrets)
        assert manager.secrets().get("test") == "value"


class TestConfigManagerValidation:
    def test_invalid_profile_has_errors(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"profile": "unknown_profile"})
        report = manager.generate_report()
        assert len(report.errors) >= 1

    def test_invalid_broker_timeout(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"broker": {"connection_timeout_seconds": -5}})
        with pytest.raises(ConfigValidationError):
            manager.get_config()

    def test_invalid_port_range(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"monitoring": {"prometheus_port": 99999}})
        with pytest.raises(ConfigValidationError):
            manager.get_config()

    def test_risk_range_validation(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"risk": {"max_drawdown_percent": 150.0}})
        with pytest.raises(ConfigValidationError):
            manager.get_config()

    def test_risk_range_passes(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"risk": {"max_drawdown_percent": 15.0}})
        config = manager.get_config()
        assert config.risk.max_drawdown_percent == 15.0


class TestConfigManagerReload:
    def test_reload(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"app": {"log_level": "WARNING"}})
        assert manager.get_config().app.log_level == "WARNING"
        manager.load_dict({"app": {"log_level": "ERROR"}})
        assert manager.get_config().app.log_level == "ERROR"

    def test_reload_preserves_sources(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"app": {"log_level": "WARNING"}}, source="test")
        sources_before = manager.sources
        manager.load_dict({"app": {"log_level": "ERROR"}}, source="other")
        assert len(manager.sources) == len(sources_before) + 1

    def test_full_reload_empty(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"app": {"log_level": "WARNING"}}, source="tmp")
        config1 = manager.get_config()
        assert config1.app.log_level == "WARNING"
        manager.reload()
        config2 = manager.get_config()
        assert config2.app.log_level == "DEBUG"  # back to profile default (dev)


# ── Secret Ref Pattern ──


class TestSecretRefResolution:
    def test_nested_secret_ref(self) -> None:
        secrets = InMemorySecretsProvider({"nested.key": "deep-value"})
        manager = ConfigManager(secrets_provider=secrets)
        manager.load_dict({"custom": {"secret_ref": "${nested.key}"}})
        config = manager.get_config()
        assert config.custom["secret_ref"] == "deep-value"

    def test_non_secret_string_preserved(self) -> None:
        secrets = InMemorySecretsProvider()
        manager = ConfigManager(secrets_provider=secrets)
        manager.load_dict({"app": {"name": "MyTITAN"}})
        config = manager.get_config()
        assert config.app.name == "MyTITAN"

    def test_empty_secret_ref_ignored(self) -> None:
        secrets = InMemorySecretsProvider()
        manager = ConfigManager(secrets_provider=secrets)
        manager.load_dict({"app": {"name": "${}"}})
        config = manager.get_config()
        assert config.app.name == "${}"


# ── Error state report ──


class TestConfigManagerErrorStates:
    def test_validation_errors_in_report(self) -> None:
        manager = ConfigManager()
        manager.load_dict({"profile": "bogus"})
        report = manager.generate_report()
        assert report.validation_status == "invalid"
        assert len(report.errors) > 0

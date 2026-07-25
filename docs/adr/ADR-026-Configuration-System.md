# ADR-026: Configuration and Environment Management System

**Status:** Accepted (Milestone M6.5.1)

**Date:** 2026-07-08

**Author:** TITAN Architecture Team

## Context

Before this ADR, TITAN configuration was fragmented across:

1. `titan/core/config.py` — a Pydantic `BaseSettings` class reading `.env`
   via `python-dotenv`.
2. `titan/config/settings.py` — a hand-rolled `Settings` singleton that
   called `os.getenv()` directly and raised `ConfigurationError` on
   missing values.
3. Ad-hoc environment variable reads scattered across broker adapters and
   application code.

This created several problems:

- **No unified configuration source.** Modules could not discover what
  settings were available or where they came from.
- **No validation.** There was no type checking, range enforcement, or
  profile-specific safety limits.
- **No secrets abstraction.** API keys, client IDs, PINs, and TOTP
  secrets were read directly from environment variables with no
  indirection layer, making future vault integration impossible without
  touching every consumer.
- **No profiles.** The same settings were used in development, testing,
  paper trading, backtesting, and production. There was no mechanism to
  override settings per environment.
- **No immutability.** Configuration objects were mutable — any module
  could mutate shared global state at runtime.
- **No dependency injection.** The `Settings` singleton was a global
  import. Testing required monkeypatching environment variables.

## Problem Statement

TITAN needs a centralized configuration framework that:

1. Provides a single source of truth for all application settings.
2. Loads configuration from YAML, JSON, environment variables, and
   built-in defaults.
3. Enforces environment profiles (development, testing, paper trading,
   backtesting, production) with per-profile overrides.
4. Validates all configuration fail-fast: required fields, types, ranges,
   broker settings, runtime settings, risk limits, execution settings.
5. Abstracts secrets behind a provider interface to support env vars,
   encrypted files, and future vault backends (AWS Secrets Manager,
   Azure Key Vault, HashiCorp Vault).
6. Returns immutable, typed configuration dataclasses to all consumers.
7. Supports caching and reload without process restart.
8. Generates a configuration report including profile, sources, warnings,
   errors, and validation status.
9. Maintains zero dependencies on broker SDKs, trading logic, or
   execution logic.
10. Preserves backward compatibility: existing code continues to work
    while migrating to the new system.

## Decision

We introduce `titan/config/` as a self-contained configuration subsystem
with the following architecture.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    ConfigManager                     │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐ │
│  │  Loader  │  │ Validator │  │ SecretsProvider     │ │
│  │ (YAML,   │  │ (types,   │  │ (env, file, vault)  │ │
│  │  JSON,   │  │  ranges,  │  │                     │ │
│  │  env)    │  │  required)│  │ ${placeholder}      │ │
│  └────┬─────┘  └────┬─────┘  └─────────┬───────────┘ │
│       │             │                  │             │
│       └─────────────┴──────────────────┘             │
│                         │                            │
│                    ┌────▼────┐                       │
│                    │ TitanConfig (frozen)             │
│                    └─────────┘                       │
└─────────────────────────────────────────────────────┘
```

### Module Layout

```
titan/config/
    __init__.py    — Public API exports
    models.py      — Frozen dataclasses, enums
    exceptions.py  — Exception hierarchy
    manager.py     — ConfigManager (orchestrator)
    loader.py      — YAML/JSON/env file loaders
    validator.py   — Type and range validation
    profiles.py    — Per-environment default overrides
    secrets.py     — SecretsProvider interface + implementations
```

### Models

All configuration models are frozen dataclasses with `slots=True` and
sensible defaults:

```python
@dataclass(frozen=True, slots=True)
class TitanConfig:
    profile: str = "development"
    app: AppConfig = field(default_factory=AppConfig)
    broker: BrokerConfig = field(default_factory=BrokerConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    custom: dict[str, object] = field(default_factory=dict)
```

Each section is a separate frozen dataclass with type-hinted fields and
safe defaults. This design:

- Prevents runtime mutation of configuration state.
- Enables structural pattern matching.
- Supports `dataclasses.replace()` for creating modified copies in tests.
- Provides clear documentation of all available settings via type
  annotations.

### Source Precedence

Configuration sources are merged in this order (later overrides earlier):

1. **Built-in base defaults** — hardcoded in `manager._base_defaults()`.
2. **Profile defaults** — from `profiles.profile_defaults(profile)`.
3. **User-loaded sources** — YAML files, JSON files, or `load_dict()`.
4. **Environment variables** — `TITAN_APP__LOG_LEVEL=DEBUG` maps to
   `{"app": {"log_level": "DEBUG"}}`.

Environment variables use double-underscore (`__`) as a section separator,
single underscores within segment names are preserved:

```
TITAN_APP__LOG_LEVEL=DEBUG        → {"app": {"log_level": "DEBUG"}}
TITAN_RISK__MAX_DRAWDOWN=20.0     → {"risk": {"max_drawdown": 20.0}}
TITAN_BROKER__API_KEY=secret       → {"broker": {"api_key": "secret"}}
```

### Validation

The `validate()` function returns `(warnings, errors)` tuples:

- **Required fields** — presence checks for critical settings.
- **Type checking** — every non-optional field is validated against its
  expected Python type.
- **Range checking** — percentages restricted to 0-100, ports to 1-65535,
  timeouts positive, etc.
- **Enum membership** — profiles, log levels, and broker providers are
  validated against their respective `StrEnum` classes.
- **Fail-fast** — `get_config()` raises `ConfigValidationError` if any
  errors exist.
- **Graceful degradation** — `generate_report()` returns errors as data
  without raising.

### Secrets Provider Interface

```python
class SecretsProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> str: ...
    @abstractmethod
    def get_or_none(self, key: str) -> str | None: ...
```

Implementations:

| Provider | Backend | Use Case |
|---|---|---|
| `EnvironmentSecretsProvider` | `TITAN_SECRET_*` env vars | Development, simple deployments |
| `InMemorySecretsProvider` | `dict[str, str]` | Testing |
| `EncryptedFileSecretsProvider` | Placeholder (always raises) | Future encrypted file support |
| `CompositeSecretsProvider` | Chain of providers | Fallback patterns |

Secret references use `${KEY_NAME}` syntax in configuration values:

```yaml
broker:
  api_key: "${broker.api_key}"
```

These are resolved at build time, before the config is frozen.

### Profiles

Five built-in profiles with tailored defaults:

| Setting | Development | Testing | Paper | Backtest | Production |
|---|---|---|---|---|---|
| Log Level | DEBUG | DEBUG | INFO | INFO | WARNING |
| Pipeline Interval | 120s | 5s | 60s | 0s | 60s |
| Stream Enabled | No | No | Yes | No | Yes |
| Max Position | 10K | 1M | 50K | 1M | 50K |
| Max Drawdown | 25% | 100% | 15% | 100% | 10% |
| Max Leverage | 1.0 | 5.0 | 1.0 | 1.0 | 0.5 |
| Monitoring | Off | Off | Off | Off | On |

Each profile returns only the overrides — all unspecified values fall
through to base defaults.

### ConfigManager API

```python
class ConfigManager:
    def __init__(self, secrets_provider=None, env_prefix="TITAN"): ...
    def set_profile(self, profile: str) -> None: ...
    def load_file(self, path: str | Path) -> None: ...
    def load_dict(self, data: dict, source: str = "<dict>") -> None: ...
    def load_env(self) -> None: ...
    def reload(self) -> None: ...
    def get_config(self) -> TitanConfig: ...
    def generate_report(self) -> ConfigurationReport: ...
    def secrets(self) -> SecretsProvider: ...
```

### ConfigurationReport

```python
@dataclass(frozen=True, slots=True)
class ConfigurationReport:
    profile: str
    sources: tuple[str, ...]
    validation_status: str  # "valid" | "warnings" | "invalid"
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    config: TitanConfig | None = None
```

## Alternatives Considered

### 1. Pydantic BaseSettings (existing approach)

TITAN already had a `Settings(BaseSettings)` class in `titan/core/config.py`.
This approach was rejected for the config module because:

- Pydantic mixes validation, parsing, and data access in a single class.
- Settings are mutable by default.
- No built-in profile system.
- No built-in secrets abstraction.
- No merge semantics (single `.env` file only).
- Adds a heavy dependency for what is fundamentally key-value loading.

Pydantic `BaseSettings` remains available for backward compatibility but
is no longer the canonical configuration source.

### 2. Dynaconf

We considered Dynaconf for its built-in multi-file, multi-environment
configuration loading.

**Rejected because:**
- Adds a heavy external dependency with its own CLI, Flask/Django
  integrations, and Redis backend.
- The TITAN config module is small (~600 LOC total). Dynaconf's
  feature surface vastly exceeds our needs.
- Dynaconf uses mutable boxed dicts — not frozen dataclasses.
- Custom validation requires Dynaconf's validator syntax rather than
  plain Python.

### 3. JSON Schema Validation

We considered using JSON Schema for validation with a library like
`jsonschema`.

**Rejected because:**
- JSON Schema error messages are verbose and schema files are verbose.
- Validation logic in Python is straightforward (~150 LOC for all
  sections) and co-located with the models it validates.
- Python type annotations already serve as a partial schema.
- JSON Schema adds a runtime dependency for validation that is more
  complex than the validation it replaces.

### 4. Singleton Pattern

We considered making `ConfigManager` a global singleton for convenience.

**Rejected because:**
- Singletons are global mutable state that cannot be replaced in tests.
- The `ConfigManager` is designed for dependency injection — each
  consumer receives its own reference.
- A module-level `get_config_manager()` factory is easy to add later
  if convenience is needed, without committing to a singleton today.
- Thread safety is easier to guarantee with instance-level isolation.

### 5. Configuration as Code (Python files)

We considered loading `config.py` files as configuration sources.

**Deferred for future consideration.** Python config files offer
maximum expressiveness but:
- Reduce the ability to audit configuration changes in non-technical
  reviews.
- Make it harder to implement a GUI or web-based config editor.
- Mix code execution with data — a security concern for untrusted
  config files.
- Can be added later as a `load_module()` method without breaking
  the existing API.

## Consequences

### Positive

1. **Single source of truth.** Every TITAN module now reads
   configuration through `ConfigManager.get_config()`. No more
   `os.getenv()` calls scattered across the codebase.

2. **Fail-fast validation.** Invalid configuration is caught at
   startup with clear error messages. No more runtime surprises from
   missing or malformed settings.

3. **Profile isolation.** Development, testing, paper trading,
   backtesting, and production each have tailored defaults. Human
   error from running dev settings in production is structurally
   prevented.

4. **Secrets abstraction.** The `SecretsProvider` interface decouples
   secret storage from secret consumption. Switching from env vars
   to Vault is a one-line change in the `ConfigManager` constructor.

5. **Immutable configuration.** All `TitanConfig` dataclasses are
   frozen. Consumers cannot accidentally (or intentionally) modify
   shared configuration state.

6. **Dependency injection.** `ConfigManager` and `SecretsProvider` are
   injected, not imported as singletons. Testing with custom config
   requires zero monkeypatching.

7. **Report-driven debugging.** `generate_report()` provides a complete
   snapshot of configuration state, sources, warnings, and errors.
   This is machine-readable for automated diagnostics and
   human-readable for operator troubleshooting.

8. **No broker or trading dependencies.** The config module imports
   zero broker SDKs, zero trading logic, zero execution logic. It is
   a pure configuration framework.

9. **Backward compatibility.** The legacy `Settings` class and
   `titan/core/config.py` continue to work. Consumers can migrate
   to the new system incrementally.

### Negative

1. **Migration effort.** Existing code that reads environment variables
   or uses the old `Settings` class needs to be updated to use
   `ConfigManager`. This is mechanical but touches every module.

2. **No hot-reload by default.** `reload()` is available but must be
   called explicitly. Automatic file watching for hot reload is not
   implemented. This is deferred as a future enhancement.

3. **No encryption for secrets at rest.** The `EncryptedFileSecretsProvider`
   is a placeholder. Actual encryption requires a future integration
   with `age`, `sops`, or a vault provider.

4. **No remote configuration.** Configuration must be local (files,
   environment variables). Remote providers (etcd, Consul, AWS AppConfig)
   are not implemented. This is deferred as a future enhancement.

### Neutral

1. **YAML parsing is optional.** PyYAML is not a hard dependency — the
   loader raises a clear error asking the user to install it if they
   try to load a `.yaml` file. JSON and env vars work without YAML.

2. **No schema versioning.** The `TitanConfig` dataclass structure is
   not versioned. Schema changes require code updates. This is
   acceptable because config and code are deployed together.

3. **`custom` dict escape hatch.** `TitanConfig.custom` provides an
   unvalidated dict for experimental or module-specific settings.
   This is intentionally untyped — it is an escape hatch, not a
   first-class API.

## Trade-offs

| Trade-off | Choice | Rationale |
|---|---|---|
| Frozen dataclasses vs Pydantic | Frozen dataclasses | Lighter, immutable by design, no magic |
| Built-in validation vs JSON Schema | Built-in | Simpler, co-located, fewer dependencies |
| Dependency injection vs Singleton | DI | Testability, no global mutable state |
| `SecretsProvider` ABC vs direct os.getenv | ABC | Vault-ready, testable, swappable |
| YAML optional vs mandatory | Optional | Reduce dependency burden |
| `dict` merge vs `TitanConfig` constructor | dict merge | Preserves section isolation, supports any source structure |

## Future Evolution

### Hot Reload / File Watching

The `ConfigManager.reload()` method already re-reads all registered
sources. A file watcher could call `reload()` when config files change
on disk:

```python
manager.watch("config/production.yaml", interval=5.0)
```

This would use `watchdog` or a polling thread. Implementation is
deferred to a future milestone.

### Versioned Configuration

Configuration schemas could be versioned with a `config_version` field:

```python
@dataclass(frozen=True)
class TitanConfigV2:
    version: int = 2
    # ...new fields...
```

Migration logic would upgrade configs between versions. This is
deferred — currently config and code are deployed together, so
schema versioning is unnecessary.

### Feature Flags

A `FeatureFlagConfig` section could gate experimental features:

```python
@dataclass(frozen=True)
class FeatureFlagConfig:
    experimental_strategy: bool = False
    new_risk_model: bool = False
```

Feature flags would be evaluated at build time and compiled into
the frozen config. No runtime flag evaluation needed.

### Multi-Account Profiles

Profile defaults could accept an account parameter:

```python
profile_defaults("production", account="main")
profile_defaults("production", account="satellite")
```

This would return different risk limits for different accounts while
sharing the same profile structure. Implementation requires extending
`profile_defaults()` with an optional account key.

### Multi-Broker Profiles

Similar to multi-account, profile defaults could accept a broker
parameter:

```python
profile_defaults("production", broker="angel_one")
profile_defaults("production", broker="zerodha")
```

This would populate `broker.provider` and broker-specific settings
based on the selected broker.

### Cloud Configuration Providers

A `RemoteConfigProvider` could fetch configuration from:

- AWS AppConfig / AWS Parameter Store
- Azure App Configuration
- Google Cloud Runtime Configurator
- HashiCorp Consul / etcd
- Redis / Zookeeper

This would be a new `ConfigManager` source type alongside
`load_file()` and `load_env()`. The merge semantics and validation
pipeline remain unchanged.

### Encrypted Secrets

A concrete `EncryptedFileSecretsProvider` would decrypt a file using
`age` or `sops`:

```python
secrets = EncryptedFileSecretsProvider("secrets.age")
manager = ConfigManager(secrets_provider=secrets)
```

The provider would need the encryption key from an environment variable
or hardware security module. This is the recommended approach for
production secret storage.

## Migration Path

### Phase 1: Parallel Operation (Milestone M6.5.1)

The `titan/config/` module is introduced alongside existing
configuration mechanisms. No existing code is changed.

- `ConfigManager` is available for new consumers.
- Legacy `Settings` and `BaseSettings` continue to work.
- Documentation directs all new development to use `ConfigManager`.

### Phase 2: Core Migration (Future Milestone)

Core infrastructure modules migrate to `ConfigManager`:

- `titan/core/logger.py` — reads log level from config
- `titan/execution/orchestrator.py` — reads execution settings
- `titan/risk/risk.py` — reads risk limits
- `titan/runtime/engine.py` — reads runtime settings

Each module receives a `ConfigManager` via constructor injection.

### Phase 3: Full Adoption (Future Milestone)

All TITAN modules consume configuration through `ConfigManager` only.

- `titan/config/settings.py` is deprecated.
- `titan/core/config.py` is deprecated.
- Ad-hoc `os.getenv()` calls are removed.

## Relationship to Other ADRs

### ADR-018 (Broker Abstraction)

The config module provides broker settings (`BrokerConfig`) consumed by
broker adapters. The broker layer imports no config classes directly —
settings are passed via constructor injection.

### ADR-021 (Execution Orchestrator)

`ExecutionConfig` provides execution parameters (retries, timeout,
slippage) to the orchestrator. The orchestrator receives its config
via dependency injection.

### ADR-022 (Trade Pipeline)

`RuntimeConfig` provides the pipeline interval and scheduler settings.
The pipeline is configured by the `ConfigManager` at startup.

### ADR-023 (Paper Trading)

The config module provides the paper trading initial cash setting
(`broker.paper_initial_cash`). Paper broker settings are profile-aware.

### ADR-024 (Backtesting Engine)

`RuntimeConfig` provides backtesting-specific settings (pipeline
interval=0, scheduler disabled). The backtesting engine configures
itself from profile defaults.

### ADR-025 (Live Runtime)

`RuntimeConfig` and `MonitoringConfig` provide the runtime engine
settings: heartbeat interval, stream enabled, prometheus port, etc.
The `ConfigManager` is injected into `RuntimeEngine` at construction.

# TITAN Configuration System

## Overview

The Configuration System is the single source of truth for all TITAN settings.

All modules consume configuration through `ConfigManager`. No module reads
environment variables or configuration files directly.

## Architecture

```
Configuration Sources (YAML, JSON, env, defaults)
        │
        ▼
     Loader
        │
        ▼
   Validator
        │
        ▼
ConfigManager (cache, merge, resolve secrets)
        │
        ▼
  Runtime Consumers
```

## Profiles

| Profile       | Purpose                     |
|---------------|-----------------------------|
| `development` | Local development           |
| `testing`     | Automated test suites       |
| `paper`       | Paper trading simulation    |
| `backtesting` | Historical data replay      |
| `production`  | Live trading                 |

Each profile overrides only the values that differ from base defaults.

## Source Precedence

Sources are merged in order (later wins):

1. Built-in base defaults
2. Profile-specific defaults
3. User-loaded configuration (YAML / JSON files or dict)
4. Environment variables (`TITAN_*`)

## Configuration Sections

| Section       | Model             | Key Settings                         |
|---------------|-------------------|--------------------------------------|
| `app`         | `AppConfig`       | name, version, environment, log_level|
| `broker`      | `BrokerConfig`    | provider, api_key, client_id, timeout|
| `runtime`     | `RuntimeConfig`   | interval, heartbeat, stream, schedule|
| `risk`        | `RiskConfig`      | position size, drawdown, leverage    |
| `execution`   | `ExecutionConfig` | retries, timeout, slippage, commish  |
| `logging`     | `LoggingConfig`   | level, file, rotation                |
| `monitoring`  | `MonitoringConfig`| prometheus port, health interval     |
| `custom`      | `dict`            | Arbitrary extension keys              |

## Secrets

Secrets use `${SECRET_KEY}` placeholder syntax in config values:

```yaml
broker:
  api_key: "${broker.api_key}"
```

Providers:

- `EnvironmentSecretsProvider` — reads `TITAN_SECRET_*` env vars
- `InMemorySecretsProvider` — in-memory store for testing
- `EncryptedFileSecretsProvider` — placeholder for future integration
- `CompositeSecretsProvider` — chains multiple providers, first wins

## Usage

```python
from titan.config import ConfigManager

manager = ConfigManager()
manager.load_file("config/production.yaml")
manager.set_profile("production")
config = manager.get_config()

# Access typed config sections
config.broker.provider
config.risk.max_position_size
config.runtime.pipeline_interval_seconds
```

## Configuration Report

```python
report = manager.generate_report()
report.profile           # "production"
report.sources           # ("config/production.yaml", "env:TITAN_*")
report.validation_status  # "valid" | "warnings" | "invalid"
report.warnings          # tuple of warning messages
report.errors            # tuple of error messages
report.config            # TitanConfig or None
```

## Validation

Fail-fast on invalid configuration:

- Required fields presence
- Type checking (str, int, float, bool)
- Numeric range validation (percentages 0-100, ports 1-65535)
- Broker settings validation
- Runtime interval bounds
- Risk limit sanity checks
- Execution parameter validation
- Log level enumeration

## Future Compatibility

- Hot reload support via `manager.reload()`
- Versioned configuration
- Feature flags
- Multi-account profiles
- Multi-broker profiles
- Remote configuration providers (etcd, Consul, AWS AppConfig)

## Quality

- Frozen dataclasses throughout
- Strict typing (MyPy clean)
- Dependency injection for secrets providers
- Immutable runtime configuration
- 69+ unit tests, zero network/broker dependencies

## CLI Integration

The configuration subsystem is exposed through the `titan config` command group:

```bash
titan config show              # Show all configuration sections
titan config show app          # Show only the APP section
titan config show broker       # Show only the BROKER section
titan config show runtime      # Show only the RUNTIME section
titan config show risk         # Show only the RISK section
titan config show execution    # Show only the EXECUTION section
titan config show logging      # Show only the LOGGING section
titan config show monitoring   # Show only the MONITORING section
titan config show --json       # Show all as JSON
titan config show broker --json  # Section as JSON

titan config validate          # Validate current configuration
titan config validate --json   # Validation as JSON

titan config diff              # Diff against development profile
titan config diff -p production  # Diff against production profile
titan config diff --json       # Diff as JSON

titan config export            # Export to config_export.json
titan config export -o cfg.json  # Custom output path
titan config export --format yaml  # Export as YAML

titan config profile           # Show current profile
titan config profile testing   # Set profile to testing
titan config profile --json    # Profile as JSON
```

### Supported Profiles

| Profile | Description |
|---------|-------------|
| `development` | Local development (default) |
| `testing` | Test environment |
| `paper` | Paper trading |
| `backtesting` | Historical backtesting |
| `production` | Live trading |

### Validation

`config validate` checks:
- All configuration sections present
- Correct types for all values
- Valid enum values (broker provider, log level, etc.)
- Numeric ranges respected
- Log directory existence (warning if missing)

## TUI Integration
The Configuration & Deployment Screen (F7) visualizes current configuration profiles.

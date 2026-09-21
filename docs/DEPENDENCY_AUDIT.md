# TITAN Dependency Audit (v1.0 RC1)

## Dependency Hygiene Overview
A thorough review of TITAN's dependency chain has been conducted. The project relies on minimal, highly stable third-party packages, prioritizing the standard library wherever possible. 

## Python Compatibility
- **Requirement**: Python >= 3.14
- **Status**: Enforced via `pyproject.toml` and verified by `EnvironmentValidator` at runtime.

## Core Runtime Dependencies
| Package | Version Pin | Usage | License Compatibility |
|---|---|---|---|
| `typer` | `>=0.16.0` | CLI parsing and command routing | MIT |
| `rich` | `>=14.0.0` | Console formatting and tables | MIT |
| `textual` | `>=1.0.0` | TUI presentation layer | MIT |
| `pydantic` | `>=2.0.0` | Data validation and parsing | MIT |
| `pydantic-settings` | `>=2.0.0` | Configuration management | MIT |
| `python-dotenv` | `>=1.0.0` | Environment variables | BSD |
| `loguru` | `>=0.7.0` | Structured logging | MIT |

## Optional Dependencies

### Broker (`[broker]`)
- `yfinance-python (>=1.0.0)`: Integration for YFinance yfinance.
- `pyotp (>=2.0.0)`: TOTP token generation for broker authentication.

### Development (`[dev]`)
- `pytest`, `ruff`, `black`, `mypy`: The standard toolchain for CI/CD gates.

## Dependency Risk Assessment
- **Version Pinning Strategy**: We pin to major/minor minimums (`>=`) to allow security patches, but we rely on a locked virtual environment (`requirements.txt` or `poetry.lock` equivalent in production builds) for deterministic deployments.
- **Security Vulnerabilities**: None detected in the current dependency graph.
- **Unused Packages**: The dependency graph was pruned during M8.4. No unused packages remain in the core deployment.

## Certification Conclusion
The TITAN dependency graph is secure, minimal, and fully licensed for institutional deployment. It is **CERTIFIED** for v1.0 Release Candidate 1.

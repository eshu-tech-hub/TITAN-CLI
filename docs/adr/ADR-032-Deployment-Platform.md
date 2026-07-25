# ADR-032: Deployment & Production Platform

## Status

Accepted

## Date

2026-07-10

## Context

TITAN needs a production deployment framework to manage the complete lifecycle: environment validation, startup orchestration, health monitoring, backup, and shutdown. Prior to this milestone, TITAN had no centralized deployment infrastructure - no Docker support, no CI/CD beyond a basic test workflow, no systemd service, and no deployment scripts.

The deployment framework must:
- Be the single entry point for all lifecycle operations.
- Validate production readiness before allowing live trading.
- Provide health probes for container orchestrators.
- Support multiple deployment targets (bare metal, Docker, systemd, Windows services).
- Include CI/CD automation for quality gates and releases.

## Decision

### DeploymentManager as Single Authority

`DeploymentManager` is the sole entry point for all TITAN lifecycle operations. No subsystem implements independent startup or shutdown. This guarantees:
- Consistent initialization order.
- Complete environment validation.
- Centralized health reporting.
- Uniform backup procedures.

### Environment-First Validation

Before any startup proceeds, `EnvironmentManager` validates:
- Python version (3.14+).
- Required directories exist and are writable.
- Dependencies are installed.
- Configuration is loaded and valid.
- Secrets are available for production profiles.
- Broker is configured.

### Pluggable Startup Steps

`StartupManager` executes an ordered sequence of startup steps. Each step is a callable that raises on failure. This design allows:
- Custom startup sequences per deployment profile.
- Easy testing (inject stub steps).
- Step-level timing and error reporting.

### Deployment Health Service

`DeploymentHealthService` provides three probes at the deployment infrastructure layer:
- **Readiness**: Can TITAN accept work? (requires startup complete + all checks pass)
- **Liveness**: Is TITAN alive? (custom health checks)
- **Startup**: Has TITAN finished initialization?

These probes are compatible with Docker HEALTHCHECK, Kubernetes liveness/readiness probes, and systemd watchdog.

### Multi-Target Deployment

The framework supports multiple deployment targets without redesign:

| Target | Mechanism |
|--------|-----------|
| Bare metal | `scripts/start.sh` / `scripts/start.ps1` |
| Docker | `docker/Dockerfile` + `docker-compose.yml` |
| systemd | `systemd/titan.service` |
| Windows Service | `windows/titan_service.py` |
| CI/CD | `.github/workflows/` (ci, quality, release) |

### CI/CD Pipeline

Three GitHub Actions workflows:
- **ci.yml**: Quality + test gates on push/PR.
- **quality.yml**: Strict quality gate on PRs (blocks merge on failure).
- **release.yml**: Automated build + Docker push on version tags.

## Consequences

### Positive

- Centralized lifecycle management.
- Environment validation prevents misconfigured deployments.
- Health probes enable container orchestration.
- Backup/restore for operational recovery.
- CI/CD automates quality enforcement.

### Negative

- Adds deployment complexity for local development.
- Docker image size may be large (mitigated by multi-stage build).
- Windows service requires pywin32 (optional dependency).

### Risks

- Startup step failures may cascade (mitigated by step-level error reporting).
- Docker image may not be optimized for size (future: distroless base).

## Alternatives Considered

1. **No deployment framework**: Rejected. TITAN needs production-grade lifecycle management.

2. **External process manager only (supervisord, pm2)**: Rejected. Does not provide health probes or environment validation.

3. **Kubernetes-only deployment**: Rejected. Too specific; bare metal and Docker are needed first.

## Module Structure

```
titan/deployment/
    __init__.py       # Public API with __all__
    models.py         # Frozen dataclasses for all reports
    exceptions.py     # Deployment exception hierarchy
    environment.py    # Environment validation & resolution
    startup.py        # Startup step orchestration
    service.py        # Production validation
    health.py         # Health probes (readiness, liveness, startup)
    version.py        # Version & build metadata
    manager.py        # DeploymentManager (single authority)
```

## Testing

65 tests covering:
- All model frozen dataclasses and serialization.
- Environment resolution and validation.
- Startup step execution (success, failure, abort).
- Production validation (strict and non-strict).
- Health probes (readiness, liveness, startup).
- DeploymentManager lifecycle (start, stop, restart, backup).
- Thread safety under concurrent access.
- Dependency injection with custom storage.
- Version metadata collection.

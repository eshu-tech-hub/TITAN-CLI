# ADR 038: Production Readiness

## Status
Accepted

## Context
Institutional deployments require a holistic readiness score.

## Decision
We generate a `ProductionReadinessReport` analyzing multiple pillars: Architecture, Reliability, Recovery, Configuration, Observability, Documentation, Testing, and Deployment.

## Consequences
Provides operators with an institutional-grade assessment instead of an arbitrary readiness number.

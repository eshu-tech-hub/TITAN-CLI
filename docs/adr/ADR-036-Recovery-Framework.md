# ADR 036: Recovery Framework

## Status
Accepted

## Context
When subsystems fail (e.g. broker disconnects, pipeline stalls), TITAN needs a deterministic escalation path.

## Decision
We maintain the central `RecoveryManager` but formalize `RecoveryLevel` (1 to 4) sequences. `RuntimeSupervisor` does not orchestrate recovery; it delegates to the `RecoveryManager` via `execute(level)`.

## Consequences
Recovery logic stays decoupled from health evaluation.

# ADR 035: Runtime Reliability

## Status
Accepted

## Context
We need a robust supervision strategy for long-running TITAN sessions without introducing threading complexity.

## Decision
We will use a synchronous `RuntimeSupervisor` integrated into the main orchestrator loop (pipeline runner). It uses a `HeartbeatRegistry` and `Watchdog` to evaluate subsystem health and uses `ReliabilityPolicy` to escalate timeouts.

## Consequences
Reduces thread contention and deadlocks, ensuring a predictable shutdown sequence.

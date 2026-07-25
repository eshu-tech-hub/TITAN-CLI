# ADR-021: Execution Orchestrator

**Status:** Accepted (Milestone M5.5)

**Date:** 2026-07-04

**Author:** TITAN Architecture Team

## Context

TITAN's decision pipeline produces `TradeDecision` objects (ADR-016)
that are approved by the Decision Engine and Risk Intelligence Engine
(ADR-015). The Order Management System (ADR-019) manages order lifecycle
and broker routing.

Prior to this ADR:

- There was no central coordinator to receive an approved `TradeDecision`
  and execute it through the pipeline.
- Execution planning (order splitting, TWAP, VWAP) was unscoped.
- Pre-execution validation (broker connectivity, market status, funds)
  was ad-hoc.
- Capital allocation consumed approved sizing inconsistently.
- There was no structured `Evidence` or `Explanation` for the execution
  stage.

## Decision

We introduce `titan/execution/orchestrator.py` and supporting modules:
`planner.py`, `validator.py`, `allocator.py`.

### Architecture

The orchestrator sequences four operations:

1. **ExecutionPlanner** converts `TradeDecision` to `ExecutionPlan`.
2. **ExecutionValidator** checks preconditions (broker, market, funds,
   OMS).
3. **ExecutionAllocator** reads already-approved sizing and produces
   `AllocationInstruction`.
4. Output is passed to `ExecutionEngine` (the OMS) which routes to a
   `Broker`.

The return value is an `OrchestratorReport` with aggregate execution
results.

### Package Structure

```
titan/execution/
    planner.py        # ExecutionPlanner, ExecutionPlan, PlannedOrder
    validator.py      # ExecutionValidator, ValidationResult
    allocator.py      # ExecutionAllocator, AllocationInstruction
    orchestrator.py   # ExecutionOrchestrator, OrchestratorReport,
                      # OrchestratorExplanation
```

### Key Design Decisions

#### Planner strategy pattern
The `plan()` method uses a simple dispatch to strategy-specific methods.
New strategies (TWAP, VWAP, Iceberg, Basket) can be added without
changing the public API. Future implementations raise `NotImplementedError`
— preserving backward compatibility as skeletons.

#### Validator pluggable checks
`market_hours_check`, `trading_enabled_check`, and `instrument_check`
are injected via constructor. This keeps the validator deterministic and
testable without external API calls. Default implementations pass all
checks.

#### Allocator reads approved sizing only
The allocator does **no** position-sizing calculations. It reads
`PositionSizing.maximum_quantity`, `CapitalAllocation.maximum_allocation`,
and `DecisionContext.maximum_contracts` from `RiskAnalysis`, then applies
the most restrictive bound together with `PortfolioSnapshot.available_capital`.
This ensures the allocator is purely a consumer of already-approved risk
parameters.

#### Orchestrator stateless coordination
`ExecutionOrchestrator` is stateless — all state (orders, plans) lives
in the OMS `OrderBook`. This makes the orchestrator safe for concurrent
use and simplifies testing.

#### Evidence category addition
`EvidenceCategory.EXECUTION` was added to `titan/core/evidence/models.py`
to represent execution-stage evidence. The signal is always `NEUTRAL`
(execution outcomes are operational, not directional); outcome severity
is encoded in `score` and `confidence`.

## Consequences

### Positive
- Clear separation of concerns: plan → validate → allocate → execute.
- All pre-execution validation is centralized in one module.
- Capital allocation is deterministic and testable.
- Evidence and Explanation follow the existing institutional pattern.
- Future execution algorithms can be added as planner strategies without
  changing the orchestrator.
- Broker connectivity, funds, and margin checks are encapsulated in the
  validator.

### Negative
- Added abstraction layer increases call depth for the common case
  (simple single-order execution).
- Validator check injections require callers to provide market-hours
  logic or accept default passthrough.

### Mitigations
- The orchestrator is lightweight — `execute()` completes in microseconds
  for the passing case.
- Default validator checks pass everything, so callers can opt in to
  specific checks gradually.

## Compliance

- **No market analysis** — Orchestrator receives only approved decisions.
- **No indicators** — No technical analysis dependencies.
- **No option analytics** — No options pricing or greeks.
- **No risk calculations** — Allocator reads, does not compute, risk.
- **No trade qualification** — Orchestrator executes qualified trades only.
- **No portfolio optimization** — Allocator consumes portfolio state.
- **Frozen dataclasses** — All models use `frozen=True, slots=True`.
- **Dependency injection** — All external dependencies injected.
- **Test coverage** — 47 tests covering all components and error paths.

## References

- ADR-016: Decision Engine
- ADR-015: Risk Intelligence
- ADR-019: Order Management System
- ADR-018: Broker Abstraction
- `titan/execution/orchestrator.py`
- `titan/execution/planner.py`
- `titan/execution/validator.py`
- `titan/execution/allocator.py`
- `tests/test_execution_orchestrator.py`

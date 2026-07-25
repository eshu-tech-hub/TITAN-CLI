# Execution Orchestrator

## Overview

The Execution Orchestrator is the institutional execution layer that receives
an approved `TradeDecision` and coordinates execution through the OMS and Broker
Adapter.

It does **not** decide whether a trade is good — it executes already-approved
trades.

## Architecture

```
TradeDecision  +  PortfolioSnapshot  +  RiskAnalysis
                        │
                        ▼
              ExecutionOrchestrator
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
      Execution    Execution    Execution
      Planner      Validator    Allocator
            │           │           │
            └───────────┼───────────┘
                        │
                        ▼
            Order Management System
                        │
                        ▼
                Broker Adapter
                        │
                        ▼
             OrchestratorReport
```

## Components

### ExecutionPlanner (`titan/execution/planner.py`)

Generates an `ExecutionPlan` from a `TradeDecision`. Supports:

- **Simple** — Single order execution.
- **TWAP** — Time-weighted average price (skeleton, `_plan_twap`).
- **VWAP** — Volume-weighted average price (skeleton, raises `NotImplementedError`).
- **Iceberg** — Large order split into visible portions (skeleton, raises `NotImplementedError`).
- **Basket** — Multi-symbol execution (skeleton, raises `NotImplementedError`).

### ExecutionValidator (`titan/execution/validator.py`)

Validates execution preconditions:

- Broker connected
- Market open (pluggable check)
- Trading enabled (pluggable check)
- Instrument tradable (pluggable check)
- Funds available
- Margin available
- OMS available (has registered brokers)
- Plan has orders

Injectable check callables:
- `market_hours_check(symbol) -> bool`
- `trading_enabled_check(symbol) -> bool`
- `instrument_check(symbol) -> bool`

### ExecutionAllocator (`titan/execution/allocator.py`)

Consumes already-approved sizing from `RiskAnalysis`:

- `PositionSizing.maximum_quantity`
- `CapitalAllocation.maximum_allocation`
- `DecisionContext.maximum_contracts`
- `PortfolioSnapshot.available_capital`

Outputs `AllocationInstruction` with:
- `execution_quantity`
- `execution_price` (price reference)
- `capital_allocated`

### ExecutionOrchestrator (`titan/execution/orchestrator.py`)

Coordinates the full pipeline:

1. **Plan** — Generate `ExecutionPlan` from `TradeDecision`.
2. **Validate** — Run all precondition checks.
3. **Allocate** — Read approved sizing, produce allocation.
4. **Submit** — Convert plan orders to `ExecutionRequest`s, submit via `ExecutionEngine`.
5. **Report** — Collect order results into `OrchestratorReport`.
6. **Evidence** — Generate `Evidence` with `EvidenceCategory.EXECUTION`.
7. **Explanation** — Generate `OrchestratorExplanation` with per-step sections.

## Models

### OrchestratorReport

| Field              | Type                    | Description                     |
|--------------------|-------------------------|---------------------------------|
| `execution_id`     | `str`                   | Unique execution identifier     |
| `orders_submitted` | `int`                   | Number of orders sent to OMS    |
| `orders_accepted`  | `int`                   | Orders accepted by broker       |
| `orders_rejected`  | `int`                   | Orders rejected by broker       |
| `average_price`    | `Decimal \| None`       | Weighted average fill price     |
| `broker_order_ids` | `tuple[str, ...]`       | Broker-assigned order IDs       |
| `timestamp`        | `datetime`              | Report generation time          |
| `errors`           | `tuple[str, ...]`       | Execution errors                 |
| `warnings`         | `tuple[str, ...]`       | Non-fatal warnings               |

### OrchestratorExplanation

| Field              | Type     | Description                    |
|--------------------|----------|--------------------------------|
| `summary`          | `str`    | High-level outcome             |
| `validation`       | `str`    | Validation step details        |
| `planning`         | `str`    | Planning step details          |
| `allocation`       | `str`    | Allocation step details        |
| `submission`       | `str`    | Order submission results       |
| `broker_response`  | `str`    | Broker response details        |

### ExecutionPlan

| Field               | Type                         | Description                   |
|---------------------|------------------------------|-------------------------------|
| `plan_id`           | `str`                        | Unique plan identifier        |
| `trade_decision_id` | `str`                        | Source TradeDecision reference |
| `orders`            | `tuple[PlannedOrder, ...]`   | Planned sub-orders            |
| `strategy`          | `str`                        | Strategy name                 |
| `total_quantity`    | `int`                        | Aggregate quantity            |
| `metadata`          | `Mapping[str, Any]`          | Strategy-specific metadata    |

## Evidence

The orchestrator generates `Evidence` with:

| Attribute    | Value                                    |
|--------------|------------------------------------------|
| `source`     | `"ExecutionOrchestrator"`                |
| `category`   | `EvidenceCategory.EXECUTION`             |
| `signal`     | `EvidenceSignal.NEUTRAL`                 |
| `score`      | `Score(ratio_accepted * 100)`            |
| `confidence` | `Confidence(ratio_accepted)`             |
| `weight`     | `1.0`                                    |
| `reasons`    | Submission and acceptance summary        |
| `metadata`   | Execution ID and order counts            |

## Future Compatibility

The architecture supports without redesign:

- Partial fills (handled by OMS state machine)
- Scaling (multiple plan orders, TWAP slices)
- Retry engine (new component, same interfaces)
- Smart routing (enhanced `OrderRouter`)
- Multi-broker routing (multiple registered brokers)
- Bracket execution (new strategy in planner)
- OCO (new strategy in planner)
- TWAP (implemented skeleton)
- VWAP (implemented skeleton)

## Usage

```python
from titan.execution import (
    ExecutionAllocator,
    ExecutionOrchestrator,
    ExecutionPlanner,
    ExecutionValidator,
)

planner = ExecutionPlanner()
validator = ExecutionValidator(
    market_hours_check=my_market_hours_func,
    trading_enabled_check=my_trading_check,
    instrument_check=my_instrument_check,
)
allocator = ExecutionAllocator()

orchestrator = ExecutionOrchestrator(
    planner=planner,
    validator=validator,
    allocator=allocator,
    oms=execution_engine,
    broker=broker,
)

report = orchestrator.execute(
    decision=trade_decision,
    portfolio=portfolio_snapshot,
    risk=risk_analysis,
    strategy="simple",
    quantity=100,
)

evidence = orchestrator.generate_evidence(report)
explanation = orchestrator.generate_explanation(report, plan, validation, allocation)
```

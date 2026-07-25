# ADR-022: Trade Pipeline Integration Engine

**Status:** Accepted (Milestone M6.1)

**Date:** 2026-07-04

**Author:** TITAN Architecture Team

## Context

TITAN's intelligence engines (market, options, volatility, dealer, news, events)
produce independent analyses. The Evidence Engine (ADR-014) and Fusion Engine
aggregate these into a unified view. Trade Qualification, Risk Intelligence
(ADR-015), Decision Engine (ADR-016), Portfolio Intelligence, and the Execution
Orchestrator (ADR-021) consume these outputs sequentially.

Prior to this ADR:

- There was no central runtime engine that coordinated the complete trade flow
  from market data input to broker execution output.
- Each module had to be invoked manually in the correct order.
- There was no standardised error handling across stages.
- No hooks existed for monitoring, metrics, logging, or dashboard integration.
- No unified report captured stage timings, evidence counts, decisions, and
  execution results in a single structure.

## Decision

We introduce `titan/pipeline/` with the following modules:

- **`pipeline.py`** — `TradePipeline`: central orchestration engine
- **`stages.py`** — `PipelineStage` enum with execution ordering
- **`context.py`** — `PipelineContext`: mutable state accumulator
- **`models.py`** — `PipelineReport`, `StageTiming`, `PipelineStatus`
- **`hooks.py`** — `PipelineHooks`: before/after/error/abort/complete callbacks
- **`exceptions.py`** — hierarchy: `PipelineError` → `PipelineValidationError`,
  `PipelineRecoverableError`, `PipelineFatalError`, `PipelineAbortedError`

### Design Rules

1. **No duplicated logic** — every stage calls existing engines only.
2. **Dependency injection** — all engines are constructor-injected with sensible
   defaults, enabling mocks in tests and alternative implementations.
3. **Optional stages** — stages with missing input data produce neutral results
   and do not block the pipeline.
4. **Fatal vs recoverable** — qualification, risk, and decision failures are
   fatal. Market intelligence, options, volatility, dealer, news, events, fusion,
   portfolio, and execution failures are recoverable.
5. **Evidence flow** — every stage that produces evidence accumulates it in the
   context. The fusion stage collects all evidence and produces a single
   `IntelligenceFusion`.
6. **Stateless core** — `TradePipeline` is stateless; all mutable state lives in
   `PipelineContext`, which is passed through stages and returned as a
   `PipelineReport`.
7. **Passive reporting stages** — OMS and BROKER stages are passive (read-only)
   reporting stages that capture post-execution state without taking action.

### Stage Execution Order

```
PREPARE → MARKET → OPTIONS → VOLATILITY → DEALER → NEWS → EVENTS →
FUSION → QUALIFICATION → RISK → DECISION → PORTFOLIO → EXECUTION →
OMS → BROKER → COMPLETE
```

### Stage-to-Engine Mapping

| Stage | Engine | Method |
|-------|--------|--------|
| MARKET | `MarketStructureAnalyzer` | `analyze(series)` |
| MARKET | `VWAPAnalyzer` | `analyze(series)` |
| MARKET | `VolumeAnalyzer` | `analyze(series)` |
| MARKET | `MarketRegimeAnalyzer` | `analyze(structure, vwap, volume, breadth)` |
| OPTIONS | `OptionChainAnalyzer` | `analyze(snapshot)` |
| OPTIONS | `GreeksAnalyzer` | `analyze(snapshot)` |
| OPTIONS | `LiquidityAnalyzer` | `analyze(snapshot)` |
| VOLATILITY | `VolatilityAnalyzer` | `analyze(snapshot)` |
| DEALER | `DealerPositioningAnalyzer` | `analyze(input)` |
| DEALER | `GammaExposureAnalyzer` | `analyze(input)` |
| DEALER | `CharmExposureAnalyzer` | `analyze(input)` |
| DEALER | `VannaExposureAnalyzer` | `analyze(input)` |
| NEWS | `NewsIntelligenceAnalyzer` | `analyze(articles)` |
| EVENTS | `EventIntelligenceAnalyzer` | `analyze(events)` |
| FUSION | `FusionEngine` | `fuse()` |
| QUALIFICATION | `TradeQualificationEngine` | `qualify(input)` |
| RISK | `RiskEngine` | `analyze(input, profile, capital)` |
| DECISION | `DecisionEngine` | `decide(input)` |
| PORTFOLIO | `PortfolioEngine` | `analyze(decision, risk, portfolio)` |
| EXECUTION | `ExecutionOrchestrator` | `execute(decision, portfolio, risk)` |

### PipelineContext Data Flow

```
PipelineContext
├── identity: pipeline_id, symbol, exchange, start_time
├── market: market_data, market_structure, vwap_analysis, volume_analysis,
│           breadth_analysis, market_regime
├── options: option_chain, greeks, liquidity
├── volatility: volatility
├── dealer: dealer_positioning, gamma_exposure, charm_exposure, vanna_exposure
├── news & events: news, events
├── evidence: evidence_items[] → fusion
├── qualification → risk → decision → portfolio → execution
├── orders, broker_responses
└── runtime: stage_timings, stage_results, stage_errors, aborted, current_stage
```

### PipelineHooks

| Hook | Signature | Typical Use |
|------|-----------|-------------|
| `before_stage` | `(stage, context) -> None` | Logging, metrics start |
| `after_stage` | `(stage, context, result, duration_ms) -> None` | Metrics recording |
| `on_error` | `(stage, context, error) -> None` | Alerting |
| `on_retry` | `(stage, context, error, attempt) -> None` | Retry logging |
| `on_abort` | `(context) -> None` | Cleanup |
| `on_complete` | `(context, report) -> None` | Dashboard update |

### Exception Hierarchy

```
PipelineError
├── PipelineValidationError (also ValueError)
├── PipelineAbortedError
├── PipelineStageError
└── PipelineExecutionError
    ├── PipelineRecoverableError
    ├── PipelineFatalError
    ├── PipelineBrokerError
    └── PipelineTimeoutError
```

## Consequences

### Positive

1. Single entry point for the complete TITAN trade flow — from symbol to report.
2. Standardised error handling with retry support for recoverable failures.
3. Hook-based extensibility for metrics, logging, notifications, dashboards.
4. All engines remain independently testable; pipeline tests use injected mocks.
5. Unified `PipelineReport` captures everything in one structure.
6. Graceful degradation — optional stages are skipped when input data is absent.
7. Future-ready — stateless design supports cloud workers and distributed execution.

### Negative

1. The pipeline constructor has many dependencies (16+ engines) — acceptable for
   an integration layer, managed via sensible defaults.
2. Stage ordering is hardcoded in `PipelineStage.execution_order()` — changes
   require code modification.

## Future Considerations

- Dynamic stage registration via decorators or configuration.
- Parallel stage execution for independent stages (news + events, dealer sub-analyzers).
- Distributed execution with serializable context across workers.
- Scheduler integration via `on_complete` hook for recurring pipelines.

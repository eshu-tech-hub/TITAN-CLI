# ADR-012: Event Intelligence Foundation

## Status

Accepted

## Context

Institutional trading requires awareness of scheduled market events — central bank policies, macroeconomic indicators, and corporate actions — to manage event-driven risk. Previously the platform had no capability to analyse scheduled events or their expected market impact.

Event intelligence was identified as the next milestone (M4.1.1) following the completion of all market intelligence engines (M3.1.1–M3.1.5).

### Requirements

- Analyse supplied event data only — no API calls, no news ingestion, no broker imports
- Support economic events (RBI Policy, FOMC, ECB, BOJ, GDP, CPI, PPI, PMI, NFP, Unemployment, Interest Rate Decision, Holiday)
- Support corporate events (Quarterly Results, Dividend, Bonus, Split, Rights Issue, Buyback, Merger, Acquisition, Guidance, Promoter Activity, Block Deal)
- Classify events by importance (LOW, MEDIUM, HIGH, CRITICAL)
- Classify risk across multiple dimensions (level, gap, volatility, liquidity)
- Provide decision context (avoid new positions, reduce size, expect high volatility, expect gap open, allow intraday only)
- Generate evidence for Evidence Engine and Intelligence Fusion Engine
- Architecture must support News Intelligence, Reuters, Bloomberg, NSE/BSE Notices, economic APIs, and calendar providers without redesign

## Decision

Implement a broker-independent Event Intelligence Engine as a new `titan.events` package with five components:

1. **EconomicCalendarAnalyzer** — classify economic events by type, assign importance via type-based mapping, sort by criticality and timestamp
2. **CorporateEventAnalyzer** — classify corporate actions by type, assign importance via type-based mapping, sort by criticality and timestamp
3. **ImpactAnalyzer** — map highest importance to expected volatility, liquidity, gap risk, affected asset class/sector, and duration
4. **EventRiskAnalyzer** — multi-dimensional risk: overall, gap, volatility, and liquidity. Uses impact thresholds for dimension-level risk
5. **EventIntelligenceAnalyzer** — orchestrator combining all sub-analyzers, generating `DecisionContext`, `Evidence` (category `EVENT`), and `EventExplanation`

### Key Design Decisions

1. **Separate package (`titan.events/`)** — Event intelligence is architecturally distinct from market intelligence (which consumes time-series data). Events are discrete, timestamped occurrences, not continuous series.

2. **Two-tier importance** — Events carry an explicit `importance` field (honoured when set) overridden by type-based default mapping. This lets callers supply pre-classified importance while providing sensible defaults.

3. **Refined importance in impact/risk** — `ImpactAnalyzer` and `EventRiskAnalyzer` do not trust raw `importance` on input events. They re-evaluate via `EconomicCalendarAnalyzer.importance_for()` / `CorporateEventAnalyzer.importance_for()` to ensure consistency.

4. **Impact as float thresholds** — Expected volatility, liquidity, and gap risk are continuous 0–1 floats. `EventRiskAnalyzer` maps them to discrete `EventRisk` levels (LOW/MODERATE/HIGH/EXTREME) using configurable thresholds.

5. **DecisionContext as boolean flags** — The five boolean fields (`avoid_new_positions`, `reduce_position_size`, `expect_high_volatility`, `expect_gap_open`, `allow_intraday_only`) provide clear, non-numerical guidance. They do NOT recommend trades.

6. **EvidenceSignal is NEUTRAL or BEARISH** — Events are inherently risk-aware. The engine does not generate bullish signals; it communicates elevated risk as bearish or neutral context.

7. **Frozen dataclasses with slots** — All models follow the same pattern as existing intelligence engines. `neutral_placeholder()` classmethod on `EventAnalysis` for graceful degradation.

## Alternatives Considered

1. **Merge with market intelligence** — Rejected. Market intelligence consumes continuous time-series (`MarketDataSeries`). Events are discrete occurrences with fundamentally different structure.

2. **Pydantic models** — Rejected. The codebase convention is frozen dataclasses with slots. Pydantic would introduce inconsistency.

3. **Single importance enum** — Rejected. Two enums (`EventImportance`, `EventRisk`) serve different purposes: importance is event-level classification, risk is market-level assessment.

4. **Numeric decision context** — Rejected. Boolean flags are clearer for downstream consumers. Numeric thresholds can be added later without breaking changes.

5. **Embed risk in ImpactAnalyzer** — Rejected. `ImpactAnalyzer` determines expected parameters; `EventRiskAnalyzer` classifies risk. Separation follows the existing pattern of sub-analyzers per concern.

## Consequences

### Positive

- Event intelligence is fully broker-independent — no SDK imports, no HTTP clients
- Clear separation from market intelligence (different input models, different analysis)
- Future news/notice/API integration requires only new sub-analyzers and/or data providers
- Frozen dataclasses ensure immutability — analysis outputs cannot be accidentally modified
- `neutral_placeholder()` provides consistent fallback for missing data
- `DecisionContext` communicates risk without recommending trades

### Negative

- No news ingestion — must be added as separate milestone
- No live data — consumers must supply event data (from calendar providers, APIs, etc.)
- Importance refinement creates a dependency loop: `ImpactAnalyzer` and `EventRiskAnalyzer` import `EconomicCalendarAnalyzer` / `CorporateEventAnalyzer` static methods
- Boolean decision context is coarse — some scenarios may warrant intermediate states

### Neutral

- 77 tests at initial release — covers normal operation and edge cases
- All events must be supplied — the engine does not discover events

## Future Evolution

### Short Term (Next Milestones)

- **News Intelligence** — `NewsEvent` model + `NewsAnalyzer` sub-analyzer
- **Multi-Event Aggregation** — Multiple events within a window can compound risk

### Medium Term

- **NSE/BSE Notices** — `RegulatoryEvent` model + notice analyzer
- **Economic API Adapters** — Official data provider connectors (calendar, consensus)

### Long Term

- **Reuters / Bloomberg Integration** — Feed adapters for major market data vendors
- **Automated Event Discovery** — Event detection from unstructured sources
- **Probabilistic Impact** — Confidence-interval-based impact estimation

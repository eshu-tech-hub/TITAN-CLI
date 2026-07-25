# ADR-010: Breadth Intelligence Engine

## Status

Accepted

## Context

Institutional trading requires understanding whether index-level price action is supported by the broad market. Previously the platform had no capability to evaluate market breadth — the number of advancing versus declining symbols, sector-level participation, or breadth-price divergence.

Breadth intelligence was identified as the next intelligence engine in the M3 roadmap, following Volume Intelligence (M3.1.3).

### Requirements

- Analyse supplied breadth data only — no exchange data fetching
- Consume only `MarketBreadthSnapshot` (broker-independent input model)
- Provide evidence for the Evidence Engine and Intelligence Fusion Engine
- Support downstream Market Structure, VWAP, and Volume integration
- Architecture must support New High/New Low, McClellan, TRIN, Tick Index without redesign

## Decision

Implement a broker-independent Breadth Intelligence Engine with four components:

1. **AdvanceDeclineAnalyzer** — A/D ratio, breadth strength classification
2. **SectorBreadthAnalyzer** — sector leadership, rotation, concentration risk
3. **MarketParticipationAnalyzer** — participation ratio, internal strength/weakness, divergence
4. **BreadthAnalyzer** — orchestrator combining the above, generating evidence and explanation

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| A/D ratio | `advances / declines` | Standard institutional metric; handles zero-decline case with fallback |
| Very strong threshold | A/D ≥ 3.0 | Captures broad-based buying with 3:1 ratio |
| Strong threshold | A/D ≥ 1.5 | Standard 3:2 institutional threshold |
| Weak threshold | A/D ≤ 0.67 | Symmetric inverse of strong |
| Very weak threshold | A/D ≤ 0.33 | Captures broad-based selling |
| Participation healthy | ≥ 80% | Standard threshold for broad market participation |
| Concentration risk | weight ≥ 0.50 | Single-sector dominance flag |
| Evidence category | `MARKET_BREADTH` | New category in `EvidenceCategory` |
| Input model | `MarketBreadthSnapshot` | Broker-independent, extensible with future fields |
| Frozen dataclasses | Yes | Immutability for evidence safety |

### Input Model Design

`MarketBreadthSnapshot` is a standalone dataclass rather than extending `MarketDataSeries` because breadth data has fundamentally different structure (symbol counts rather than per-candle prices). This also prevents coupling between breadth and price-series consumers.

`SectorBreadthSnapshot` is designed to accommodate future fields like `advancing_volume`, `new_highs`, `new_lows` without breaking changes.

## Alternatives Considered

### 1. Extend MarketDataSeries
Rejected. Breadth data is cross-sectional (across symbols) rather than time-series (per candle). The data structures, validation rules, and consumers differ fundamentally.

### 2. Single Analyzer
Rejected. Advance/decline, sector, and participation analyses have different dependencies and confidence models. Separate analyzers keep each independently testable.

### 3. Include McClellan Oscillator
Rejected for M3.1.4. Requires daily A/D data with specific lookback periods (19 and 39 EMA). The architecture supports it as a future sub-analyzer.

### 4. Include TRIN (Arms Index)
Rejected for M3.1.4. Requires advancing/declining volume data not yet available in the input model.

## Consequences

### Positive

- Clear separation of concerns between A/D, sector, and participation analysis
- Each sub-analyzer independently testable
- No duplicated calculations between analyzers
- Evidence and explanation follow established patterns from M3.1.1–M3.1.3
- Neutral placeholder pattern for graceful degradation
- Architecture ready for New High/New Low, McClellan, TRIN, Tick Index
- Sector concentration risk flags single-sector index dominance

### Negative

- Input model requires external population — no automatic data fetching
- Sector analysis limited to supplied sectors — no automatic sector mapping
- Participation quality is heuristic (threshold-based rather than statistical)

### Risks

- Incomplete snapshots (missing sectors, incorrect totals) may produce misleading analysis
- Sector weight data may not be available from all data sources
- Divergence detection is based on participation thresholds rather than statistical z-scores

## Future Evolution

1. **New High / New Low (M3.3.x)** — Add `new_highs`/`new_lows` fields to `MarketBreadthSnapshot`; create `HighLowAnalyzer`
2. **Percent Above MA** — New `MAAnalyzer` using per-symbol MA data
3. **McClellan Oscillator** — New `McClellanAnalyzer` consuming daily A/D data with EMA computation
4. **McClellan Summation Index** — Cumulative extension of McClellan Oscillator
5. **TRIN (Arms Index)** — New `TRINAnalyzer` requiring `advancing_volume`/`declining_volume`
6. **Tick Index** — New `TickAnalyzer` consuming tick-level up/down ticks
7. **Cross-index Breadth** — Extend `MarketBreadthSnapshot` to support multiple indexes

All future extensions use the same `BreadthAnalyzer` orchestrator pattern — add a sub-analyzer, update the orchestrator, extend the `BreadthAnalysis` dataclass.

## References

- M3.1.1: Market Structure Intelligence (ADR-007)
- M3.1.2: VWAP Intelligence (ADR-008)
- M3.1.3: Volume Intelligence (ADR-009)
- `titan/market/intelligence/breadth.py`
- `titan/market/intelligence/advance_decline.py`
- `titan/market/intelligence/sector_breadth.py`
- `titan/market/intelligence/market_participation.py`
- `titan/market/intelligence/models.py` (BreadthBias, BreadthStrength, AdvanceDecline, SectorBreadth, MarketParticipation, BreadthExplanation, BreadthAnalysis, MarketBreadthSnapshot, SectorBreadthSnapshot)

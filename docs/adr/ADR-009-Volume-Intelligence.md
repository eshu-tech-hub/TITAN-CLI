# ADR-009: Volume Intelligence Engine

## Status

Accepted

## Context

Institutional trading requires understanding whether price movements are supported by meaningful volume. The platform previously had no dedicated volume analysis capability.

Volume intelligence was identified as the next intelligence engine in the M3 roadmap, following Market Structure (M3.1.1) and VWAP (M3.1.2).

### Requirements

- Analyse observable volume only — no order flow estimation
- Consume only `MarketDataSeries` (OHLCV candles)
- Provide evidence for the Evidence Engine and Intelligence Fusion Engine
- Support downstream Market Structure and VWAP integration
- Architecture must support Volume Profile, Footprint Charts, CVD without redesign

## Decision

Implement a broker-independent Volume Intelligence Engine with four components:

1. **VolumeTrendAnalyzer** — slope, expansion, contraction
2. **RelativeVolumeAnalyzer** — RVOL ratio, participation level
3. **AccumulationDistributionAnalyzer** — up/down volume ratio, divergence
4. **VolumeAnalyzer** — orchestrator combining the above, generating evidence and explanation

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Expansion threshold | 1.25x | Standard institutional threshold; avoids noise at 1.0–1.2x |
| Contract threshold | 0.75x | Symmetric to expansion |
| RVOL very low | ≤ 0.25 | Captures extreme illiquidity |
| RVOL extreme | ≥ 3.0 | Standard climax threshold |
| Trend lookback | 10 candles | Consistent with VWAP trend lookback |
| A/D lookback | 5 candles | Short enough to be responsive, long enough to filter noise |
| A/D divergence threshold | 1.3x | Requires meaningful volume decline |
| Evidence category | `MARKET_VOLUME` | Separate from `MARKET_STRUCTURE` |
| Frozen dataclasses | Yes | Immutability for evidence safety |

## Alternatives Considered

### 1. On-Balance Volume (OBV)
Rejected. OBV is a cumulative indicator unsuitable for per-candle evidence. It would require stateful tracking and does not align with the evidence-based architecture.

### 2. Volume-Weighted MACD
Rejected. Too complex for the current scope. Would introduce 9+ EMA parameters without clear institutional benefit.

### 3. Single Analyzer
Rejected. The three sub-analyzers have different dependencies (trend needs multi-window, RVOL needs lookback, A/D needs price correlation). Separate analyzers keep each testable in isolation.

### 4. Include Volume Profile
Rejected for M3.1.3. Volume Profile requires tick-level or time-and-sales data not yet available. The architecture supports it as a future sub-analyzer.

## Consequences

### Positive

- Clear separation of concerns between volume trend, RVOL, and accumulation/distribution
- Each sub-analyzer independently testable
- No duplicated calculations between analyzers
- Evidence and explanation follow established patterns from M3.1.1 and M3.1.2
- Neutral placeholder pattern for graceful degradation
- Architecture ready for Volume Profile, Footprint Charts, CVD

### Negative

- Accumulation/distribution detection is heuristic (up/down volume ratio) rather than order-flow based
- RVOL uses simple average rather than exponential or VWAP-based average
- Exhaustion probability is a heuristic combination of three factors

### Risks

- Low float or illiquid instruments may produce misleading RVOL classifications
- Accumulation/distribution detection may produce false signals in choppy markets
- No Volume Profile means no price-level volume context

## Future Evolution

1. **Volume Profile (M3.2.x)** — New `VolumeProfileAnalyzer` consuming tick-level data with TPO-based structure
2. **Footprint Charts** — New `FootprintAnalyzer` consuming bid/ask delta per price level
3. **CVD (Cumulative Volume Delta)** — New `CVDEngine` consuming tick-level trade data
4. **Iceberg Detection** — Heuristic in `AccumulationDistributionAnalyzer` detecting repeated volume at a price level
5. **Absorption** — New `AbsorptionAnalyzer` detecting large-volume absorption at support/resistance

All future extensions use the same `VolumeAnalyzer` orchestrator pattern — add a sub-analyzer, update the orchestrator, extend the `VolumeAnalysis` dataclass.

## References

- M3.1.1: Market Structure Intelligence (ADR-007)
- M3.1.2: VWAP Intelligence (ADR-008)
- `titan/market/intelligence/volume.py`
- `titan/market/intelligence/volume_trend.py`
- `titan/market/intelligence/relative_volume.py`
- `titan/market/intelligence/accumulation_distribution.py`
- `titan/market/intelligence/models.py` (VolumeBias, ParticipationLevel, VolumeTrend, RelativeVolume, AccumulationDistribution, VolumeExplanation, VolumeAnalysis)

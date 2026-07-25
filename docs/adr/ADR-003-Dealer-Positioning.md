# ADR-003: Dealer Positioning Intelligence Engine

**Status:** Accepted (Milestone M2.2.5)

**Date:** 2026-07-02

**Author:** TITAN Architecture Team

## Context

The TITAN platform now has five independent option analytics intelligence
engines:

1. **OptionChainAnalyzer** (M1) — combined option-chain intelligence.
2. **GreeksAnalyzer** (M1) — combined Greeks intelligence.
3. **LiquidityAnalyzer** (M2.2.1) — combined liquidity intelligence.
4. **SurfaceIntelligenceAnalyzer** (M2.2.4) — combined volatility
   surface intelligence (wrapping Volatility, Smile, Skew, Term
   Structure).

Each produces isolated analysis with an `Evidence` object. There is no
mechanism to:

- Estimate dealer gamma positioning from aggregated analytics.
- Infer dealer directional bias from surface and chain signals.
- Assess likely dealer hedging pressure.
- Produce a unified institutional view of dealer positioning.

Traders must manually cross-reference four separate analysis outputs
to form a dealer positioning view. This is impractical for real-time
trading decisions.

### Constraints

- Must not duplicate calculations already performed by existing
  analyzers.
- Must not modify any existing analyzer.
- Must not introduce broker dependencies or API calls.
- Must not use raw option chain data — only pre-analyzed models.
- Must not estimate order flow.
- Must not make market-making assumptions beyond configurable
  heuristics.
- Must not depend on numpy, scipy, or Black-Scholes.
- Must produce Evidence compatible with the Intelligence Fusion Engine.
- Must support future dealer analytics (Gamma Exposure, Zero Gamma,
  Vanna, Charm, Dealer Hedging, Intraday Position Changes) without
  redesign.

## Decision

Build a three-class Dealer Positioning Intelligence Engine with one
orchestrator and two sub-analyzers:

### 1. DealerInventoryAnalyzer

Estimates whether dealers are net long gamma, net short gamma, or
neutral.

**Decision:** Inventory estimation uses three signal sources:

1. **Greeks (net_gamma):** Direct gamma exposure. Positive values
   suggest long gamma, negative values suggest short gamma. Scaled by
   configurable thresholds.
2. **Surface intelligence:** Smile and skew signals. Rich surface
   conditions (strong smile/convexity, steep skew) suggest dealers have
   written premium → short gamma. Bearish/compressed surface suggests
   dealers may be long gamma.
3. **Option-chain OI imbalance:** Concentration at OTM strikes
   suggests dealer short-premium positioning.

Signal weighting is additive with fixed caps at ±100. Scores above +20
classify as LONG_GAMMA, below -20 classify as SHORT_GAMMA, and between
them as NEUTRAL.

### 2. DealerBiasAnalyzer

Estimates the directional bias implied by dealer positioning.

**Decision:** Bias estimation uses three signal sources:

1. **Surface intelligence (Skew, Smile, Term Structure):** Skew
   direction is the primary source (40pt weight), smile regime supports
   (25pt), term structure provides context (15pt). Surface component
   signals are averaged.
2. **Option-chain bullish/bearish scores:** Net score (bullish -
   bearish) scaled by 0.5, capped at ±50.
3. **Greeks (net_delta, average_delta, overall_bias):** Delta
   converted to score, combined with bias direction, and averaged.

Scores above +20 classify as BULLISH, below -20 as BEARISH, between as
NEUTRAL.

### 3. DealerPositioningAnalyzer (Orchestrator)

The orchestrator:

- Accepts the same four analysis types as the input API (matching
  `VolatilitySurfaceInput` pattern).
- Wraps them in a `DealerPositioningInput` container.
- Runs inventory and bias sub-analyzers.
- Computes **hedging pressure** as a composite of gamma extremity,
  directional conviction, and short-gamma amplification risk.
- Calculates **confidence** as the weighted average of sub-analyzer
  confidences.
- Generates a single `Evidence` object where:
  - Signal maps from dealer_bias level.
  - Score is the confidence-weighted average of inventory and bias
    scores (mapped to 0-100).
  - Confidence is the composite orchestrator confidence.
- Produces a five-section structured `DealerPositioningExplanation`.

**Decision:** The orchestrator uses `object.__setattr__` to attach
`evidence` and `explanation` to the frozen `DealerPositioningAnalysis`,
following the established pattern from SurfaceIntelligenceAnalyzer.

### Alternative: Extend the Intelligence Fusion Engine

Add dealer-positioning heuristics to the existing `EvidenceAggregator`
or create a new fusion-stage analyzer.

**Rejected.** The Fusion Engine is designed for generic evidence
aggregation. Dealer positioning requires domain-specific heuristics
(gamma interpretation, surface-based inventory, directional bias from
compound signals) that do not belong in a general-purpose aggregator.

### Alternative: Single Combined Analyzer

Create one large analyzer that incorporates inventory, bias, and
orchestration logic in a single class.

**Rejected.** Two sub-analyzers provide:
- Focused testing — each is independently testable.
- Dependency injection — sub-analyzers are swappable.
- Clear separation of concerns — inventory and bias use different
  signal sources and have different classification logic.
- Extension path — new dealer analytics (GEX, Vanna) are added as new
  sub-analyzers or new fields, not by modifying existing logic.

### Alternative: Consume Raw Option Chain

Read `OptionChainSnapshot` directly to compute inventory and bias
metrics from raw strike data.

**Rejected.** All existing analyzers already consume the raw chain and
produce analyzed output. Duplicating that analysis in the dealer
positioning engine would violate the "no duplicated logic" constraint
and create maintenance burden. The engine consumes only pre-analyzed
models.

## Consequences

### Positive

1. **No duplicated logic.** All five existing analyzers are unmodified.
   The orchestrator reads their outputs only.
2. **No broker dependencies.** All inputs come from existing in-process
   analysis models.
3. **Clear extension path.** New dealer analytics (Gamma Exposure,
   Vanna, Charm, Dealer Hedging) are added as new sub-analyzers and
   new optional fields on `DealerPositioningInput`. No orchestrator
   logic changes.
4. **Deterministic.** All thresholds are fixed constants. Results are
   reproducible.
5. **Fusion-ready.** Evidence output is directly consumable by the
   Intelligence Fusion Engine.
6. **Graceful degradation.** Missing components produce appropriate
   warnings and reduced confidence rather than crashes.
7. **41 tests** cover enums, data models, sub-analyzers, orchestrator,
   evidence generation, explanation generation, serialization, and edge
   cases.

### Negative

1. **Signal mapping loses granularity.** Surface component signals
   like VERY_BULLISH/VERY_BEARISH are collapsed to BULLISH/BEARISH
   for dealer bias estimation. Mitigation: no existing analyzer
   produces VERY_BULLISH/VERY_BEARISH — they are reserved for the
   aggregator.
2. **Hedging pressure is a heuristic composite.** It combines gamma
   extremity, directional conviction, and a short-gamma boost into a
   single 0-1 metric. Mitigation: the metric is explicitly documented
   as a heuristic, not a probabilistic measure.
3. **DealerPositioningInput duplicates field types.** It is a flat
   container with four optional fields. Mitigation: this is simpler
   than alternatives (variadic args, dict of str→Analysis) and
   provides typed access to each component.
4. **Limited accuracy without raw data.** Estimations based on
   pre-analyzed models are necessarily less precise than those using
   raw option chain data. Mitigation: the engine documents its
   confidence explicitly, and users can cross-reference with raw data
   when available.

## Future Evolution

### New Sub-Analyzer Pattern

To add a new dealer analytics component (e.g., Gamma Exposure):

```python
@dataclass(frozen=True, slots=True)
class GammaExposureAnalysis:
    gex_level: float | None
    gex_rank: float | None
    confidence: float
    evidence: Evidence | None = None

@dataclass(frozen=True, slots=True)
class DealerPositioningInput:
    option_chain: OptionChainAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    liquidity: LiquidityAnalysis | None = None
    surface: SurfaceIntelligenceAnalysis | None = None
    gamma_exposure: GammaExposureAnalysis | None = None  # new field
```

### Planned Enhancements

| Feature | Approach | Timeline |
|---|---|---|
| Gamma Exposure (GEX) | New input model + sub-analyzer | M3.x |
| Zero Gamma / Zero DR | New sub-analyzer reading GEX | M3.x |
| Vanna / Charm | Extend GreeksAnalysis with these fields | M3.x |
| Dealer Hedging Simulation | New sub-analyzer using inventory + bias | M3.x |
| Intraday Position Changes | Time-series aware trend analyzer | M3.x |

### Threshold Tuning

All confidence thresholds (`INVENTORY_CONFIDENCE_LOW`,
`INVENTORY_CONFIDENCE_MODERATE`, `INVENTORY_CONFIDENCE_HIGH`, and
their bias counterparts) are explicit constants that can be tuned
per-deployment without code changes to signal extraction logic.

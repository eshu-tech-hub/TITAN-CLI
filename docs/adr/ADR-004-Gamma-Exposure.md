# ADR-004: Gamma Exposure Intelligence Engine

**Status:** Accepted (Milestone M2.2.6)

**Date:** 2026-07-02

**Author:** TITAN Architecture Team

## Context

The TITAN platform now has the following option analytics intelligence
engines:

1. **OptionChainAnalyzer** (M1) — combined option-chain intelligence.
2. **GreeksAnalyzer** (M1) — combined Greeks intelligence.
3. **LiquidityAnalyzer** (M2.2.1) — combined liquidity intelligence.
4. **SurfaceIntelligenceAnalyzer** (M2.2.4) — combined volatility
   surface intelligence.
5. **DealerPositioningAnalyzer** (M2.2.5) — combined dealer
   positioning intelligence.

Each produces isolated analysis with an `Evidence` object. There is no
mechanism to:

- Estimate aggregate net gamma exposure from per-strike greeks and OI.
- Identify the zero-gamma (gamma flip) level from cumulative gamma.
- Detect gamma walls (call wall / put wall) from gamma-weighted OI
  concentration.
- Assess pinning probability and volatility expansion likelihood from
  gamma conditions.
- Produce a unified institutional view of gamma exposure.

Traders must manually cross-reference Greeks, OI, and dealer positioning
to form a gamma exposure view. This is impractical for real-time
trading decisions.

### Constraints

- Must not duplicate calculations already performed by existing
  analyzers.
- Must not modify any existing analyzer.
- Must not introduce broker dependencies or API calls.
- Must not implement Black-Scholes or any option pricing model.
- Must consume supplied Greeks and Open Interest only.
- Must not present GEX as a standalone trading signal — treat as
  market-regime context.
- Must not depend on numpy, scipy, or any optional numerical library.
- Must produce Evidence compatible with the Intelligence Fusion Engine.
- Must support future extensions (Vanna, Charm, Dealer Hedging, 0DTE
  GEX, Cross-expiry GEX, Historical GEX, Intraday GEX) without
  redesign.

## Decision

Build a three-class Gamma Exposure Intelligence Engine with one
orchestrator and two sub-analyzers:

### 1. ZeroGammaAnalyzer

Estimates the price level where aggregate gamma exposure crosses zero.

**Decision:** The zero-gamma level is found by:

1. Computing the cumulative gamma exposure across strikes in ascending
   strike-price order. Per-strike gamma exposure is the product of
   abs(gamma) × open interest, signed as call_gex - put_gex.
2. Detecting a sign change in the cumulative gamma series.
3. Linearly interpolating between the two straddling strikes to find
   the exact crossing point.

When per-strike gamma data is unavailable, the analyzer returns a
null level with reduced confidence. The gamma regime (positive /
negative) is determined from either the net_gamma sign in
GreeksAnalysis or, as fallback, the dealer_side from
DealerPositioningAnalysis.

### 2. GammaWallsAnalyzer

Identifies strikes with the highest gamma-weighted open interest
concentration for both call and put sides.

**Decision:** Walls are identified by:

1. Computing call gamma exposure (abs(call_gamma) × call_oi) for each
   strike.
2. Computing put gamma exposure (abs(put_gamma) × put_oi) for each
   strike.
3. Ranking strikes separately per side by gamma exposure descending.
4. The top-ranked candidate becomes the wall for that side.
5. Gamma concentration is the ratio of the top candidate's exposure
   to the total of the top 5 candidates.
6. Confidence is computed from concentration, OI magnitude, and
   candidate count.

When gamma values are unavailable, the analyzer falls back to raw OI
ranking, ensuring graceful degradation.

### 3. GammaExposureAnalyzer (Orchestrator)

The orchestrator:

- Accepts the same five analysis types as the input API (matching
  `GammaExposureInput` pattern, extending the `VolatilitySurfaceInput`
  / `DealerPositioningInput` container pattern).
- Wraps them in a `GammaExposureInput` container.
- Computes net gamma exposure from GreeksAnalysis (preferred) or
  per-strike gamma × OI.
- Determines gamma regime from net gamma sign or dealer side fallback.
- Runs the ZeroGammaAnalyzer and GammaWallsAnalyzer sub-analyzers.
- Computes **pinning probability** as a composite of gamma regime
  (long gamma → pinning), zero-gamma proximity, and wall proximity.
- Computes **volatility expansion probability** as a composite of
  gamma regime (short gamma → expansion) and wall weakness.
- Generates a single `Evidence` object where:
  - Signal maps from gamma regime level.
  - Score is regime-based (70 POSITIVE, 30 NEGATIVE, 50 NEUTRAL)
    adjusted for pinning extremity.
  - Confidence is the weighted average of Greeks, dealer positioning,
    zero-gamma, and wall confidences.
- Produces a six-section structured `GammaExposureExplanation`.

**Decision:** The orchestrator uses `object.__setattr__` to attach
`evidence` and `explanation` to the frozen `GammaExposureAnalysis`,
following the established pattern from SurfaceIntelligenceAnalyzer and
DealerPositioningAnalyzer.

### Alternative: Extend DealerPositioningAnalyzer

Add gamma exposure estimation as a new sub-analyzer within the dealer
positioning engine.

**Rejected.** Gamma exposure is a distinct intelligence domain with
different consumers, signal semantics, and extension paths. It
produces two sub-analyzers (zero gamma, walls) that are independently
testable. Embedding in the dealer engine would create a monolithic
module and dilute the separation between "dealer positioning" and
"gamma exposure."

### Alternative: Single Combined Analyzer

Create one large analyzer that incorporates zero gamma, walls,
pinning, and volatility expansion in a single class.

**Rejected.** Two sub-analyzers provide:
- Focused testing — each is independently testable.
- Dependency injection — sub-analyzers are swappable.
- Clear separation of concerns — zero gamma and walls use different
  algorithms and have different data requirements.
- Extension path — new analytics (Vanna, Charm) are added as new
  sub-analyzers.

### Alternative: Require OptionChainSnapshot Always

Design the engine to require raw option-chain data for all estimates.

**Rejected.** The engine degrades gracefully from GreeksAnalysis-only
inputs (regime + confidence) to full per-strike analysis. This matches
the pattern established by DealerPositioningAnalyzer and supports
scenarios where only aggregated Greeks are available.

## Consequences

### Positive

1. **No duplicated logic.** All existing analyzers are unmodified.
   The orchestrator reads their outputs and/or the raw snapshot.
2. **No broker dependencies.** All inputs come from existing in-process
   analysis models and broker-independent snapshots.
3. **No Black-Scholes.** Analysis uses supplied Greeks and OI only.
4. **Clear extension path.** Vanna, Charm, and other exposures are
   added as new sub-analyzers and new optional fields on
   `GammaExposureInput`. No orchestrator logic changes.
5. **Deterministic.** All thresholds are fixed constants. Results are
   reproducible.
6. **Fusion-ready.** Evidence output is directly consumable by the
   Intelligence Fusion Engine.
7. **Graceful degradation.** Missing components produce appropriate
   warnings and reduced confidence rather than crashes.
8. **40+ tests** cover enums, data models, sub-analyzers, orchestrator,
   evidence generation, explanation generation, serialization, and edge
   cases.

### Negative

1. **Zero-gamma interpolation is linear.** The true gamma exposure
   function may be non-linear between strikes. Mitigation: linear
   interpolation is standard practice and matches the discrete nature
   of option strikes.
2. **Gamma exposure assumes all OI is on one side.** The computation
   does not decompose OI into dealer vs. non-dealer positions.
   Mitigation: this is a standard industry simplification; the
   DealerPositioningAnalyzer provides a more nuanced decomposition.
3. **Pinning and expansion probabilities are heuristic.** They are
   composite scores based on regime and proximity, not probabilistic
   forecasts. Mitigation: explicitly documented as heuristic metrics.
4. **No expiry decomposition.** All strikes are aggregated regardless
   of expiry. Mitigation: cross-expiry GEX is a planned future
   enhancement.

## Future Evolution

### New Sub-Analyzer Pattern

To add a new gamma exposure component (e.g., Vanna):

```python
@dataclass(frozen=True, slots=True)
class VannaExposureAnalysis:
    vanna_level: float | None
    confidence: float

@dataclass(frozen=True, slots=True)
class GammaExposureInput:
    dealer_positioning: DealerPositioningAnalysis | None = None
    greeks: GreeksAnalysis | None = None
    option_chain: OptionChainAnalysis | None = None
    surface: SurfaceIntelligenceAnalysis | None = None
    option_chain_snapshot: OptionChainSnapshot | None = None
    vanna_exposure: VannaExposureAnalysis | None = None  # new field
```

### Planned Enhancements

| Feature | Approach | Timeline |
|---|---|---|
| Vanna Exposure | New input model + sub-analyzer | Future |
| Charm Exposure | New input model + sub-analyzer | Future |
| Dealer Hedging Simulation | New sub-analyzer using inventory + GEX | Future |
| 0DTE Gamma | Per-expiry GEX decomposition | Future |
| Cross-expiry GEX | Term-structure-aware GEX aggregation | Future |
| Historical GEX | Time-series-aware GEX snapshots | Future |
| Intraday GEX Evolution | Trend-aware intraday GEX analyzer | Future |

### Threshold Tuning

All confidence thresholds used by sub-analyzers are explicit constants
that can be tuned per-deployment without code changes to signal
extraction logic. Key constants include:

- `NEUTRAL_GAMMA_THRESHOLD` — absolute gamma below which regime is
  neutral (1e-10).
- `MIN_STRIKES_FOR_WALL` — minimum strikes for wall detection (2).
- `MAX_WALL_CANDIDATES` — candidates considered for concentration
  normalisation (5).
- `CONFIDENCE_LOW` / `CONFIDENCE_MODERATE` / `CONFIDENCE_HIGH` —
  confidence thresholds for explanation text.

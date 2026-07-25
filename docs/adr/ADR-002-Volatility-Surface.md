# ADR-002: Volatility Surface Intelligence Engine

**Status:** Accepted (Milestone M2.2.4)

**Date:** 2026-07-02

**Author:** TITAN Architecture Team

## Context

The TITAN platform now has four independent volatility intelligence
analyzers:

1. **VolatilityAnalyzer** (M1) — current IV, HV, IV rank, regime.
2. **SmileAnalyzer** (M2.2.1) — smile curvature, symmetry, regime.
3. **SkewAnalyzer** (M2.2.2) — skew direction, strength, risk reversal.
4. **TermStructureAnalyzer** (M2.2.3) — curve shape, strength, event
   premium.

Each produces isolated analysis. There is no mechanism to:

- Assess overall surface quality.
- Detect cross-module signal conflicts.
- Surface anomalies like extreme smile, extreme skew, or broken term
  structure.
- Derive an aggregate institutional view from all four components.

Users must manually cross-reference four separate analysis objects.
This is impractical for real-time trading decisions.

### Constraints

- Must not duplicate calculations already performed by the four
  analyzers.
- Must not modify any existing analyzer.
- Must not introduce broker dependencies or API calls.
- Must not depend on numpy, scipy, or Black-Scholes.
- Must produce Evidence compatible with the Intelligence Fusion Engine.
- Must support future volatility analytics (GEX, Vanna, Charm, forward
  vol, VRP, surface history) without redesign.

## Decision

Build a fifth analyzer — `SurfaceIntelligenceAnalyzer` — that acts as a
pure orchestrator. It consumes the four existing analysis outputs via a
`VolatilitySurfaceInput` wrapper and delegates to three sub-analyzers:

### 1. SurfaceHealthAnalyzer

Evaluates component availability and confidence. Returns one of
HEALTHY / GOOD / CAUTION / UNHEALTHY / UNKNOWN.

**Decision:** Health classification uses confidence thresholds:
>= 0.7 for HEALTHY, >= 0.5 for GOOD, >= 0.3 for CAUTION. These
thresholds are explicit constants and can be tuned per-deployment.

### 2. SurfaceConsistencyAnalyzer

Compares directional signals across components. Returns CONSISTENT /
PARTIALLY_CONSISTENT / INCONSISTENT / UNKNOWN.

**Decision:** Signal mapping collapses VERY_BULLISH→BULLISH and
VERY_BEARISH→BEARISH. This simplifies the consistency check to three
states (bullish / bearish / neutral) which maps cleanly to the
existing `MarketBias` enum.

### 3. SurfaceAnomalyAnalyzer

Detects six anomaly types by inspecting each component's output.

**Decision:** Each anomaly type maps to a specific, checkable
condition on the existing analysis models. No new data fields or
computations are required.

### Orchestrator Evidence

The orchestrator produces a single `Evidence` object:

- **Signal** is derived by majority voting from component Evidence
  signals (weighted by confidence).
- **Score** is the confidence-weighted average of component scores.
- **Confidence** is the arithmetic mean of component confidences.

**Decision:** Using confidence-weighted averaging for the score gives
more weight to higher-quality components. The confidence mean is a
simple, transparent aggregate.

### Alternative: Extend the Intelligence Fusion Engine

Add cross-module consistency and health assessment to the existing
`EvidenceAggregator` or a new surface-level aggregator.

**Rejected.** The Fusion Engine's `EvidenceAggregator` is designed for
generic evidence aggregation (weighted mean, category grouping). Adding
surface-specific logic (health thresholds, anomaly detection, signal
voting) would violate its general-purpose contract and create coupling
to volatility-specific models.

### Alternative: Add Health/Consistency/Anomaly Methods to Each Analyzer

Add methods like `is_extreme()`, `confidence_level()`, or
`signal_agreement()` to each existing analyzer.

**Rejected.** This would modify four stable, tested modules with
concerns (cross-module comparison) that do not belong to any single
analyzer. The orchestrator pattern keeps each analyzer focused on its
own responsibility.

### Alternative: Single Combined Analyzer

Create one large analyzer that incorporates health, consistency, and
anomaly logic in a single class.

**Rejected.** Three sub-analyzers provide:
- Focused testing — each is independently testable.
- Dependency injection — sub-analyzers are swappable.
- Clear separation of concerns — health, consistency, and anomaly
  detection are independent heuristics.

### Alternative: Direct Evidence Aggregation Without Analysis

Skip health/consistency/anomaly analysis and simply aggregate the four
component Evidence objects.

**Rejected.** This would lose all surface-level insight. The value of
the orchestrator is precisely in detecting conflicts, anomalies, and
degraded health — information no single component can provide.

## Consequences

### Positive

1. **No duplicated logic.** All four existing analyzers are unmodified.
   The orchestrator reads their outputs only.
2. **Clear extension path.** New volatility analytics (GEX, Vanna,
   forward vol) are added as new sub-analyzers and new optional fields
   on `VolatilitySurfaceInput`. No orchestrator logic changes.
3. **Deterministic.** All thresholds are fixed constants. Results are
   reproducible.
4. **Fusion-ready.** Evidence output is directly consumable.
5. **Testable.** 59 tests cover all sub-analyzers, orchestrator,
   evidence generation, and edge cases.
6. **Graceful degradation.** Missing components produce appropriate
   health levels and anomaly warnings rather than crashes.
7. **Aggregate confidence.** The orchestrator computes a single
   institutional confidence that accounts for all component
   confidences.

### Negative

1. **Fourth layer of abstraction.** The call chain is now: input
   model → CalendarAnalyzer → TermStructureAnalyzer →
   SurfaceIntelligenceAnalyzer. Mitigation: each layer adds unique
   value and the types are distinct.
2. **Signal mapping loses granularity.** VERY_BULLISH/VERY_BEARISH are
   collapsed to BULLISH/BEARISH. Mitigation: no existing analyzer
   produces VERY_BULLISH/VERY_BEARISH signals — they are reserved for
   the aggregator.
3. **Confidence-weighted score is not a true probabilistic measure.**
   It is a heuristic. Mitigation: the score is explicitly documented as
   a weighted average of component scores, not a statistical measure.
4. **VolatilitySurfaceInput duplicates field types.** It is a flat
   container with four optional fields. Mitigation: this is simpler
   than alternatives (variadic args, dict of str→Analysis) and
   provides typed access to each component.

## Future Evolution

### New Sub-Analyzer Pattern

To add a new volatility component (e.g., Gamma Exposure):

```python
@dataclass(frozen=True, slots=True)
class GammaExposureAnalysis:
    gex_level: float | None
    gex_rank: float | None
    confidence: float
    evidence: Evidence | None = None

@dataclass(frozen=True, slots=True)
class VolatilitySurfaceInput:
    volatility: VolatilityAnalysis | None = None
    smile: SmileAnalysis | None = None
    skew: SkewAnalysis | None = None
    term_structure: TermStructureAnalysis | None = None
    gamma_exposure: GammaExposureAnalysis | None = None  # new field
```

The surface health, consistency, and anomaly analyzers already iterate
over components generically — new fields are automatically included in
availability and confidence checks.

### Consolidation Path

If the number of volatility analytics grows past 8-10 components,
consider:

- Grouping sub-analyzers by category (smile surface, term surface,
  risk surface).
- Introducing a hierarchical health model (per-group health, then
  overall health).
- Using a registry pattern for component discovery instead of explicit
  fields on `VolatilitySurfaceInput`.

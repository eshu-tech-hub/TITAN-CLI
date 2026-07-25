# ADR-001: Volatility Term Structure Intelligence Engine

**Status:** Accepted (Milestone M2.2.3)

**Date:** 2026-07-02

**Author:** TITAN Architecture Team

## Context

The TITAN platform needs the ability to analyze implied volatility
across multiple option expiries — the volatility term structure. This
capability is required for:

1. **Calendar spread trading** — identifying relative value between
   expiries.
2. **Roll yield estimation** — quantifying the carry from short
   volatility positions.
3. **Event risk detection** — identifying expiries with abnormally
   elevated implied volatility.
4. **Market regime classification** — distinguishing normal
   upward-sloping curves from stressed inverted curves.

The existing codebase had no multi-expiry volatility analysis. The
`VolatilityAnalyzer` operates on a single snapshot. The
`VolatilitySurfaceSnapshot` (M2.2.0) provided the data infrastructure
but no analytics.

### Constraints

- No estimation of implied volatility — consume supplied values only.
- No dependency on any broker SDK (Angel One, SmartAPI, etc.).
- No numpy, scipy, or Black-Scholes.
- Must support weekly, monthly, and quarterly expiries without
  redesign.
- Missing expiries must degrade gracefully, not crash.
- Output must integrate with the existing Evidence Engine and
  Intelligence Fusion Engine (M2.2.2).

## Decision

Implement the term structure intelligence engine as four independent
analyzers with the orchestrator pattern:

### 1. New Input Models (standalone, not coupling to VolatilitySurfaceSnapshot)

Create `TermStructureExpiry` and `TermStructureSnapshot` as lightweight
input models decoupled from the existing `VolatilitySnapshot` and
`VolatilitySurfaceSnapshot`. This avoids:

- Forcing consumers to construct heavy `VolatilitySnapshot` objects.
- Requiring historical volatility, IV rank, or percentile data that
  term structure analysis does not need.

**Decision:** Accept the duplication of expiry-IV representation in
exchange for a clean, minimal input contract.

### 2. CalendarAnalyzer (IV extraction layer)

Sorts expiries, resolves IV (atm_iv > average_iv), computes calendar
spread, curve slope, average slope, max discontinuity, and event
premium.

**Decision:** Event premium is computed as the maximum positive
residual from linear interpolation between neighbours. Only interior
expiries (3+ required) are checked. No curve fitting.

### 3. ContangoAnalyzer (upward-slope classifier)

Takes `CalendarResult`, classifies positive spread into
LOW/MEDIUM/HIGH/EXTREME buckets by fixed thresholds.

**Decision:** Thresholds are based on absolute spread magnitude, not
normalised by time. This is intentional — absolute spread is the
direct input to trade construction and risk management decisions.

### 4. BackwardationAnalyzer (downward-slope classifier)

Takes `CalendarResult`, classifies negative spread into the same
strength buckets. Includes a `stress_indicator` flag at 6% spread.

**Decision:** The stress threshold matches the HIGH strength
threshold. This means any HIGH backwardation automatically triggers
the stress indicator.

### 5. TermStructureAnalyzer (orchestrator)

Runs CalendarAnalyzer, ContangoAnalyzer, BackwardationAnalyzer in
sequence. Produces `TermStructureAnalysis` with shape, strength, bias,
evidence, and explanation.

**Decision:** Evidence and explanation are set after construction via
`object.__setattr__` to preserve the frozen dataclass contract. This
is consistent with how `TermStructureAnalysis.neutral_placeholder()`
works.

### Shape Classification Table

| Spread | Strength | Shape |
|---|---|---|
| Positive | LOW | NORMAL |
| Positive | MEDIUM, HIGH, EXTREME | CONTANGO |
| Negative | LOW | BACKWARDATION |
| Negative | MEDIUM, HIGH, EXTREME | INVERTED |
| Any (abs <= 0.01) | — | FLAT |
| None | — | UNKNOWN |

## Alternatives Considered

### Alternative A: Extend VolatilityAnalyzer

Add term structure analysis directly to the existing
`VolatilityAnalyzer`.

**Rejected.** `VolatilityAnalyzer` operates on a single
`VolatilitySnapshot`. Adding multi-expiry analysis would violate the
single-responsibility principle and couple term structure logic to
single-expiry concerns (historical vol, IV rank, percentile).

### Alternative B: Reuse VolatilitySurfaceSnapshot

Consume `VolatilitySurfaceSnapshot` as the input model for the
orchestrator.

**Rejected.** `VolatilitySurfaceSnapshot` requires full
`VolatilitySnapshot` objects (with historical volatility, IV rank,
IV percentile). These are expensive to construct and include data
that term structure analysis does not consume. The lightweight
`TermStructureSnapshot` is a better match.

A future adapter can translate `VolatilitySurfaceSnapshot` to
`TermStructureSnapshot` if surface integration is needed.

### Alternative C: Parametric Curve Fitting (Nelson-Siegel, cubic spline)

Fit a parametric curve to the available IV points and classify shape
from curve parameters.

**Rejected.** Violates the core constraint of consuming supplied
values only. Curve fitting would introduce model risk, interpolation
artifacts, and dependency on numpy/scipy. The current approach of
classifying from raw spread and strength is transparent and
deterministic.

### Alternative D: Single Analyzer with All Logic

Implement all term structure logic in one class.

**Rejected.** The separation into CalendarAnalyzer, ContangoAnalyzer,
BackwardationAnalyzer, and TermStructureAnalyzer provides:

- Testability — each analyzer has a focused, testable contract.
- Reusability — CalendarResult can be consumed independently.
- Dependency injection — sub-analyzers are swappable.
- Separation of concerns — IV extraction, slope detection, and
  shape classification are independent concerns.

## Consequences

### Positive

1. **Decoupled architecture.** New expiry types (weekly, monthly,
   quarterly) require no changes — they are just `datetime` values.
2. **Graceful degradation.** Missing IV data, single expiries, and
   empty snapshots all produce valid neutral-placeholder results.
3. **Fusion-ready.** Evidence output integrates directly with the
   Intelligence Fusion Engine without any adapter.
4. **Deterministic.** All thresholds are fixed constants. Results are
   reproducible across runs and environments.
5. **Testable.** Each analyzer has a focused input and output. 85
   tests cover normal, edge, and error cases.
6. **Extensible.** New strength levels, shape classifications, or
   curve metrics can be added without changing the public API.

### Negative

1. **Model duplication.** `TermStructureExpiry` duplicates the
   expiry-IV association that exists in `VolatilitySnapshot`.
   Mitigation: the models serve different purposes — one is a
   snapshot of one expiry's full vol profile, the other is a minimal
   data point for term structure analysis.
2. **No time normalization.** Spread thresholds are absolute, not
   normalised by time-to-expiry. A 6% spread over 3 months is
   treated identically to a 6% spread over 12 months. Mitigation:
   curve_slope (spread / num_steps) provides a rough per-step
   normalisation. Future iterations may add time-normalised metrics.
3. **Linear interpolation for event premium.** The simple average of
   neighbours is not a robust curve estimate. It works reliably for
   broadly monotonic curves but may give false positives on
   irregularly spaced expiries. Mitigation: the 2% deviation
   threshold filters out noise, and the result is flagged as a
   warning for human review.

## Future Evolution

### Input Evolution

```python
# Current (lightweight)
snapshot = TermStructureSnapshot(
    underlying="SPY",
    timestamp=now,
    expiries=(
        TermStructureExpiry(expiry=d1, atm_iv=0.20),
        TermStructureExpiry(expiry=d2, atm_iv=0.22),
    ),
)

# Future: surface adapter
surface = VolatilitySurfaceSnapshot(...)
snapshot = TermStructureSnapshot.from_surface(surface)

# Future: per-expiry smile context
expiry = TermStructureExpiry(
    expiry=d1,
    atm_iv=0.20,
    metadata={"smile_shape": "put_skew", "skew": -0.05},
)
```

### Analyzer Evolution

```python
# Current
analyzer = TermStructureAnalyzer()

# Future: additional sub-analyzers
analyzer = TermStructureAnalyzer(
    calendar_analyzer=CalendarAnalyzer(),
    contango_analyzer=ContangoAnalyzer(),
    backwardation_analyzer=BackwardationAnalyzer(),
    forward_vol_analyzer=ForwardVolatilityAnalyzer(),
    regime_analyzer=TermStructureRegimeAnalyzer(),
)
```

### Consolidation Path

If the proliferation of lightweight input models becomes a maintenance
burden, a future refactor could introduce a common `VolatilityPoint`
model:

```python
@dataclass(frozen=True, slots=True)
class VolatilityPoint:
    expiry: datetime
    atm_iv: float | None
    average_iv: float | None
    metadata: Mapping[str, Any]
```

This single model would replace `TermStructureExpiry`, be usable by
`VolatilitySnapshot`, and serve as the common currency for all
volatility analytics.

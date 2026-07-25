# Volatility Term Structure Intelligence Engine

## Purpose

The Volatility Term Structure Intelligence Engine analyzes the implied
volatility curve across multiple option expiries. It classifies the
term structure shape (normal, contango, backwardation, flat, inverted),
quantifies its strength, detects event premium anomalies, and produces
institutional-grade analysis — all without estimating implied volatility
or fitting any pricing model.

This engine is **observation-only**: it classifies and describes the
supplied IV data.

## Institutional Background

The volatility term structure describes how implied volatility varies
with option expiry. It is a critical input for:

- **Calendar spread trading** — identifying rich/cheap expiry pairs.
- **Roll yield estimation** — the carry from rolling short volatility
  positions forward in contango markets.
- **Event risk pricing** — detecting expiries where IV is elevated
  relative to the surrounding curve.
- **Regime detection** — distinguishing normal upward-sloping markets
  from stressed inverted markets.
- **Portfolio construction** — matching strategy tenor to the
  shape of the term structure.

### Normal (Upward-Sloping)

Longer-dated options carry a risk premium for additional time exposure.
A moderate upward slope is the baseline institutional expectation.

### Contango (Steep Upward)

When far-term IV significantly exceeds near-term IV, the curve is in
contango. This environment benefits short-volatility strategies through
positive roll yield.

### Backwardation (Downward-Sloping)

When near-term IV exceeds far-term IV, near-term risk perception is
elevated. Mild backwardation warrants monitoring; strong backwardation
(inversion) signals market stress.

### Flat

Limited term premium — no significant risk premium assigned to any
particular horizon.

### Inverted (Sharp Downward)

Near-term IV substantially exceeds far-term IV, suggesting acute
near-term market stress or event-driven dislocation.

## Architecture

```text
+-----------------------------+
|   TermStructureSnapshot     |  (input)
|-----------------------------|
| underlying / timestamp      |
| expiries[]                  |
|   expiry / atm_iv           |
|   average_iv                |
+-----------+-----------------+
            |
            v
+-----------------------------+
|     CalendarAnalyzer        |
|-----------------------------|
| IV extraction / sorting     |
| Calendar spread             |
| Curve slope                 |
| Event premium detection     |
| Max discontinuity           |
| Confidence / Warnings       |
+-----------+-----------------+
            |
            v
+-----------------------------+     +--------------------------------+
|   ContangoAnalyzer          |     |  BackwardationAnalyzer         |
|-----------------------------|     |--------------------------------|
| Spread > 0 detection        |     | Spread < 0 detection           |
| Strength classification     |     | Strength classification        |
| Interpretation generation   |     | Stress indicator               |
+-----------+-----------------+     +--------------+-----------------+
            |                                     |
            +------------------+------------------+
                               |
                               v
+-----------------------------+
|   TermStructureAnalyzer     |  (orchestrator)
|-----------------------------|
| Shape classification        |
| Strength aggregation        |
| Bias determination          |
| Confidence calculation      |
| Evidence generation         |
| Explanation generation      |
+-----------+-----------------+
            |
            v
+-----------------------------+
|   TermStructureAnalysis     |  (output)
|-----------------------------|
| shape / strength            |
| front_iv / back_iv          |
| curve_slope                 |
| event_premium               |
| overall_bias                |
| confidence                  |
| evidence / explanation      |
+-----------------------------+
```

## Calendar Spreads

The calendar spread is the difference between the back-month (farthest
valid expiry) and front-month (nearest valid expiry) implied volatility:

```
calendar_spread = back_iv - front_iv
```

Additional metrics:

| Metric | Definition | Purpose |
|---|---|---|
| `curve_slope` | `calendar_spread / (num_steps)` | Average IV change per expiry step |
| `average_slope` | Mean of all pairwise IV differences | Robust alternative with outlier resistance |
| `max_discontinuity` | Max absolute IV change between consecutive expiries | Identifies jumps in the curve |

### Curve Slope

The `curve_slope` normalises the calendar spread by the number of
expiry steps rather than calendar days. This avoids introducing an
assumption that IV changes linearly with time.

The `average_slope` computes the mean of all consecutive pairwise
differences, providing a smoother measure when the curve has internal
structure (e.g., a mid-curve hump).

### Max Discontinuity

The maximum absolute IV change between any two consecutive valid
expiries. Values significantly above the average step change suggest
data anomalies, illiquid expiries, or unpriced event risk.

## Contango

Contango is detected when the calendar spread is positive (back IV >
front IV) and exceeds the contango threshold of 1%.

### Strength Classification

| Strength | Spread Range | Label |
|---|---|---|
| LOW | 0.01 (1%) to 0.03 (3%) | Mild contango |
| MEDIUM | 0.03 (3%) to 0.06 (6%) | Moderate contango |
| HIGH | 0.06 (6%) to 0.10 (10%) | Strong contango |
| EXTREME | >= 0.10 (10%) | Extreme contango |

### Interpretation

| Strength | Interpretation |
|---|---|
| LOW | Normal market conditions, standard upward slope |
| MEDIUM | Healthy demand for longer-dated protection |
| HIGH | Elevated uncertainty over longer horizons |
| EXTREME | Structural uncertainty or dislocation in vol market |

## Backwardation

Backwardation is detected when the calendar spread is negative (front
IV > back IV) and the absolute spread exceeds the backwardation
threshold of 1%.

### Strength Classification

| Strength | Abs Spread Range | Label |
|---|---|---|
| LOW | 0.01 (1%) to 0.03 (3%) | Mild backwardation |
| MEDIUM | 0.03 (3%) to 0.06 (6%) | Moderate backwardation |
| HIGH | 0.06 (6%) to 0.10 (10%) | Strong backwardation |
| EXTREME | >= 0.10 (10%) | Extreme backwardation |

### Stress Indicator

When `abs(spread) >= 0.06 (6%)`, the `stress_indicator` flag is set to
`True`. This signals that backwardation has exceeded normal thresholds
and may indicate market stress or dislocation.

## Event Premium

Event premium measures whether any single expiry has an implied
volatility that is abnormally elevated relative to its neighbours on
the curve.

### Detection Algorithm

1. Require at least 3 valid expiries.
2. For each interior expiry, compute the linear interpolation of its
   two neighbours: `interpolated = (iv_prev + iv_next) / 2.0`.
3. Compute the residual: `residual = iv_i - interpolated`.
4. If any residual exceeds the `EVENT_PREMIUM_DEVIATION` threshold
   (2%), the event premium is the maximum positive residual.

### Interpretation

A detected event premium suggests that market participants are pricing
specific event risk (earnings, FOMC, data releases, geopolitics) into
the affected expiry. The affected expiry should be cross-referenced
against known market events.

## Curve Interpretation

Shape classification combines calendar spread direction with contango
and backwardation strength:

| Spread | Strength | Shape |
|---|---|---|
| Positive | LOW | NORMAL |
| Positive | MEDIUM+ | CONTANGO |
| Negative | LOW | BACKWARDATION |
| Negative | MEDIUM+ | INVERTED |
| Any | abs(spread) <= 0.01 | FLAT |
| None | — | UNKNOWN |

### Bias

| Shape | Calendar Bias | Overall Bias |
|---|---|---|
| NORMAL | NEUTRAL | NEUTRAL |
| CONTANGO | NEUTRAL | NEUTRAL |
| BACKWARDATION | BEARISH | BEARISH |
| INVERTED | BEARISH | BEARISH |
| FLAT | NEUTRAL | NEUTRAL |
| UNKNOWN | UNKNOWN | UNKNOWN |

### Evidence Signal

The `Evidence` signal is derived from the overall bias:
- Neutral signal for normal/contango/flat shapes.
- Bearish signal for backwardation/inverted shapes.
- Bullish signal is reserved for future extension.

### Evidence Score

| Shape / Strength | Score |
|---|---|
| CONTANGO / INVERTED / BACKWARDATION with HIGH+ strength | 50 + confidence * 40 |
| CONTANGO / INVERTED / BACKWARDATION with lower strength | 50 + confidence * 25 |
| All other shapes | 50 (baseline) |

## Current Implementation

### Files

| File | Role |
|---|---|
| `titan/options/analytics/models.py` | Enums and dataclasses |
| `titan/options/analytics/calendar.py` | Calendar spread and curve metrics |
| `titan/options/analytics/contango.py` | Contango detection and classification |
| `titan/options/analytics/backwardation.py` | Backwardation detection and stress |
| `titan/options/analytics/term_structure.py` | Orchestrator, evidence, explanation |
| `titan/options/analytics/__init__.py` | Public API exports |

### Constants

| Constant | Value | Used In |
|---|---|---|
| `EVENT_PREMIUM_DEVIATION` | 0.02 (2%) | CalendarAnalyzer |
| `MIN_EXPIRIES_FOR_CURVE` | 2 | CalendarAnalyzer |
| `MIN_EXPIRIES_FOR_EVENT` | 3 | CalendarAnalyzer |
| `MIN_EXPIRIES_RELIABLE` | 3 | CalendarAnalyzer |
| `CONTANGO_THRESHOLD` | 0.01 (1%) | ContangoAnalyzer |
| `CONTANGO_MEDIUM` | 0.03 (3%) | ContangoAnalyzer |
| `CONTANGO_HIGH` | 0.06 (6%) | ContangoAnalyzer |
| `CONTANGO_EXTREME` | 0.10 (10%) | ContangoAnalyzer |
| `BACKWARDATION_THRESHOLD` | 0.01 (1%) | BackwardationAnalyzer |
| `BACKWARDATION_MEDIUM` | 0.03 (3%) | BackwardationAnalyzer |
| `BACKWARDATION_HIGH` | 0.06 (6%) | BackwardationAnalyzer |
| `BACKWARDATION_EXTREME` | 0.10 (10%) | BackwardationAnalyzer |
| `STRESS_THRESHOLD` | 0.06 (6%) | BackwardationAnalyzer |
| `SHAPE_FLAT_THRESHOLD` | 0.01 (1%) | TermStructureAnalyzer |

## API Examples

### Basic Usage

```python
from titan.options.analytics import TermStructureAnalyzer, TermStructureSnapshot, TermStructureExpiry
from datetime import datetime, timedelta

now = datetime(2026, 7, 2, 9, 30)
snapshot = TermStructureSnapshot(
    underlying="SPY",
    timestamp=now,
    expiries=(
        TermStructureExpiry(expiry=now + timedelta(days=30), atm_iv=0.20),
        TermStructureExpiry(expiry=now + timedelta(days=60), atm_iv=0.22),
        TermStructureExpiry(expiry=now + timedelta(days=90), atm_iv=0.24),
        TermStructureExpiry(expiry=now + timedelta(days=180), atm_iv=0.28),
    ),
)

analyzer = TermStructureAnalyzer()
analysis = analyzer.analyze(snapshot)

print(f"Shape: {analysis.shape}")       # Shape: CONTANGO
print(f"Strength: {analysis.strength}") # Strength: HIGH
print(f"Front IV: {analysis.front_iv:.2%}")   # Front IV: 20.00%
print(f"Back IV: {analysis.back_iv:.2%}")     # Back IV: 28.00%
print(f"Bias: {analysis.overall_bias}")        # Bias: NEUTRAL
```

### Detecting Event Premium

```python
snapshot = TermStructureSnapshot(
    underlying="SPY",
    timestamp=now,
    expiries=(
        TermStructureExpiry(expiry=now + timedelta(days=30), atm_iv=0.20),
        TermStructureExpiry(expiry=now + timedelta(days=60), atm_iv=0.35),
        TermStructureExpiry(expiry=now + timedelta(days=90), atm_iv=0.22),
        TermStructureExpiry(expiry=now + timedelta(days=180), atm_iv=0.24),
    ),
)

analysis = TermStructureAnalyzer().analyze(snapshot)
print(f"Event premium: {analysis.event_premium:.2%}")
# Event premium: 14.00%
```

### Using Evidence in Fusion Engine

```python
analysis = TermStructureAnalyzer().analyze(snapshot)
if analysis.evidence is not None:
    print(f"Signal: {analysis.evidence.signal}")
    print(f"Score: {analysis.evidence.score}")
    print(f"Reasons: {analysis.evidence.reasons}")
```

### Structured Explanation

```python
analysis = TermStructureAnalyzer().analyze(snapshot)
if analysis.explanation is not None:
    print(analysis.explanation.curve_shape)
    print(analysis.explanation.institutional_view)
    print(analysis.explanation.risk_assessment)
```

### Dependency Injection

```python
from titan.options.analytics import CalendarAnalyzer, ContangoAnalyzer, BackwardationAnalyzer

custom = TermStructureAnalyzer(
    calendar_analyzer=CalendarAnalyzer(),
    contango_analyzer=ContangoAnalyzer(),
    backwardation_analyzer=BackwardationAnalyzer(),
)
```

### Missing Data

```python
# Empty snapshot — returns neutral placeholder
empty = TermStructureSnapshot(underlying="SPY", timestamp=now, expiries=())
analysis = TermStructureAnalyzer().analyze(empty)
print(analysis.shape)  # Shape: UNKNOWN
print(analysis.confidence)  # 0.0
print(analysis.warnings)  # ("No expiry data provided.",)

# Mixed IV availability — skips missing entries
partial = TermStructureSnapshot(
    underlying="SPY",
    timestamp=now,
    expiries=(
        TermStructureExpiry(expiry=now + timedelta(days=30), atm_iv=0.20),
        TermStructureExpiry(expiry=now + timedelta(days=60)),  # missing IV
        TermStructureExpiry(expiry=now + timedelta(days=90), atm_iv=0.28),
    ),
)
analysis = TermStructureAnalyzer().analyze(partial)
print(analysis.front_iv)  # 0.20
print(analysis.back_iv)   # 0.28
print(analysis.warnings)  # warning about missing IV data
```

## Data Model

### TermStructureAnalysis

| Field | Type | Description |
|---|---|---|
| `shape` | `TermStructureShape` | Curve shape classification |
| `strength` | `TermStructureStrength` | Curve strength classification |
| `front_iv` | `float \| None` | Front-month implied volatility |
| `back_iv` | `float \| None` | Back-month implied volatility |
| `curve_slope` | `float \| None` | Calendar spread / number of steps |
| `event_premium` | `float \| None` | Max residual above interpolated neighbours |
| `calendar_bias` | `MarketBias` | Bias derived from shape |
| `overall_bias` | `MarketBias` | Overall directional interpretation |
| `confidence` | `float` | Aggregate confidence (0.0–1.0) |
| `warnings` | `tuple[str, ...]` | Non-fatal warnings |
| `evidence` | `Evidence \| None` | Evidence for fusion engine |
| `explanation` | `TermStructureExplanation \| None` | Structured explanation |

### TermStructureExplanation

| Field | Type | Description |
|---|---|---|
| `curve_shape` | `str` | Shape and strength description |
| `calendar_analysis` | `str` | Front/back IV, spread, slope, event premium |
| `slope_interpretation` | `str` | Market context of the slope |
| `institutional_view` | `str` | Trading implications |
| `risk_assessment` | `str` | Risk management guidance |
| `future_considerations` | `str` | Event premium, confidence, monitoring |
| `warnings` | `tuple[str, ...]` | Non-fatal warnings |

### Enums

| Enum | Values |
|---|---|
| `TermStructureShape` | NORMAL, CONTANGO, BACKWARDATION, FLAT, INVERTED, UNKNOWN |
| `TermStructureStrength` | LOW, MEDIUM, HIGH, EXTREME, UNKNOWN |

## Missing Data Handling

| Scenario | Behaviour |
|---|---|
| No expiries | Neutral placeholder, warning |
| No valid IV expiries | Neutral placeholder, warning |
| Single valid IV expiry | Insufficient for analysis, warning |
| Two valid IV expiries | Curve metrics available, no event premium, reduced confidence |
| Missing IV on some expiries | Missing entries skipped, warning |
| IV <= 0 | Treated as invalid/missing |
| IV >= 10.0 (1000%) | Treated as invalid/missing |
| `atm_iv` is None | Falls back to `average_iv` |
| Both IVs are None | Expiry skipped |
| Backwardation spread >= 6% | `stress_indicator` set to True |

## Evidence Integration

The `TermStructureAnalyzer` produces `Evidence` consumable by the
Intelligence Fusion Engine:

| Property | Value |
|---|---|
| **Source** | "Volatility Term Structure" |
| **Category** | `EvidenceCategory.OPTION_CHAIN` |
| **Signal** | NEUTRAL (normal/contango/flat), BEARISH (backwardation/inverted) |
| **Score** | 50.0 baseline, +25-40 bonus for stronger shapes |
| **Confidence** | Average of CalendarAnalyzer, ContangoAnalyzer, BackwardationAnalyzer confidences |
| **Weight** | 1.0 |

## Migration Impact

**None.** This is a purely additive change:

- `TermStructureSnapshot` and `TermStructureExpiry` are new standalone
  input models — they do not modify `VolatilitySnapshot` or
  `VolatilitySurfaceSnapshot`.
- `CalendarAnalyzer`, `ContangoAnalyzer`, `BackwardationAnalyzer`,
  and `TermStructureAnalyzer` are new independent modules.
- `TermStructureAnalysis`, `TermStructureExplanation`, and all new
  enums are new optional exports.
- All existing analyzers continue unchanged.
- Evidence Engine and Intelligence Fusion integration unchanged.
- No broker dependencies introduced.

## Quality

- Strict typing throughout (Python 3.14+).
- Frozen dataclasses with slots.
- No broker dependencies, no API calls.
- No numpy, no scipy, no Black-Scholes.
- No SABR, no SVI, no interpolation of missing values.
- No variance/volatility estimation of any kind.
- Ruff clean, Black clean, MyPy clean (0 new errors).
- Full test coverage in `tests/test_term_structure_intelligence.py`
  (85 tests, 15 test classes).
- Forbidden import checks extended to cover all new modules.

## Future Roadmap

### Short Term

| Feature | How |
|---|---|
| Forward volatility | Consume calendar spread to compute forward IV between expiries |
| Variance curve | Compute variance from IV squared for each expiry |
| Volatility of term structure | Track shape changes over successive snapshots |

### Medium Term

| Feature | How |
|---|---|
| Weekly/monthly/quarterly expiry support | Already supported — the model uses arbitrary `datetime` expiries |
| Surface integration | Consume `VolatilitySurfaceSnapshot` as alternative input |
| Per-expiry smile context | Extend `TermStructureExpiry.metadata` with smile analytics |

### Long Term

| Feature | How |
|---|---|
| Curve fitting (parametric) | New model wrapping term structure with Nelson-Siegel or cubic spline |
| Principal component analysis | Decompose curve moves into level/slope/curvature factors |
| Regime clustering | Classify term structure evolution into persistent regimes |

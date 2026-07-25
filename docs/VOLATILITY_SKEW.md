# Volatility Skew Intelligence Engine

## Purpose

The Volatility Skew Intelligence Engine analyzes implied volatility skew
across option strikes and produces institutional-grade skew intelligence.
It integrates with the Evidence Engine and Intelligence Fusion Engine.

This engine is **observation-only**: it classifies and describes the
supplied IV data. No Black-Scholes, no volatility estimation, no delta
estimation.

## Architecture

```text
+-----------------------------+
|   OptionChainSnapshot       |  (existing)
|-----------------------------|
| underlying / expiry         |
| strikes[]                   |
|   strike_price              |
|   call_implied_volatility   |
|   put_implied_volatility    |
|   call_delta                |
|   put_delta                 |
+-----------+-----------------+
            |
            v
+-----------------------------------------+
|           SkewAnalyzer                  |  (NEW)
|-----------------------------------------|
| Orchestrates:                           |
|   +-- RiskReversalAnalyzer              |
|   |   1. 25-Delta RR (from delta)       |
|   |   2. General RR (OTM IV average)    |
|   |   3. Bias determination             |
|   |                                     |
|   +-- ButterflyAnalyzer                 |
|       1. ATM Richness                   |
|       2. Wing Richness                  |
|       3. Relative Curvature             |
|                                         |
| Combined Output:                        |
|   - SkewDirection + SkewStrength        |
|   - Overall bias                        |
|   - Evidence generation                 |
|   - Structured explanation              |
+-------------------+---------------------+
                    |
                    v
+-----------------------------+
|      SkewAnalysis           |  (NEW)
|-----------------------------|
| direction / strength        |
| risk_reversal (sub-result)  |
| butterfly (sub-result)      |
| overall_bias / confidence   |
| evidence / explanation      |
+-----------------------------+
```

## Components

### 1. RiskReversalAnalyzer

Measures the difference between put and call implied volatilities.

**25-Delta Risk Reversal**:
- Finds the OTM put strike with `put_delta` closest to -0.25
- Finds the OTM call strike with `call_delta` closest to +0.25
- Computes RR = put_IV - call_IV at those strikes
- RR > 0 → puts more expensive → bearish
- RR < 0 → calls more expensive → bullish
- Only available when delta values are supplied in the chain

**General Risk Reversal**:
- Averages OTM put IV (strikes below ATM, using `put_implied_volatility`)
- Averages OTM call IV (strikes above ATM, using `call_implied_volatility`)
- General RR = avg_put_iv - avg_call_iv
- Same directional interpretation as 25-delta RR

**Bias Determination**:

| RR Value | Bias |
|---|---|
| > +0.02 | Bearish (puts rich) |
| < -0.02 | Bullish (calls rich) |
| Between | Neutral |

**Strength Classification**:

| |RR Magnitude| |
|---|---|---|
| Low | < 0.01 |
| Medium | 0.01 – 0.03 |
| High | 0.03 – 0.06 |
| Extreme | > 0.06 |

### 2. ButterflyAnalyzer

Examines the curvature and relative pricing of ATM vs wing strikes.

**ATM Richness**: How expensive ATM options are relative to near wings.
- Positive → ATM is rich (expensive vs wings)
- Negative → ATM is cheap (wings are expensive vs ATM)

**Wing Richness**: How expensive far OTM strikes are relative to near OTM.
- Positive → far wings are rich (steep skew)

**Relative Curvature**: Combined measure of overall steepness.

Wing separation uses a median split: all non-ATM strikes are sorted by
distance from ATM, then the closer half becomes "near wings" and the
further half becomes "far wings".

### 3. SkewAnalyzer

Orchestrates RiskReversalAnalyzer and ButterflyAnalyzer to produce the
combined output.

**Direction**:

| Condition | Direction |
|---|---|
| RR bearish with confidence ≥ 0.3 | LEFT (put skew) |
| RR bullish with confidence ≥ 0.3 | RIGHT (call skew) |
| RR neutral with confidence ≥ 0.3 | SYMMETRIC |
| Insufficient data | UNKNOWN |

**Strength**: Derived from risk reversal magnitude (primary) or butterfly
curvature (fallback).

**Overall Bias**: From risk reversal bias when available, otherwise
from skew direction.

## Data Model

### SkewAnalysis

| Field | Type | Description |
|---|---|---|
| `direction` | `SkewDirection` | LEFT, RIGHT, SYMMETRIC, UNKNOWN |
| `strength` | `SkewStrength` | LOW, MEDIUM, HIGH, EXTREME, UNKNOWN |
| `risk_reversal` | `RiskReversalResult \| None` | Sub-analysis from RR analyzer |
| `butterfly` | `ButterflyResult \| None` | Sub-analysis from butterfly analyzer |
| `overall_bias` | `MarketBias` | BULLISH, BEARISH, NEUTRAL, UNKNOWN |
| `confidence` | `float` | Combined confidence (0-1) |
| `evidence` | `Evidence \| None` | Evidence for fusion engine |
| `explanation` | `SkewExplanation \| None` | Structured explanation |

### RiskReversalResult

| Field | Type | Description |
|---|---|---|
| `twenty_five_delta_rr` | `float \| None` | Put IV - Call IV at 25-delta strikes |
| `twenty_five_delta_put_iv` | `float \| None` | Put IV at 25-delta strike |
| `twenty_five_delta_call_iv` | `float \| None` | Call IV at 25-delta strike |
| `twenty_five_delta_put_strike` | `float \| None` | Strike closest to 25-delta put |
| `twenty_five_delta_call_strike` | `float \| None` | Strike closest to 25-delta call |
| `general_rr` | `float \| None` | Avg OTM put IV - avg OTM call IV |
| `avg_otm_put_iv` | `float \| None` | Average OTM put IV |
| `avg_otm_call_iv` | `float \| None` | Average OTM call IV |
| `bias` | `MarketBias` | BULLISH, BEARISH, NEUTRAL, UNKNOWN |
| `confidence` | `float` | Analysis confidence (0-1) |

### ButterflyResult

| Field | Type | Description |
|---|---|---|
| `atm_richness` | `float \| None` | (ATM IV - near wing IV) / near wing IV |
| `wing_richness` | `float \| None` | (far wing IV - near wing IV) / near wing IV |
| `relative_curvature` | `float \| None` | Combined |atm_richness| + |wing_richness| |
| `atm_iv` | `float \| None` | ATM implied volatility |
| `near_wing_iv` | `float \| None` | Average IV of closer wing strikes |
| `far_wing_iv` | `float \| None` | Average IV of further wing strikes |
| `confidence` | `float` | Analysis confidence (0-1) |

### Enums

| Enum | Values |
|---|---|
| `SkewDirection` | LEFT, RIGHT, SYMMETRIC, UNKNOWN |
| `SkewStrength` | LOW, MEDIUM, HIGH, EXTREME, UNKNOWN |

### SkewExplanation

| Field | Type | Description |
|---|---|---|
| `skew_direction` | `str` | Direction and strength assessment |
| `risk_reversal` | `str` | Risk reversal analysis text |
| `butterfly` | `str` | Butterfly analysis text |
| `institutional_interpretation` | `str` | Market context |
| `risk_assessment` | `str` | Risk management guidance |

## Evidence Integration

The `SkewAnalyzer` produces `Evidence` consumable by the Intelligence
Fusion Engine:

- **Source**: "Volatility Skew"
- **Category**: `EvidenceCategory.OPTION_CHAIN`
- **Signal**: Bearish (left skew), Bullish (right skew), Neutral
- **Score**: 50.0 baseline, +25-40 bonus for biased skew with confidence
- **Confidence**: Averaged from sub-analyzers
- **Reasons**: Direction, strength, RR values, butterfly metrics

## Missing Data Handling

| Scenario | Behaviour |
|---|---|
| No strikes | Neutral placeholder, warning |
| No IV data | Unknown direction, zero confidence |
| No deltas | General RR used, 25-delta skipped |
| No underlying_price | Median strike used as ATM proxy |
| Negative IV | Treated as invalid/missing |
| IV > 10.0 (1000%) | Treated as invalid/missing |
| Sparse strikes | Degraded confidence, appropriate warnings |

## Future Compatibility

The architecture supports these extensions without redesign:

- **25-Delta Skew**: Already implemented when deltas are supplied
- **10-Delta Skew**: Add delta target parameter to RiskReversalAnalyzer
- **Surface Skew**: Consume `VolatilitySurfaceSnapshot` with per-expiry skew
- **Expiry Skew**: Extend to term structure analysis
- **Cross-Asset Skew**: Add asset identifier to metadata pipeline

## Migration Impact

**None.** This is a purely additive change:

- `OptionChainSnapshot` and `OptionStrikeSnapshot` are not modified.
- All existing analyzers continue unchanged.
- `SkewAnalyzer`, `RiskReversalAnalyzer`, `ButterflyAnalyzer` are new.
- All models are new additions to `models.py`.

## Quality

- Strict typing throughout (Python 3.14+).
- Frozen dataclasses with slots.
- No broker dependencies, no API calls.
- No numpy, no scipy, no Black-Scholes.
- No delta or IV estimation.
- Ruff clean, Black clean, MyPy clean.
- Full test coverage in `tests/test_skew_intelligence.py`.
- Forbidden import checks extended to all new modules.

# Volatility Smile Intelligence Engine

## Purpose

The Volatility Smile Intelligence Engine analyzes the implied volatility
smile across strikes from a single-expiry option chain snapshot. It
produces institutional-grade smile analysis without estimating implied
volatility or fitting any pricing model.

This engine is **observation-only**: it classifies and describes the
supplied IV data.

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
+-----------+-----------------+
            |
            v
+-----------------------------+
|     SmileAnalyzer           |  (NEW)
|-----------------------------|
| 1. ATM Detection            |
| 2. Curvature Measurement    |
| 3. Symmetry Measurement     |
| 4. Coverage Evaluation      |
| 5. Quality Assessment       |
| 6. Evidence Generation      |
| 7. Explanation Generation   |
+-----------+-----------------+
            |
            v
+-----------------------------+
|     SmileAnalysis           |  (NEW)
|-----------------------------|
| atm_strike / atm_iv         |
| smile_shape / smile_regime  |
| smile_symmetry              |
| curvature / wing IVs        |
| strike_count / completeness |
| confidence / quality        |
| evidence / explanation      |
+-----------------------------+
```

## Analytics

### 1. ATM Implied Volatility

The ATM strike is determined by finding the strike closest to the
supplied `underlying_price`. If `underlying_price` is not available,
the median strike is used as proxy.

ATM IV is the average of the ATM call and put implied volatilities
when both are available. If only one side has IV data, that value
is used directly.

### 2. Smile Curvature

Curvature measures the convexity of the smile — how much wing IVs
exceed ATM IV.

| Shape | Curvature (|wing_avg - atm| / atm) |
|---|---|---|
| Flat | < 5% |
| Mild | 5% – 10% |
| Normal | 10% – 20% |
| Strong | 20% – 35% |
| Extreme | ≥ 35% |

Left wing uses `put_implied_volatility` from strikes below ATM (OTM
puts). Right wing uses `call_implied_volatility` from strikes above
ATM (OTM calls).

### 3. Smile Symmetry

Symmetry compares left-wing average IV to right-wing average IV:

| Classification | Ratio (left / right) |
|---|---|
| Symmetric | 0.9 – 1.1 |
| Left-biased (put skew) | > 1.1 |
| Right-biased (call skew) | < 0.9 |

### 4. Strike Coverage

| Metric | Calculation |
|---|---|
| Strike count | Total strikes in the chain |
| IV completeness | Strikes with at least one valid IV / total strikes |
| Valid IV | > 0 and < 10.0 (1000%) |

### 5. Smile Quality

| Quality | Criteria |
|---|---|
| Reliable | ≥ 5 strikes, ≥ 70% IV completeness, ATM found |
| Partial | ≥ 3 strikes, ≥ 40% IV completeness, ATM found |
| Unreliable | < 3 strikes or < 40% completeness or ATM missing |

### 6. Smile Regime

| Regime | Condition |
|---|---|
| Put Skew | Left-biased (OTM puts > OTM calls) |
| Call Skew | Right-biased (OTM calls > OTM puts) |
| Normal Convexity | Symmetric with curvature |
| Flat | Symmetric without curvature |
| Inverted | Negative curvature (wings below ATM) |
| Unknown | Insufficient data |

### 7. Evidence Generation

The analyzer produces `Evidence` objects compatible with the
Intelligence Fusion Engine:

- **Source**: "Volatility Smile"
- **Category**: `EvidenceCategory.OPTION_CHAIN`
- **Signal**: Bullish (right-biased), Bearish (left-biased), Neutral
- **Score**: 50.0 baseline, +25-40 bonus for biased smiles with confidence
- **Confidence**: Dynamic based on data quality and completeness
- **Reasons**: Shape, symmetry, regime, ATM IV, curvature, quality

### 8. Human Explanation

Structured `SmileExplanation` with sections:

- **Overview**: One-sentence summary of the smile profile
- **Curvature**: Quantitative and qualitative curvature assessment
- **Symmetry**: Balance description
- **Quality**: Data reliability statement
- **Institutional Interpretation**: Market context without speculation

Example:

> "The volatility smile exhibits moderate convexity. OTM put IV
> averages 28.0% and OTM call IV averages 22.0%. The smile is
> left-biased with elevated OTM put implied volatility, suggesting
> stronger demand for downside protection."

## Data Model

### SmileAnalysis

| Field | Type | Description |
|---|---|---|
| `atm_strike` | `float \| None` | Determined ATM strike |
| `atm_iv` | `float \| None` | ATM implied volatility |
| `smile_shape` | `SmileShape` | Curvature classification |
| `smile_symmetry` | `SmileSymmetry` | Left/right balance |
| `smile_regime` | `SmileRegime` | Market regime from smile |
| `smile_quality` | `SmileQuality` | Data reliability |
| `curvature` | `float \| None` | Measured curvature ratio |
| `left_wing_iv` | `float \| None` | Average OTM put IV |
| `right_wing_iv` | `float \| None` | Average OTM call IV |
| `strike_count` | `int` | Total strikes in chain |
| `iv_completeness` | `float` | Fraction of strikes with IV |
| `confidence` | `float` | Analysis confidence (0-1) |
| `evidence` | `Evidence \| None` | Evidence for fusion |
| `explanation` | `SmileExplanation \| None` | Structured explanation |

### SmileExplanation

| Field | Type | Description |
|---|---|---|
| `overview` | `str` | One-sentence smile summary |
| `curvature_assessment` | `str` | Curvature analysis text |
| `symmetry_assessment` | `str` | Symmetry analysis text |
| `quality_assessment` | `str` | Data quality text |
| `institutional_interpretation` | `str` | Market context text |

### Enums

| Enum | Values |
|---|---|
| `SmileShape` | FLAT, MILD, NORMAL, STRONG, EXTREME, UNKNOWN |
| `SmileSymmetry` | SYMMETRIC, LEFT_BIASED, RIGHT_BIASED, UNKNOWN |
| `SmileRegime` | PUT_SKEW, CALL_SKEW, NORMAL_CONVEXITY, FLAT, INVERTED, UNKNOWN |
| `SmileQuality` | RELIABLE, PARTIAL, UNRELIABLE, UNKNOWN |

## Missing Data Handling

| Scenario | Behaviour |
|---|---|
| No strikes | Neutral placeholder, warning |
| No underlying_price | Median strike used as ATM proxy |
| ATM strike has no IV | ATM IV is None, quality degraded |
| Negative IV | Treated as invalid/missing |
| IV > 10.0 | Treated as invalid/missing |
| Only puts available | ATM from put IV, left-biased symmetry |
| Only calls available | ATM from call IV, right-biased symmetry |
| Single strike | ATM found, no curvature possible |
| Sparse IVs | Quality = Partial or Unreliable |

## Evidence Integration

The `SmileAnalyzer` produces `Evidence` consumable by the
Intelligence Fusion Engine:

- Left-biased smile → `BEARISH` signal (downside hedging demand)
- Right-biased smile → `BULLISH` signal (upside speculation)
- Symmetric smile → `NEUTRAL` signal

## Migration Impact

**None.** This is a purely additive change:

- `OptionChainSnapshot` and `OptionStrikeSnapshot` are not modified.
- All existing analyzers continue unchanged.
- `SmileAnalyzer` is a new independent module.
- `SmileAnalysis` and `SmileExplanation` are new optional models.

## Quality

- Strict typing throughout (Python 3.14+).
- Frozen dataclasses with slots.
- No broker dependencies, no API calls.
- No numpy, no scipy, no Black-Scholes.
- No SABR, no SVI, no interpolation.
- Ruff clean, Black clean, MyPy clean.
- Full test coverage in `tests/test_smile_intelligence.py`.
- Forbidden import checks extended to `smile.py`.

## Future Extension Points

| Extension | How |
|---|---|
| Vanna-Volga pricing | Consumes `curvature` and `atm_iv` for risk reversal / butterfly pricing |
| Skew term structure | Consume `VolatilitySurfaceSnapshot` with per-expiry `SmileAnalysis` |
| Volatility of Volatility | Track `SmileRegime` changes over time |
| Wing decay analysis | Extend curvature measurement with per-strike distance weighting |

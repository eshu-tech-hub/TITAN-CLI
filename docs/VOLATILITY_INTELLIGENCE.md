# Volatility Intelligence Engine

## Purpose

The Volatility Intelligence Engine analyzes option volatility data and produces
institutional-grade volatility intelligence. It integrates with the Evidence
Engine and Intelligence Fusion Engine through `Evidence` objects.

This engine does **not** estimate implied volatility. It does **not** implement
Black-Scholes or any option pricing model. It consumes supplied volatility data
only and classifies/analyzes it.

## Architecture

```text
+-------------------------+
|   VolatilitySnapshot    |
|-------------------------|
| implied_volatility      |
| historical_volatility   |
| iv_rank                |
| iv_percentile          |
| volatility_index       |
| implied_volatilities[]  |
| historical_volatilities[]|
+-----------+------------+
            |
            v
+----------------------------+
|     VolatilityAnalyzer     |
|----------------------------|
|  IVAnalyzer                |
|  HVAnalyzer                |
|  IVRankAnalyzer            |
|  IVPercentileAnalyzer      |
|  VolatilityRegimeAnalyzer  |
+----------------------------+
            |
            v
+----------------------------+
|     VolatilityAnalysis     |
|----------------------------|
| current_iv / current_hv    |
| iv_rank / iv_percentile    |
| iv_vs_hv / regime          |
| buying_bias / selling_bias |
| overall_bias / confidence  |
| evidence / explanation     |
+----------------------------+
            |
            v
+----------------------------+
|     Evidence               |
|----------------------------|
| Source: "Volatility"       |
| Category: OPTION_CHAIN     |
| Signal: derived            |
| Score / Confidence         |
| Reasons / Warnings         |
+----------------------------+
```

## Sub-Analyzers

### IVAnalyzer

Classifies implied volatility as High, Low, or Normal based on thresholds:

| Level | Threshold |
|---|---|
| High | IV >= 0.40 (40%) |
| Normal | 0.15 < IV < 0.40 |
| Low | IV <= 0.15 (15%) |

Detects IV trend (Rising, Falling, Flat) when historical IV values are supplied.

### HVAnalyzer

Reports current historical volatility value and detects:

- **Trend**: Rising, Falling, Flat (same ratio-based method as IV)
- **Stability**: Stable (CV <= 0.30) or Unstable (CV > 0.30)

Requires at least 3 observations for stability classification.

### IVRankAnalyzer

Classifies IV rank (0-100) into five tiers:

| Level | Threshold |
|---|---|
| Very High | rank >= 80 |
| High | 60 <= rank < 80 |
| Neutral | 20 <= rank < 60 |
| Very Low | rank < 20 |

Out-of-range values ( < 0 or > 100) return Unknown.

### IVPercentileAnalyzer

Same threshold structure as IVRank, using percentile values:

| Level | Threshold |
|---|---|
| Very High | pctl >= 80 |
| High | 60 <= pctl < 80 |
| Neutral | 40 <= pctl < 60 |
| Low | pctl < 40 |

### VolatilityRegimeAnalyzer

Classifies the combined IV/HV state:

| Regime | Condition |
|---|---|
| Expansion | IV >> HV and IV trend rising |
| Compression | IV << HV and IV trend falling |
| Stable | IV ≈ HV and both trending flat |
| Transition | IV ≈ HV but trending |
| Unknown | IV or HV missing |

Also determines **buying bias** (cheap options → buy vol) vs **selling bias**
(expensive options → sell vol).

## VolatilityAnalyzer (Orchestrator)

The `VolatilityAnalyzer` runs all five sub-analyzers against a single
`VolatilitySnapshot` and produces:

1. `VolatilityAnalysis` — all structured fields
2. `Evidence` — for the Evidence Engine / Fusion Engine
3. `VolatilityExplanation` — structured interpretation sections

### Output Sections

- **Current Volatility**: IV level, value, trend
- **Historical Comparison**: HV level, trend, stability
- **IV vs HV**: Premium, discount, or alignment
- **Regime**: Expansion, compression, stable, transition
- **Risk**: Data completeness warnings
- **Institutional Interpretation**: Trading implications
  - Expensive options → premium collection, tail-risk hedging
  - Cheap options → long premium, volatility mean-reversion

## Data Model

### VolatilitySnapshot

| Field | Type | Description |
|---|---|---|
| `implied_volatility` | `float \| None` | Current ATM implied volatility |
| `historical_volatility` | `float \| None` | Current historical/realized volatility |
| `realized_volatility` | `float \| None` | Alternative realized volatility |  | `implied_volatilities` | `tuple[float, ...]` | Recent IV values for trend detection |
| `historical_volatilities` | `tuple[float, ...]` | Recent HV values for trend/stability |
| `iv_rank` | `float \| None` | IV rank (0-100) |
| `iv_percentile` | `float \| None` | IV percentile (0-100) |
| `volatility_index` | `float \| None` | External volatility index (e.g. VIX) |
| `underlying_price` | `float \| None` | Current underlying price |

### VolatilityAnalysis

| Field | Type | Description |
|---|---|---|
| `current_iv` | `float \| None` | Current implied volatility |
| `current_hv` | `float \| None` | Current historical volatility |
| `iv_rank` | `float \| None` | IV rank value (0-100) |
| `iv_percentile` | `float \| None` | IV percentile value (0-100) |
| `iv_vs_hv` | `IVHVRelation` | Premium, discount, or normal |
| `volatility_regime` | `VolatilityRegime` | Expansion, compression, etc. |
| `iv_level` | `IVLevel` | High, Low, Normal |
| `iv_rank_level` | `IVRankLevel` | Very High through Very Low |
| `iv_trend` | `IVTrend` | Rising, Falling, Flat |
| `hv_trend` | `HVTrend` | Rising, Falling, Flat |
| `hv_stability` | `HVStability` | Stable or Unstable |
| `buying_bias` | `bool` | Conditions favor vol buying |
| `selling_bias` | `bool` | Conditions favor vol selling |
| `overall_bias` | `MarketBias` | Directional market interpretation |
| `confidence` | `float` | Aggregate confidence (0.0-1.0) |
| `warnings` | `tuple[str, ...]` | Missing data warnings |
| `evidence` | `Evidence \| None` | Evidence for fusion |
| `explanation` | `VolatilityExplanation \| None` | Structured explanation |

## Missing Data Handling

All volatility values may be `None`. The engine never crashes on missing data:

- Missing IV → `IVLevel.UNKNOWN`, confidence = 0.0
- Missing HV → `None` returned, stability = `UNKNOWN`
- Missing rank/percentile → `IVRankLevel.UNKNOWN`
- Missing IV and HV → `VolatilityRegime.UNKNOWN`
- Warnings are generated for each missing field

## Evidence Integration

The `VolatilityAnalyzer` produces `Evidence` with:

- `source`: "Volatility"
- `category`: `EvidenceCategory.OPTION_CHAIN`
- `signal`: Derived from overall bias (Bullish/Bearish/Neutral)
- `score`: Based on confidence-weighted bias
- `confidence`: Average of sub-analyzer confidences

This evidence can be consumed by the Intelligence Fusion Engine.

## Future Compatibility

The architecture supports these extensions without redesign:

- **Volatility Smile/Skew**: Add per-strike IV data to `VolatilitySnapshot`
- **Volatility Surface**: Extend with tenor dimension and term structure models
- **Term Structure**: Add forward volatility and curve analysis
- **Variance Risk Premium**: Use existing IV/HV comparison infrastructure
- **Volatility Clustering**: Extend regime analysis with GARCH-aware features

## Quality

- Strict typing throughout
- Frozen dataclasses with slots
- Enums for all classifications
- Ruff clean, Black clean, MyPy clean
- Full test coverage
- No broker imports
- No API calls
- No Black-Scholes implementation
- No duplicated logic

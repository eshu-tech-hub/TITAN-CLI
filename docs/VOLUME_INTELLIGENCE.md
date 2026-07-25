# Volume Intelligence Engine

## Overview

The Volume Intelligence Engine analyses market participation and determines whether price movements are supported by meaningful volume. It is a pure analysis module that consumes only `MarketDataSeries` and produces institutional-grade volume context for the Evidence Engine and Intelligence Fusion Engine.

### Core Philosophy

> Analyse observable volume only. Do not estimate institutional orders. Do not implement Volume Profile, Footprint Charts, or CVD.

The engine evaluates four dimensions of volume:

1. **Relative Volume (RVOL)** — current volume relative to average
2. **Volume Trend** — slope, expansion, and contraction patterns
3. **Accumulation / Distribution** — price-volume relationship divergence
4. **Breakout Confirmation** — volume validating price movement

---

## Architecture

```
MarketDataSeries
       │
       ├─→ RelativeVolumeAnalyzer    (RVOL, participation level)
       ├─→ VolumeTrendAnalyzer       (slope, expansion, contraction)
       ├─→ AccumulationDistributionAnalyzer  (A/D, divergence)
       │
       └─→ VolumeAnalyzer (orchestrator)
                │
                ├─→ VolumeAnalysis
                ├─→ Evidence (MARKET_VOLUME)
                └─→ VolumeExplanation
```

### Analyzers

| Component | File | Responsibility |
|-----------|------|---------------|
| `VolumeAnalyzer` | `volume.py` | Orchestrator — combines sub-analyzers, generates evidence + explanation |
| `VolumeTrendAnalyzer` | `volume_trend.py` | Linear regression slope, expansion ratio, trend direction |
| `RelativeVolumeAnalyzer` | `relative_volume.py` | RVOL ratio, participation level classification |
| `AccumulationDistributionAnalyzer` | `accumulation_distribution.py` | Up/down volume ratio, price-volume divergence |

---

## Data Models

### Enums

| Enum | Values |
|------|--------|
| `VolumeBias` | BULLISH, BEARISH, NEUTRAL, UNKNOWN |
| `ParticipationLevel` | VERY_LOW, LOW, NORMAL, HIGH, EXTREME |

### Core Dataclasses

All dataclasses are frozen with slots for immutability and performance.

| Class | Key Fields |
|-------|-----------|
| `VolumeTrend` | slope, expanding, contracting, expansion_ratio, confidence |
| `RelativeVolume` | rvol, average_volume, participation, confidence |
| `AccumulationDistribution` | accumulation, distribution, ad_ratio, divergence, confidence |
| `VolumeExplanation` | current_volume, relative_volume, participation, accumulation_distribution, breakout_quality, institutional_interpretation |
| `VolumeAnalysis` | current_volume, average_volume, relative_volume, participation_level, volume_bias, breakout_confirmation, exhaustion_probability, trend, relative, accumulation_distribution, confidence, warnings, metadata, evidence, explanation |

All classes provide a `neutral_placeholder()` classmethod for graceful degradation on insufficient data.

---

## Relative Volume (RVOL)

RVOL is the ratio of current candle volume to the average volume over a configurable lookback period (default 20).

### Participation Level Classification

| RVOL Range | Participation Level | Interpretation |
|------------|-------------------|----------------|
| ≤ 0.25 | VERY_LOW | Market is illiquid |
| ≤ 0.67 | LOW | Below-normal conviction |
| 0.67–1.5 | NORMAL | Typical market activity |
| 1.5–3.0 | HIGH | Significant institutional interest |
| ≥ 3.0 | EXTREME | Potential climax or exhaustion |

---

## Volume Trend

Volume trend is evaluated across two windows:
- **Recent**: last 5 candles
- **Prior**: 10 candles before the recent window

State is determined by the ratio of recent average to prior average:

| Condition | Ratio |
|-----------|-------|
| Expanding | ≥ 1.25x |
| Contracting | ≤ 0.75x |
| Stable | otherwise |

Slope is computed via simple linear regression over the last 10 candles.

---

## Accumulation / Distribution

Detected by evaluating the price-volume relationship over the last 5 periods:

- **Accumulation**: up-volume ratio ≥ 0.6 (price rises on rising volume)
- **Distribution**: up-volume ratio ≤ 0.4 (price falls on rising volume)
- **Divergence**: price moves without volume confirmation in ≥ half the lookback periods

The `ad_ratio` is the proportion of up-volume to total directional volume.

---

## Breakout Confirmation

A breakout is considered confirmed when:
- Volume is **expanding** (from VolumeTrendAnalyzer)
- **AND** accumulation OR distribution is detected (from AccumulationDistributionAnalyzer)

This prevents false breakouts on low conviction volume.

---

## Exhaustion Probability

Estimated from three factors:

| Factor | Contribution |
|--------|-------------|
| RVOL ≥ 3.0 | +0.4 |
| Volume contracting | +0.3 |
| Decreasing volume over 3 candles + elevated RVOL | +0.3 |

Maximum is capped at 1.0.

---

## Evidence Generation

Each `VolumeAnalysis` produces a single `Evidence` item:

| Field | Value |
|-------|-------|
| Source | `"Volume"` |
| Category | `EvidenceCategory.VOLUME` |
| Signal | Mapped from `VolumeBias` |
| Score | Base 65 (bullish) / 35 (bearish) / 50 (neutral), +5 for breakout confirmation, +5 for confidence≥0.7, +3 for confidence≥0.5 |
| Confidence | Weighted average of sub-analyzers + sample factor |
| Reasons | RVOL, participation level, bias, breakout status |

---

## Confidence Calculation

```
confidence = (relative.confidence × 0.35 +
              trend.confidence × 0.35 +
              ad.confidence × 0.30 +
              sample_factor × 0.20) / sum(weights)
```

Sample factor = `min(1.0, candle_count / 20)`.

---

## Institutional Interpretation

The `institutional_interpretation` section of `VolumeExplanation` provides contextual judgement:

- **Bullish**: "Volume supports bullish positioning. Institutional accumulation detected."
- **Bearish**: "Volume supports bearish positioning. Institutional distribution detected."
- **Neutral**: "Volume is neutral. Institutions are not actively positioning."
- **Unknown**: "Volume context is inconclusive. Cross-reference with market structure."

Exhaustion warnings are appended when probability ≥ 0.3 (moderate) or ≥ 0.6 (elevated).

---

## Testing

Tests cover:

- High RVOL and low RVOL scenarios
- Volume expansion and contraction
- Bullish accumulation and bearish distribution
- Breakout confirmation and no-breakout cases
- Single candle and missing volume edge cases
- Flat market with no trend
- Evidence generation and signal mapping
- Explanation generation and section content
- Frozen dataclass validation (immutability, slots)
- Neutral placeholder construction
- Exhaustion probability computation
- Confidence bounds

Run with:

```bash
pytest tests/test_volume_intelligence.py -v
```

---

## Future Roadmap

The architecture supports these extensions without redesign:

| Feature | Integration Point |
|---------|------------------|
| Volume Profile | New sub-analyzer, same `MarketDataSeries` input |
| Footprint Charts | New sub-analyzer, additional data source |
| Bid/Ask Delta | New sub-analyzer, new data fields |
| Cumulative Volume Delta (CVD) | New sub-analyzer, tick-level data |
| Iceberg Detection | Heuristic in `AccumulationDistributionAnalyzer` |
| Absorption | New sub-analyzer, same orchestrator pattern |

---

## Dependencies

- `titan/market/series.py` — `MarketDataSeries`
- `titan/core/evidence/` — `Evidence`, `EvidenceCategory`, `EvidenceSignal`
- **No broker imports**
- **No API calls**
- **No Black-Scholes**

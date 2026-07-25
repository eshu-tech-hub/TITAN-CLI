# ADR-008: VWAP Intelligence Engine

## Status

Accepted

## Context

M3.1.2 requires a VWAP Intelligence Engine that computes session VWAP from supplied price data and produces institutional-grade VWAP context. The system must:

1. Compute standard session VWAP using typical price weighted by volume
2. Classify price position relative to VWAP (above, below, at, unknown)
3. Determine institutional bias from VWAP context (bullish, bearish, neutral, unknown)
4. Analyse VWAP slope, direction, and price interactions (crossover, reclaim, rejection, pullback)
5. Compute upper and lower deviation bands for dynamic support/resistance
6. Integrate with the Evidence Engine and Intelligence Fusion Engine
7. Support future extensions for Anchored VWAP, Multi-session VWAP, Weekly/Monthly VWAP, VWAP Profile, and Rolling VWAP without redesign
8. Be broker-independent with no API calls and no execution algorithm integration
9. Pass Ruff, Black, MyPy, and Pytest quality checks

## Decision

We will implement the VWAP Intelligence Engine as three components plus an orchestrator:

### 1. VWAPEngine (Core Computation)

- `compute_vwap(series)` — computes per-candle cumulative VWAP using typical price `(H+L+C)/3` weighted by volume
- `current_vwap(vwap_values)` — returns the latest VWAP level
- Handles zero-volume edge cases (returns 0.0 when cumulative volume is 0)

### 2. VWAPTrendAnalyzer

- Computes VWAP slope using linear regression over the last 10 candles
- Classifies direction (BULLISH/BEARISH/SIDEWAYS) from slope sign
- Detects crossover — price crosses VWAP (sign change in price-VWAP difference over lookback window)
- Detects reclaim — price moves from consistently below VWAP to above VWAP
- Detects rejection — price moves from consistently above VWAP to at/near VWAP (touches and reverses)
- Detects pullback — price moves away from VWAP then returns within threshold distance

### 3. VWAPBandsAnalyzer

- Computes standard deviation of price-VWAP differences across all candles
- Calculates upper band = VWAP + deviations × std_dev and lower band = VWAP - deviations × std_dev
- Default deviation multiplier: 2.0
- Computes current deviation multiple (how many standard deviations from VWAP)
- Computes normalized bandwidth `(upper - lower) / vwap`

### 4. VWAPAnalyzer (Orchestrator)

- Creates `VWAPEngine`, `VWAPTrendAnalyzer`, `VWAPBandsAnalyzer` instances
- Determines price position and institutional bias from VWAP distance and slope
- Generates `Evidence` with:
  - Source: `"VWAP"`
  - Category: `MARKET_STRUCTURE`
  - Signal: BULLISH/BEARISH/NEUTRAL/UNKNOWN mapped from bias
  - Base score: BULLISH→65, BEARISH→35, NEUTRAL/UNKNOWN→50
  - Score adjusted +5 when crossover/reclaim detected, +5 for high confidence
  - Confidence weighted: bias (0.3) + trend (0.4) + bands (0.3) + sample factor (0.2, normalized)
- Generates structured `VWAPExplanation` with six sections:
  - VWAP — current level and distance
  - Institutional Bias — market context interpretation
  - Price Position — relative to VWAP
  - VWAP Trend — slope and interactions
  - Support/Resistance — band levels and deviation
  - Institutional Interpretation — composite assessment
- Returns `VWAPAnalysis.neutral_placeholder()` when data is insufficient

### Data Models

- `VWAPBias` enum: BULLISH, BEARISH, NEUTRAL, UNKNOWN
- `VWAPPosition` enum: ABOVE, BELOW, AT, UNKNOWN
- `VWAPTrend` dataclass: slope, direction, crossover, reclaim, rejection, pullback, confidence, reasons
- `VWAPBands` dataclass: upper, lower, deviation, bandwidth, confidence, reasons
- `VWAPExplanation` dataclass: six-section structured explanation
- `VWAPAnalysis` dataclass: vwap, current_price, distance, position, bias, slope, upper_band, lower_band, trend, bands, confidence, warnings, metadata, evidence, explanation with `neutral_placeholder()` classmethod

## Alternatives Considered

### Simple vs. Interactive VWAP
- **Decision**: Standard simple VWAP (cumulative running average)
- **Rejected**: Interactive VWAP (re-calculated on each new data point) — functionally equivalent for the orchestrator; we compute per-candle values which supports both

### Regression-Based vs. Threshold-Based Crossover Detection
- **Decision**: Threshold-based (sign change in price-VWAP difference over lookback window)
- **Rejected**: Regression-based (fitting a line to recent differences) — more computationally expensive without material benefit for crossover detection

### Fixed vs. Configurable Deviation Bands
- **Decision**: Default 2.0 deviations, configurable via parameter
- **Rationale**: Follows standard VWAP band convention; configurability allows users to tighten/widen bands

## Consequences

### Positive
1. Clean separation of concerns — VWAP computation, trend analysis, bands analysis, and orchestration are independent
2. Future VWAP variants (Anchored, Multi-session, Weekly, Monthly, Rolling) can add new data sources without changing the analysis pipeline
3. No broker SDK imports — pure computation from supplied price data
4. Evidence Engine integration follows the same pattern as Market Structure Intelligence
5. Explanation generation follows the same six-section pattern as Market Structure Intelligence

### Negative
1. VWAP is recomputed from scratch on each `analyze()` call — no caching of intermediate cumulative values between calls
2. Linear regression slope over 10 candles uses simple OLS rather than more robust methods

### Mitigations
1. The compute is lightweight (O(n) for n candles); caching can be added later if needed
2. OLS is the industry standard for VWAP slope; robustness can be improved later with Theil-Sen or similar

## Future Evolution

- `VWAPEngine` can be extended with `AnchoredVWAP`, `MultiSessionVWAP`, `WeeklyVWAP`, `MonthlyVWAP` subclasses or mixins
- `VWAPTrendAnalyzer` can accept alternative VWAP data sources (e.g., rolling, anchored) without changes
- `VWAPBandsAnalyzer` can support multiple band styles (fixed standard deviation, percentile-based, ATR-based)
- `VWAPAnalyzer` parameter injection (via `__init__`) supports dependency injection for testing and future variants

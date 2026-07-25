# VWAP Intelligence Engine

## Overview

Volume-Weighted Average Price (VWAP) is one of the most widely used institutional benchmarks in financial markets. It represents the average price a security has traded at throughout the day, weighted by volume.

In institutional trading, VWAP serves as:
- **Execution benchmark** — institutions measure fill quality against VWAP
- **Trend confirmation** — price above/below VWAP indicates institutional sentiment
- **Dynamic support/resistance** — VWAP acts as a magnet for price
- **Institutional bias** — sustained price above VWAP suggests accumulation; below suggests distribution

The VWAP Intelligence Engine (Milestone M3.1.2) computes session VWAP from supplied `MarketDataSeries` and produces institutional context about price position, VWAP trend, price interactions (crossovers, reclaims, rejections, pullbacks), and deviation bands.

## Architecture

```
MarketDataSeries
       │
       ▼
┌──────────────┐
│  VWAPEngine  │  compute_vwap(): Σ(tp × volume) / Σ(volume)
│              │  current_vwap(): latest VWAP level
└──────┬───────┘
       │ vwap_values, vwap_level
       ▼
┌───────────────────┐
│ VWAPTrendAnalyzer  │  Slope, direction, crossover, reclaim,
│                    │  rejection, pullback detection
└────────┬──────────┘
         │ VWAPTrend
         ▼
┌───────────────────┐
│ VWAPBandsAnalyzer  │  Upper/lower deviation bands, bandwidth,
│                    │  current deviation multiple
└────────┬──────────┘
         │ VWAPBands
         ▼
┌───────────────────┐
│   VWAPAnalyzer     │  Evidence generation
│   (Orchestrator)   │  Explanation generation
│                    │  Institutional bias determination
└───────────────────┘
         │
         ▼
   VWAPAnalysis
```

### Dependencies

- `VWAPEngine` — requires `MarketDataSeries` with OHLCV candles and volume
- `VWAPTrendAnalyzer` — requires `MarketDataSeries` and pre-computed VWAP values
- `VWAPBandsAnalyzer` — requires `MarketDataSeries` and pre-computed VWAP values
- `VWAPAnalyzer` — orchestrates all three sub-components

## VWAP Calculation

Standard session VWAP is computed as a cumulative running average:

```
VWAP_i = Σ(tp_j × vol_j) / Σ(vol_j) for j = 1..i
```

Where `tp_j = (high_j + low_j + close_j) / 3` (typical price).

## Price Position

| Position | Distance        | Interpretation                        |
|----------|-----------------|---------------------------------------|
| ABOVE    | > 0.001         | Price above VWAP — bullish context    |
| BELOW    | < -0.001        | Price below VWAP — bearish context    |
| AT       | < 0.001         | Price at VWAP — decision point        |
| UNKNOWN  | N/A             | No VWAP data                          |

## Institutional Bias

| Price Position | VWAP Slope | Bias     |
|----------------|------------|----------|
| ABOVE          | > 0        | BULLISH  |
| ABOVE          | <= 0       | NEUTRAL  |
| BELOW          | < 0        | BEARISH  |
| BELOW          | >= 0       | NEUTRAL  |
| AT             | > 0        | BULLISH  |
| AT             | < 0        | BEARISH  |
| AT             | = 0        | NEUTRAL  |

## Price Interactions

| Interaction | Description |
|-------------|-------------|
| Crossover   | Price crosses the VWAP line (any direction) |
| Reclaim     | Price moves from below VWAP to above VWAP |
| Rejection   | Price approaches VWAP from above and reverses |
| Pullback    | Price moves away from VWAP and returns |

## Evidence Signal Mapping

| Bias    | Evidence Signal |
|---------|-----------------|
| BULLISH | BULLISH         |
| BEARISH | BEARISH         |
| NEUTRAL | NEUTRAL         |
| UNKNOWN | UNKNOWN         |

## Score Calculation

| Bias    | Base Score |
|---------|------------|
| BULLISH | 65         |
| BEARISH | 35         |
| NEUTRAL | 50         |
| UNKNOWN | 50         |

Adjustments:
- +5 when crossover or reclaim detected
- +5 when confidence >= 0.7
- +3 when confidence >= 0.5

## Current Implementation

- `titan/market/intelligence/vwap.py` — `VWAPEngine`, `VWAPAnalyzer`
- `titan/market/intelligence/vwap_trend.py` — `VWAPTrendAnalyzer`
- `titan/market/intelligence/vwap_bands.py` — `VWAPBandsAnalyzer`
- `titan/market/intelligence/models.py` — `VWAPAnalysis`, `VWAPTrend`, `VWAPBands`, `VWAPExplanation`, `VWAPBias`, `VWAPPosition`
- `tests/test_vwap_intelligence.py` — 62 tests
- `docs/adr/ADR-008-VWAP-Intelligence.md` — Architecture Decision Record

## Future Roadmap

The architecture supports these future extensions without redesign:

- **Anchored VWAP** — VWAP from a specific start date/event
- **Multi-session VWAP** — VWAP across multiple trading sessions
- **Weekly VWAP** — VWAP computed over a weekly window
- **Monthly VWAP** — VWAP computed over a monthly window
- **VWAP Profile** — Distribution of VWAP throughout the trading session
- **Rolling VWAP** — VWAP with a rolling window (e.g., 20-period)

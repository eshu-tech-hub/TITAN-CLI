# Vanna Exposure Intelligence

## Overview

Vanna measures the rate of change of an option's Vega with respect to changes in the underlying asset's price:

```
Vanna = ∂Vega / ∂Spot = ∂²Option / (∂Spot × ∂σ)
```

In institutional trading, Vanna quantifies how a dealer's Vega hedge must be adjusted as the underlying price moves. This creates a feedback loop between price changes and implied volatility that can amplify or suppress directional moves.

The Vanna Exposure Intelligence Engine (Milestone M2.2.7) consumes **per-strike Vanna values** from supplied option analytics and produces two layers of analysis:

1. **Vanna Regime** — what the net Vanna position is (positive, negative, balanced, or unknown)
2. **Vanna Pressure** — what the Vanna position implies for dealer hedging, IV dynamics, and price action

## Architecture

```
OptionChainSnapshot (per-strike vanna × OI)
         │
         ▼
┌─────────────────────┐
│  VannaRegimeAnalyzer │  net_vanna = Σ(call_vanna × call_OI) + Σ(put_vanna × put_OI)
│                     │  Regime: POSITIVE / NEGATIVE / BALANCED / UNKNOWN
└─────────┬───────────┘
          │ VannaRegime
          ▼
┌──────────────────────┐
│ VannaPressureAnalyzer  │  iv_sensitivity = f(vanna_regime, gamma_regime)
│                       │  price_sensitivity = f(gamma_regime, vanna_sign, dealer_hedging)
│                       │  Pressure: LOW / MEDIUM / HIGH / EXTREME
└─────────┬────────────┘
          │ VannaPressure
          ▼
┌──────────────────────┐
│ VannaExposureAnalyzer  │  Evidence generation
│                       │  Explanation generation
│                       │  Warnings for missing data
└──────────────────────┘
```

### Dependencies

- `VannaRegimeAnalyzer` — requires `OptionChainSnapshot` with per-strike `call_vanna` / `put_vanna` fields; falls back to `UNKNOWN` regime with no per-strike data
- `VannaPressureAnalyzer` — requires `VannaRegime` plus optional `GammaExposureAnalysis`, `DealerPositioningAnalysis`, `GreeksAnalysis`
- `VannaExposureAnalyzer` — optionally consumes `SurfaceIntelligenceAnalysis`, `OptionChainAnalysis`, `GreeksAnalysis` for context

## Vanna Regime Classification

| Regime   | Net Vanna | Interpretation |
|----------|-----------|----------------|
| POSITIVE | > 0       | Dealers are long Vega. As spot rises, IV increases → dealers sell options to hedge. Resistance to upside, potential acceleration on downside. |
| NEGATIVE | < 0       | Dealers are short Vega. As spot rises, IV decreases → dealers buy options to hedge. Support on upside, potential acceleration on downside. |
| BALANCED | ~ 0       | Vanna exposure is neutral. Minimal IV feedback from price moves. |
| UNKNOWN  | N/A       | No per-strike Vanna data available. |

## Vanna Pressure Levels

| Level  | iv_sensitivity | price_sensitivity | Interpretation |
|--------|----------------|-------------------|----------------|
| LOW    | 0.0-0.3        | 0.0-0.3           | Minimal vanna-driven hedging expected. |
| MEDIUM | 0.3-0.6        | 0.3-0.6           | Moderate dealer vanna rebalancing possible. |
| HIGH   | 0.6-0.8        | 0.6-0.8           | Significant dealer vanna hedging expected. |
| EXTREME| > 0.8          | > 0.8             | Extreme vanna-driven hedging pressure. |

## Evidence Signal Mapping

| Vanna Regime | Vanna Pressure | Evidence Signal |
|--------------|----------------|-----------------|
| POSITIVE     | LOW..MEDIUM    | BULLISH         |
| POSITIVE     | HIGH..EXTREME  | STRONG_BULLISH  |
| NEGATIVE     | LOW..MEDIUM    | BEARISH         |
| NEGATIVE     | HIGH..EXTREME  | STRONG_BEARISH  |
| BALANCED     | any            | NEUTRAL         |
| UNKNOWN      | any            | UNKNOWN         |

## Score Calculation

- Base score: POSITIVE → 65, NEGATIVE → 35, BALANCED → 50
- Adjust: +5 when pressure is HIGH or EXTREME
- Evidence weight = 1.0

## Confidence Calculation

```
overall_confidence = (regime.confidence * 0.5) + (pressure.confidence * 0.5)
```

Where:
- `regime.confidence` reflects completeness of per-strike vanna data
- `pressure.confidence` is weighted: regime (0.4) + gamma exposure (0.3) + dealer positioning (0.2) + greeks (0.1)

## Institutional Interpretation

### Positive Vanna Regime

When the net Vanna position is positive:

- **Dealers are long Vega.** As the price rises, the Vega of their short option positions increases, forcing them to sell options to rebalance.
- **This creates resistance to upward moves.** IV spikes as price rises, which increases put prices → dealers sell puts → adding selling pressure.
- **On downside moves, the effect reverses.** As price drops, IV drops → dealers buy back options → adding buying pressure.
- **Impact:** Positive Vanna is stabilizing in uptrends (resistance) but destabilizing in downtrends (acceleration).

### Negative Vanna Regime

When the net Vanna position is negative:

- **Dealers are short Vega.** As the price rises, the Vega of their short option positions decreases, forcing them to buy options to rebalance.
- **This creates support on upward moves.** IV drops as price rises → dealers buy options → adding buying pressure.
- **On downside moves, IV rises → dealers sell options → adding selling pressure.**
- **Impact:** Negative Vanna is stabilizing in downtrends (support) but destabilizing in uptrends (acceleration).

### Vanna × Gamma Interactions

| Gamma Regime  | Vanna Regime | Combined Effect |
|---------------|--------------|-----------------|
| Positive (long) | Positive    | Strong pinning resistance. Dealers short vol surfacing, long gamma stabilizes price. |
| Positive (long) | Negative    | Support on dips, resistance on rallies. Mixed signals. |
| Negative (short)| Positive    | Amplified moves. Dealers chase price. High vol-of-vol expected. |
| Negative (short)| Negative    | Acceleration on drops, resistance on rallies. Liquidity events possible. |

## Usage

```python
from titan.options.analytics import (
    VannaExposureAnalyzer,
    VannaExposureInput,
)
from titan.options.analytics import OptionChainSnapshot, OptionStrikeSnapshot

# Build a snapshot with per-strike vanna
strike = OptionStrikeSnapshot(
    strike_price=100.0,
    call_open_interest=5000,
    put_open_interest=3000,
    call_vanna=0.001,
    put_vanna=-0.0005,
)
snapshot = OptionChainSnapshot(
    underlying="SPY",
    expiry=datetime(2026, 7, 17),
    timestamp=datetime.now(),
    strikes=(strike,),
    underlying_price=100.0,
)

# Analyze
analyzer = VannaExposureAnalyzer()
result = analyzer.analyze(option_chain_snapshot=snapshot)

print(f"Net Vanna: {result.net_vanna}")
print(f"Regime: {result.regime.regime_type}")
print(f"Pressure: {result.pressure.pressure_level}")
print(f"Confidence: {result.confidence:.2f}")
```

## Future Enhancements

- **Charm (DDeltaDtime):** Delta decay sensitivity to price → cross-reference with Vanna for time-dependent hedging analysis
- **Dealer Hedging Flow:** Real-time hedging estimates using Vanna + Gamma + Vega decomposition
- **0DTE Options:** Intraday Vanna dynamics for zero-days-to-expiry contracts
- **Intraday Flow:** Vanna regime changes during trading hours
- **Cross-expiry Vanna:** Vanna contributions across multiple expiries
- **Historical Vanna:** Track Vanna regime changes over time for pattern detection

# Charm Exposure Intelligence

## Overview

Charm measures the rate of change of an option's Delta with respect to time:

```
Charm = -∂Delta / ∂Time = -∂²Option / (∂Spot × ∂Time)
```

In institutional trading, Charm quantifies how a dealer's delta hedge must be adjusted as time passes — known as **dealer delta decay**. This creates a systematic hedging flow that intensifies as options approach expiry.

The Charm Exposure Intelligence Engine (Milestone M2.2.8) consumes **per-strike Charm values** from supplied option analytics and produces two layers of analysis:

1. **Charm Regime** — what the net Charm position is (positive, negative, balanced, or unknown)
2. **Charm Pressure** — what the Charm position implies for time-driven dealer hedging, delta decay, and near-expiry risk

## Architecture

```
OptionChainSnapshot (per-strike charm × OI)
         │
         ▼
┌───────────────────────┐
│  CharmRegimeAnalyzer   │  net_charm = Σ(call_charm × call_OI) + Σ(put_charm × put_OI)
│                       │  Regime: POSITIVE / NEGATIVE / BALANCED / UNKNOWN
└─────────┬─────────────┘
          │ CharmRegime
          ▼
┌────────────────────────┐
│ CharmPressureAnalyzer   │  time_sensitivity = f(charm_regime, gamma_regime, vanna)
│                        │  near_expiry_risk = expiry within 7d + active charm regime
│                        │  Pressure: LOW / MEDIUM / HIGH / EXTREME
└─────────┬──────────────┘
          │ CharmPressure
          ▼
┌────────────────────────┐
│ CharmExposureAnalyzer    │  dealer_delta_decay derived from time_sensitivity + near_expiry
│                         │  Evidence generation
│                         │  Explanation generation
│                         │  Warnings for missing data
└────────────────────────┘
```

### Dependencies

- `CharmRegimeAnalyzer` — requires `OptionChainSnapshot` with per-strike `call_charm` / `put_charm` fields; falls back to `UNKNOWN` regime with no per-strike data
- `CharmPressureAnalyzer` — requires `CharmRegime` plus optional `GammaExposureAnalysis`, `VannaExposureAnalysis`, `DealerPositioningAnalysis`, `OptionChainSnapshot` (for expiry detection)
- `CharmExposureAnalyzer` — optionally consumes `SurfaceIntelligenceAnalysis`, `OptionChainAnalysis`, `GreeksAnalysis` for context

## Charm Regime Classification

| Regime   | Net Charm | Interpretation |
|----------|-----------|----------------|
| POSITIVE | > 0       | Dealer delta increases with time. Dealers must buy delta as time passes to maintain hedges. Systematic buy pressure from delta rebalancing. |
| NEGATIVE | < 0       | Dealer delta decays with time. Dealers must sell delta as time passes to maintain hedges. Systematic sell pressure from delta rebalancing. |
| BALANCED | ~ 0       | Charm exposure is neutral. Dealer delta is stable with respect to time. |
| UNKNOWN  | N/A       | No per-strike Charm data available. |

## Charm Pressure Levels

| Level  | time_sensitivity | Interpretation |
|--------|------------------|----------------|
| LOW    | 0.0-0.25         | Minimal charm-driven delta rebalancing expected. |
| MEDIUM | 0.25-0.45        | Moderate dealer delta adjustment over time. |
| HIGH   | 0.45-0.7         | Significant time-driven dealer hedging expected. |
| EXTREME| > 0.7            | Extreme charm-driven delta decay pressure. |

Near-expiry risk adds a +0.2 boost to the combined pressure score.

## Evidence Signal Mapping

| Charm Regime | Charm Pressure | Evidence Signal |
|--------------|----------------|-----------------|
| POSITIVE     | LOW..MEDIUM    | BULLISH         |
| POSITIVE     | HIGH..EXTREME  | STRONG_BULLISH  |
| NEGATIVE     | LOW..MEDIUM    | BEARISH         |
| NEGATIVE     | HIGH..EXTREME  | STRONG_BEARISH  |
| BALANCED     | any            | NEUTRAL         |
| UNKNOWN      | any            | UNKNOWN         |

## Score Calculation

- Base score: POSITIVE → 60, NEGATIVE → 40, BALANCED → 50
- Adjust: +5 when pressure is HIGH or EXTREME
- Evidence weight = 1.0

## Confidence Calculation

```
overall_confidence = (regime.confidence * 0.5) + (pressure.confidence * 0.5)
```

Where:
- `regime.confidence` reflects completeness of per-strike charm data
- `pressure.confidence` is weighted: regime (0.35) + gamma exposure (0.25) + vanna exposure (0.2) + dealer positioning (0.1) + greeks (0.1)

## Dealer Delta Decay

Dealer delta decay is computed as:

```
dealer_delta_decay = pressure.time_sensitivity
                   + (0.15 if near_expiry_risk else 0)
                   + (0.10 if strong charm signal with confidence else 0)
                   (capped at 1.0)
```

### Interpretation

| decay range | Meaning |
|-------------|---------|
| 0.0-0.3     | Low decay — minimal dealer delta adjustment needed |
| 0.3-0.5     | Moderate decay — some dealer delta adjustment expected |
| 0.5-0.7     | High decay — significant dealer delta rebalancing |
| 0.7-1.0     | Extreme decay — aggressive dealer delta hedging expected |

## Near-Expiry Risk

Near-expiry charm risk is flagged when:
1. Expiry is within 7 calendar days
2. Charm regime is active (POSITIVE or NEGATIVE, not BALANCED or UNKNOWN)

When flagged, charm-driven hedging accelerates because delta decay per unit time increases as time-to-expiry approaches zero.

## Institutional Interpretation

### Positive Charm Regime

When the net Charm position is positive:

- **Dealer delta increases with time.** As each day passes, ITM calls gain delta and OTM puts lose delta.
- **Dealers must buy delta** to maintain delta-neutral hedges.
- **This creates systematic buy pressure** that is most pronounced for strikes with high open interest.
- **Near expiry**, the effect accelerates — dealers may need to aggressively buy delta in the final days.
- **Impact:** Positive charm provides a structural bid that supports prices over time, especially near key strike concentrations.

### Negative Charm Regime

When the net Charm position is negative:

- **Dealer delta decays with time.** As each day passes, OTM calls lose delta and ITM puts gain delta.
- **Dealers must sell delta** to maintain delta-neutral hedges.
- **This creates systematic sell pressure** that is most pronounced for strikes with high open interest.
- **Near expiry**, the effect accelerates — dealers may need to aggressively sell delta in the final days.
- **Impact:** Negative charm provides structural supply that weighs on prices over time, especially near key strike concentrations.

### Charm × Gamma Interactions

| Gamma Regime  | Charm Regime | Combined Effect |
|---------------|--------------|-----------------|
| Positive (long) | Positive    | Dealers long gamma dampen moves; systematic delta buy over time supports rallies. |
| Positive (long) | Negative    | Dealers long gamma dampen moves; systematic delta sell over time weighs on rallies. |
| Negative (short)| Positive    | Dealers short gamma amplify moves; systematic delta buy over time accelerates rallies. |
| Negative (short)| Negative    | Dealers short gamma amplify moves; systematic delta sell over time accelerates declines. |

## Usage

```python
from titan.options.analytics import (
    CharmExposureAnalyzer,
    CharmExposureInput,
)
from titan.options.analytics import OptionChainSnapshot, OptionStrikeSnapshot

# Build a snapshot with per-strike charm
strike = OptionStrikeSnapshot(
    strike_price=100.0,
    call_open_interest=5000,
    put_open_interest=3000,
    call_charm=0.001,
    put_charm=-0.0005,
)
snapshot = OptionChainSnapshot(
    underlying="SPY",
    expiry=datetime(2026, 7, 17),
    timestamp=datetime.now(),
    strikes=(strike,),
    underlying_price=100.0,
)

# Analyze
analyzer = CharmExposureAnalyzer()
result = analyzer.analyze(option_chain_snapshot=snapshot)

print(f"Net Charm: {result.net_charm}")
print(f"Regime: {result.regime.regime_type}")
print(f"Pressure: {result.pressure.pressure_level}")
print(f"Dealer Delta Decay: {result.dealer_delta_decay:.2f}")
print(f"Near-expiry risk: {result.near_expiry_risk}")
print(f"Confidence: {result.confidence:.2f}")
```

## Future Enhancements

- **Dealer Hedging Flow:** Real-time delta-decay hedging estimates using Charm + Gamma decomposition
- **0DTE Options:** Intraday Charm dynamics for zero-days-to-expiry contracts — Charm accelerates dramatically on expiry day
- **Intraday Charm:** Charm regime changes during trading hours as time-to-expiry decreases
- **Cross-expiry Charm:** Charm contributions across multiple expiries for term structure analysis
- **Historical Charm:** Track Charm regime changes over time for pattern detection
- **Time-series Flow Analysis:** Predict dealer hedging flows from Charm regime shifts

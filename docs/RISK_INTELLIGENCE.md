# Risk Intelligence Engine

## Overview

The Risk Intelligence Engine converts a qualified trade into a complete institutional risk plan. It consumes completed intelligence and trade qualification results to determine how capital should be protected and allocated.

It does **not** decide whether to trade, select strikes, or place orders.

Its sole responsibility is to answer: *"If this trade is taken, how should capital be protected and allocated?"*

## Architecture

```
RiskInput (TradeQualification + Intelligence)
        │
        ▼
RiskEngine
        │
        ├── PositionSizingEngine    ──  Max capital, risk per trade, units, contracts
        ├── StopLossEngine          ──  Technical, volatility, time, emergency stops
        ├── TargetEngine            ──  Three targets, trailing trigger, R:R
        ├── CapitalAllocationEngine ──  Used/available capital, daily/weekly exposure
        └── ExposureEngine          ──  Directional, volatility, event, liquidity exposure
        │
        ▼
RiskAnalysis
```

## Inputs

The engine accepts a `RiskInput` containing:

| Input | Type | Required |
|-------|------|----------|
| Trade Qualification | `TradeQualification` | Yes |
| Market Regime | `MarketRegimeAnalysis` | No |
| Volatility | `VolatilityAnalysis` | No |
| Liquidity | `LiquidityAnalysis` | No |
| Dealer Positioning | `DealerPositioningAnalysis` | No |
| Gamma Exposure | `GammaExposureAnalysis` | No |
| Event Analysis | `EventAnalysis` | No |
| News Analysis | `NewsAnalysis` | No |
| Intelligence Fusion | `IntelligenceFusion` | No |
| Underlying Price | `float` | No |
| Entry Price | `float` | No |

## Output

`RiskAnalysis` contains:

| Field | Description |
|-------|-------------|
| `risk_profile` | CONSERVATIVE, MODERATE, AGGRESSIVE, INSTITUTIONAL |
| `risk_score` | 0–100 score with band (VERY_LOW/LOW/MODERATE/HIGH/EXTREME) |
| `position_sizing` | Max capital, risk per trade, units, contracts, utilisation |
| `stop_loss` | Technical, volatility, time, invalidation, emergency stops |
| `targets` | Three profit targets, trailing trigger, risk-reward ratio |
| `capital_allocation` | Used/available capital, daily/weekly exposure, concentration |
| `exposure` | Directional, volatility, event, sector, liquidity, overall |
| `decision_context` | Size guidance, hedging requirements, max contracts |
| `evidence` | Evidence for Intelligence Fusion Engine |
| `explanation` | Structured human-readable explanation |
| `warnings` | Non-fatal warnings |

## Risk Profiles

| Profile | Max Risk/Trade | Max Position | Kelly Fraction | Min Confidence |
|---------|:-------------:|:------------:|:--------------:|:--------------:|
| CONSERVATIVE | 2% | 10% | 0.25 | 0.6 |
| MODERATE | 3% | 15% | 0.50 | 0.5 |
| AGGRESSIVE | 5% | 25% | 0.75 | 0.4 |
| INSTITUTIONAL | 1% | 5% | 0.10 | 0.7 |

## Position Sizing

The Position Sizing Engine computes:
1. **Base allocation** — Total capital × max position size %
2. **Risk per trade** — Total capital × max risk per trade %
3. **Size modifier** — Adjusted by trade score, liquidity, volatility, event risk, and confidence:
   - Score ≥ 80: +25%
   - Score 60–80: 0%
   - Score 40–60: −25%
   - Score < 40: −50%
   - Poor liquidity: −50%
   - High volatility: −15–25%
   - Extreme event risk: −50%
   - Low confidence: −50%
4. **Units** — Based on risk per trade and entry price
5. **Contracts** — Estimated from lot size conventions

## Stop Loss

The Stop Loss Engine produces five stop levels:
1. **Technical Stop** — From gamma walls (put wall for longs, call wall for shorts)
2. **Volatility Stop** — Entry ± (ATR × multiplier), where ATR is estimated from IV
3. **Time Stop** — Before the next scheduled economic event
4. **Invalidation Level** — Thesis invalidation from dealer positioning or gamma regime
5. **Emergency Stop** — Wider stop at 2× the volatility stop distance
6. **Recommended** — Most protective valid stop

## Targets

The Target Engine computes three profit targets:
- **Target 1** — Entry + (risk distance × multiplier 1)
- **Target 2** — Entry + (risk distance × multiplier 2)
- **Target 3** — Entry + (risk distance × multiplier 3)
- **Trailing Trigger** — Activates at Target 1
- **Expected R:R** — Target 3 distance ÷ risk distance

Multipliers vary by risk profile (e.g., MODERATE: 1.5×, 2.5×, 3.5×).

## Capital Allocation

Calculates:
- **Capital Used** — Sum of current position market values
- **Available Capital** — Total capital minus used
- **Daily Exposure** — Loss-based exposure from current positions
- **Weekly Exposure** — 2.5× daily exposure
- **Maximum Allocation** — Per-trade limit adjusted for event risk
- **Portfolio Concentration** — Largest position ÷ total capital

## Exposure Assessment

Five dimensions assessed:
- **Directional** — From dealer gamma positioning and gamma regime
- **Volatility** — From volatility regime, IV rank, and IV/HV relation
- **Event** — From event overall risk and highest importance
- **Sector** — From market regime trend strength
- **Liquidity** — From execution grade

Each dimension scored: VERY_LOW, LOW, MODERATE, HIGH, or EXTREME.

## Risk Score (0–100)

| Component | Max Points | Description |
|-----------|:----------:|-------------|
| Position Sizing | 20 | Capital utilisation ratio |
| Stop Loss | 15 | Available stop types |
| Capital Allocation | 20 | Allocation ratio |
| Exposure | 20 | Overall portfolio exposure |
| Event Risk | 15 | Event intelligence assessment |
| Trade Quality | 10 | Inverse of trade score |

### Bands

| Band | Range | Meaning |
|------|-------|---------|
| VERY_LOW | 0–20 | Minimal risk, full allocation |
| LOW | 21–40 | Low risk, standard sizing |
| MODERATE | 41–60 | Moderate risk, standard sizing |
| HIGH | 61–80 | Elevated risk, reduce size |
| EXTREME | 81–100 | Maximum risk, avoid trade |

## Decision Context

Generated from risk score and exposure:
- **avoid_trade** — Risk score EXTREME or extreme event risk
- **reduce_size** — Risk score HIGH or EXTREME
- **normal_size** — Risk score LOW or MODERATE
- **increase_size** — Risk score VERY_LOW
- **hedging_required** — Overall exposure HIGH or EXTREME
- **maximum_contracts** — From position sizing
- **confidence** — Inversely proportional to risk score

## Evidence Generation

Each analysis produces a single `Evidence` object:
- **Category**: `RISK`
- **Source**: `RiskEngine`
- **Signal**: Derived from decision context (avoid = bearish)
- **Score**: Inverse of risk score (100 − risk score)
- **Confidence**: Based on certainty of assessment
- **Reasons**: Key decision drivers

## Explanation

Structured `RiskExplanation` with six sections:
1. **Position Size** — Sizing parameters and rationale
2. **Capital Allocation** — Allocation and concentration
3. **Stop Loss** — All stop levels and rationale
4. **Targets** — Target levels and R:R
5. **Exposure** — All exposure dimensions
6. **Overall Risk Assessment** — Summary and guidance

## Usage

```python
from titan.risk import RiskEngine, RiskInput, RiskProfile
from titan.trading import TradeQualification

engine = RiskEngine()
risk_input = RiskInput(
    trade_qualification=qualification_result,
    market_regime=regime_analysis,
    volatility=volatility_analysis,
    liquidity=liquidity_analysis,
    event_analysis=event_analysis,
    entry_price=19600.0,
    underlying_price=19600.0,
)
result = engine.analyze(
    risk_input=risk_input,
    risk_profile=RiskProfile.INSTITUTIONAL,
    total_capital=10_000_000.0,
)

print(f"Risk Score: {result.risk_score.value:.0f} ({result.risk_score.band.value})")
print(f"Avoid Trade: {result.decision_context.avoid_trade}")
print(f"Max Contracts: {result.decision_context.maximum_contracts}")
print(f"Stop Loss: {result.stop_loss.recommended_stop}")
```

## Dependencies

**Runtime:** Trade Qualification Engine and upstream intelligence modules.

**Test:** pytest.

Zero broker dependencies. Zero API calls. Pure risk planning.

## Future Enhancements

### Short Term
- ATR-based position sizing using realised ATR
- Kelly Criterion and Fractional Kelly integration
- Dynamic leverage based on volatility regime

### Medium Term
- Portfolio margin and SPAN margin estimation
- Broker margin API integration
- Volatility targeting with position scaling

### Long Term
- Monte Carlo risk simulation overlays
- Machine learning risk scoring
- Real-time risk re-evaluation on intelligence updates

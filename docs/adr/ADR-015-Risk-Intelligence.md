# ADR-015: Risk Intelligence Engine

**Status:** Accepted (Milestone M4.2.2)

**Date:** 2026-07-03

**Author:** TITAN Architecture Team

## Context

The TITAN platform now produces trade qualification outputs through the
Trade Qualification Engine (ADR-014). What has been missing is a
comprehensive risk planning layer that converts a qualified trade into
a complete institutional risk plan.

Without this engine, each consumer must independently determine position
sizing, stop loss placement, target selection, capital allocation, and
exposure management — a fragmented process that leads to inconsistent
risk management and prevents systematic capital preservation.

The Risk Intelligence Engine exists to solve this problem. It is the
final planning stage before execution. It does NOT determine BUY/SELL,
CE/PE, strike selection, or order execution. Its sole responsibility is
to determine how capital should be protected and allocated if a trade
is taken.

## Decision

We introduce a `titan/risk/` package containing a `RiskEngine` that
orchestrates five sub-engines:

1. **PositionSizingEngine** — Determines maximum capital, risk per
   trade, units, contracts, and capital utilisation.
2. **StopLossEngine** — Produces technical, volatility, time,
   invalidation, and emergency stop levels.
3. **TargetEngine** — Produces three profit targets, trailing stop
   trigger, and expected risk-reward ratio.
4. **CapitalAllocationEngine** — Calculates capital used, available
   capital, daily/weekly exposure, maximum allocation, and portfolio
   concentration.
5. **ExposureEngine** — Assesses directional, volatility, event,
   sector, and liquidity exposure.

### Package Structure

```
titan/risk/
    __init__.py       # Public API exports
    models.py         # Frozen dataclasses and enums
    exceptions.py     # Domain exceptions
    position.py       # PositionSizingEngine
    stoploss.py       # StopLossEngine
    targets.py        # TargetEngine
    allocation.py     # CapitalAllocationEngine
    exposure.py       # ExposureEngine
    risk.py           # RiskEngine (orchestrator)
```

### Risk Input

The engine accepts a `RiskInput` frozen dataclass that bundles:
- `TradeQualification` (required) — Output from Trade Qualification Engine
- `MarketRegimeAnalysis`, `VolatilityAnalysis`, `LiquidityAnalysis`,
  `DealerPositioningAnalysis`, `GammaExposureAnalysis`, `EventAnalysis`,
  `NewsAnalysis`, `IntelligenceFusion` (all optional — missing components
  degrade gracefully)
- `underlying_price` and `entry_price` (optional — required for
  concrete sizing and stop/target calculation)

### Risk Profiles

Four risk profiles map to pre-configured `RiskProfileConfig` values:

| Profile | Risk/Trade | Position | Kelly Fraction | Min Confidence |
|---------|:----------:|:--------:|:--------------:|:--------------:|
| CONSERVATIVE | 2% | 10% | 0.25 | 0.6 |
| MODERATE | 3% | 15% | 0.50 | 0.5 |
| AGGRESSIVE | 5% | 25% | 0.75 | 0.4 |
| INSTITUTIONAL | 1% | 5% | 0.10 | 0.7 |

### Position Sizing

Position size is computed from:
1. Base allocation = total capital × profile position size %
2. Risk per trade = total capital × profile risk per trade %
3. Size modifier adjusted for:
   - Trade score (25% bonus for ≥80, 75% penalty for <20)
   - Liquidity grade (50% penalty for D/F/UNKNOWN)
   - Volatility regime (25% penalty for expansion)
   - Event risk (50% penalty for high/extreme)
   - Confidence threshold (50% penalty below minimum)
4. Units derived from risk distance and entry price
5. Maximum quantity capped during extreme events

### Stop Loss

Stop levels are derived from:
- **Technical**: Gamma walls and zero-gamma levels from GammaExposure
- **Volatility**: ATR estimate from implied volatility × profile multiplier
- **Time**: Next scheduled economic event from EventAnalysis
- **Invalidation**: Dealer positioning regime (short gamma thesis breach)
- **Emergency**: 2× volatility stop distance
- **Recommended**: Most protective valid stop, bounded by profile limits

### Targets

Targets are computed as:
- Target N = entry ± (risk distance × profile multiplier N)
- Trailing stop trigger = Target 1 level
- Expected R:R = Target 3 distance ÷ risk distance

### Capital Allocation

Allocation is computed from:
- Capital used = sum of current position market values
- Available capital = total − used
- Daily exposure = position P&L-based loss exposure
- Weekly exposure = 2.5× daily exposure
- Maximum allocation = capital × profile position size %, reduced by event risk
- Portfolio concentration = largest position ÷ total capital

### Exposure Assessment

Each risk dimension is scored from intelligence:
- **Directional**: DealerSide.SHORT_GAMMA → HIGH, GammaRegime.NEGATIVE → HIGH
- **Volatility**: VolatilityRegime.EXPANSION → HIGH, IV rank high → MODERATE
- **Event**: EventRisk.EXTREME → EXTREME, EventImportance.CRITICAL → HIGH
- **Sector**: Low trend strength → MODERATE
- **Liquidity**: ExecutionGrade F/UNKNOWN → EXTREME, D → HIGH

Overall risk is the weighted average of all dimensions, with extreme
overrides.

### Risk Score

Score from 0 (lowest risk) to 100 (highest risk):

| Component | Weight | Metric |
|-----------|:------:|--------|
| Position Sizing Risk | 20 | Capital utilisation |
| Stop Loss Risk | 15 | Available stop types |
| Capital Allocation Risk | 20 | Allocation ratio |
| Exposure Risk | 20 | Overall portfolio exposure |
| Event Risk | 15 | Event assessment |
| Trade Quality Risk | 10 | Inverse of trade score |

**Bands:** VERY_LOW (≤20), LOW (21–40), MODERATE (41–60), HIGH (61–80),
EXTREME (81–100).

### Decision Context

| Context | Condition |
|---------|-----------|
| avoid_trade | Risk score EXTREME or extreme event risk |
| reduce_size | Risk score HIGH or EXTREME |
| normal_size | Risk score LOW or MODERATE |
| increase_size | Risk score VERY_LOW |
| hedging_required | Overall exposure HIGH or EXTREME |

### Evidence Generation

Each analysis produces a single `Evidence` object:
- **Category**: `RISK` (existing `EvidenceCategory`)
- **Source**: `RiskEngine`
- **Signal**: Determined from decision context
- **Score**: Inverse of risk score (100 − risk)
- **Confidence**: Based on decision certainty

### Explanation

Structured `RiskExplanation` with six sections covering all planning
dimensions and an overall risk assessment.

## Alternatives Considered

### Alternative A: Single monolithic risk calculator

A single class that computes all risk parameters inline.

**Rejected** because: Would violate separation of concerns, make testing
difficult, and prevent independent evolution of sizing, stop loss,
target, allocation, and exposure logic. Each dimension has distinct
inputs, outputs, and test requirements.

### Alternative B: Plugin-based architecture

Allow external plugins to contribute custom risk models.

**Rejected** because: Premature abstraction. The five sub-engines already
provide clean extension points. Plugin support can be added later
without redesign via the engine interfaces.

### Alternative C: Broker-aware margin calculations

Integrate broker margin APIs directly into the risk engine.

**Rejected** because: This would couple the engine to specific brokers,
violating the core principle that risk planning is broker-independent.
Margin API integration belongs in a separate adaptor layer.

## Consequences

### Positive

1. Complete institutional risk plan from a single engine.
2. Five independent, testable sub-engines with clear responsibilities.
3. Four risk profiles covering conservative to institutional use cases.
4. Risk score with bands enables intuitive risk communication.
5. Decision context provides actionable sizing guidance.
6. Evidence generation feeds the Intelligence Fusion Engine.
7. Graceful degradation when intelligence modules are unavailable.
8. Zero broker dependencies — pure risk planning.
9. Frozen dataclasses throughout — no mutation, clear contracts.
10. Architecture supports future enhancements (ATR sizing, Kelly,
    portfolio margin, Monte Carlo) without redesign.

### Negative

1. Adds a new `titan/risk/` package with eight modules.
2. Position sizing requires entry price — unavailable in pure
   qualification-only flows.
3. ATR estimation from IV is a rough proxy until realised ATR is
   integrated.

### Neutral

1. Risk profiles are currently hard-coded; configurable profiles can
   be added later.
2. The engine does not validate current portfolio holdings beyond
   what is passed via `current_positions`.

## Future Evolution

### Short Term

- ATR-based position sizing using realised ATR from market data.
- Kelly Criterion and Fractional Kelly integration.
- Dynamic leverage scaling with volatility regime.
- Configurable risk profiles from external configuration.

### Medium Term

- Portfolio margin and SPAN margin estimation.
- Broker margin API integration via adaptor layer.
- Volatility targeting with automated position scaling.
- Position correlation and cross-asset concentration checks.

### Long Term

- Monte Carlo simulation for risk distribution overlays.
- Machine learning-driven risk scoring.
- Real-time risk re-evaluation on intelligence updates.
- Backtesting framework for risk parameter optimisation.

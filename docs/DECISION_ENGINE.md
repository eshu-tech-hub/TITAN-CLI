# Decision Engine

## Overview

The Decision Engine is the final decision-making layer in the TITAN pipeline. It consumes completed intelligence, qualification, and risk outputs to produce a complete institutional trade plan.

It performs **no** market analysis, **no** indicator calculations, and **no** broker execution. It is a pure orchestration and decision layer.

Its sole responsibility is to answer: *"What should we do with this qualified, risk-planned opportunity?"*

## Architecture

```
DecisionInput (TradeQualification + RiskAnalysis + Intelligence)
         │
         ▼
DecisionEngine
         │
         ├── DecisionValidationEngine  ──  Rejection checks, constraint enforcement
         ├── DecisionRankingEngine     ──  Opportunity ranking (BEST → REJECT)
         └── DecisionSelectionEngine   ──  Final action, instrument, plan
         │
         ▼
TradeDecision
```

## Inputs

The engine accepts a `DecisionInput` containing:

| Input | Type | Required |
|-------|------|----------|
| Trade Qualification | `TradeQualification` | Yes |
| Risk Analysis | `RiskAnalysis` | Yes |
| Market Regime | `MarketRegimeAnalysis` | No |
| Option Chain | `OptionChainAnalysis` | No |
| Greeks | `GreeksAnalysis` | No |
| Liquidity | `LiquidityAnalysis` | No |
| Volatility | `VolatilityAnalysis` | No |
| Dealer Positioning | `DealerPositioningAnalysis` | No |
| Gamma Exposure | `GammaExposureAnalysis` | No |
| Vanna Exposure | `VannaExposureAnalysis` | No |
| Charm Exposure | `CharmExposureAnalysis` | No |
| Event Analysis | `EventAnalysis` | No |
| News Analysis | `NewsAnalysis` | No |
| Intelligence Fusion | `IntelligenceFusion` | No |
| Underlying Price | `float` | No |
| Symbol | `str` | No |

## Output

`TradeDecision` contains:

| Field | Type | Description |
|-------|------|-------------|
| `decision` | `DecisionAction` | BUY, SELL, NO_TRADE, WATCHLIST, WAIT |
| `trade_direction` | `TradeDirection` | LONG, SHORT, OPTION_BUYING, OPTION_SELLING |
| `instrument_type` | `InstrumentType` | UNDERLYING, FUTURES, CALL_OPTION, PUT_OPTION |
| `symbol` | `str` | Instrument symbol |
| `expiry` | `str \| None` | Option expiry date |
| `strike` | `float \| None` | Option strike price |
| `entry_strategy` | `str` | Entry approach description |
| `stop_loss_reference` | `float` | Recommended stop loss price |
| `target_reference` | `float` | Recommended take-profit target (T1) |
| `holding_style` | `HoldingStyle` | SCALP, DAY_TRADE, SWING, POSITION |
| `rank` | `DecisionRank` | BEST, GOOD, ACCEPTABLE, REJECT |
| `confidence` | `float` | Overall confidence (0.0–1.0) |
| `probability` | `float` | Estimated success probability (0.0–1.0) |
| `trade_score` | `float` | Normalised trade quality (0–100) |
| `institutional_grade` | `bool` | Meets institutional grade |
| `evidence` | `Evidence \| None` | Evidence for Intelligence Fusion |
| `explanation` | `DecisionExplanation \| None` | Structured explanation |
| `warnings` | `tuple[str, ...]` | Non-fatal warnings |
| `metadata` | `Mapping[str, Any]` | Producer context |
| `timestamp` | `datetime` | Computation timestamp |

## Decision Flow

### 1. Validation (`DecisionValidationEngine`)

Checks that execute before any selection logic:

- **Risk rejection**: If `risk_analysis.decision_context.avoid_trade` is True, the trade is rejected.
- **Qualification rejection**: If `trade_qualification.status` is REJECTED, the trade is rejected.
- **Conflicting intelligence**: If the Intelligence Fusion engine reports conflicts, the trade is flagged.
- **Insufficient confidence**: If `trade_qualification.confidence` falls below 0.3, the trade is rejected.
- **Extreme event risk**: If the risk score band is EXTREME and event risk is EXTREME, the trade is rejected.

### 2. Ranking (`DecisionRankingEngine`)

The opportunity is scored from 0–100 using four weighted components:

| Component | Weight | Source |
|-----------|--------|--------|
| Trade Quality | 40% | Trade score band (EXCELLENT → REJECT) |
| Risk Alignment | 25% | Risk score band (VERY_LOW → EXTREME) |
| Bias Alignment | 20% | Fusion signal, option chain, greeks, dealer bias |
| Confidence | 15% | Average of qualification, risk, and fusion confidence |

**Rank boundaries:**

| Score Range | Rank |
|-------------|------|
| ≥ 80 | BEST |
| ≥ 60 | GOOD |
| ≥ 40 | ACCEPTABLE |
| < 40 | REJECT |

### 3. Selection (`DecisionSelectionEngine`)

Determines the final action:

- **WATCHLIST/WAIT** status → Respects qualification status over directional bias.
- **BUY**: Long qualified, no short qualification.
- **SELL**: Short qualified, no long qualification.
- **Both directions**: Uses volatility bias to disambiguate.
- **NO_TRADE**: Any validation failure, REJECT rank, or extreme risk band.

**Instrument type**: Determined from option availability and volatility regime:
- Compression + Bullish volatility → CALL_OPTION
- Compression + Bearish volatility → PUT_OPTION
- Positive gamma + Bullish bias → CALL_OPTION
- Negative gamma + Bearish bias → PUT_OPTION
- Default → UNDERLYING

**Holding style**: Determined from volatility regime:
- EXPANSION/TRANSITION → DAY_TRADE
- COMPRESSION → SWING
- High/Extreme event risk → DAY_TRADE

## Usage

```python
from titan.decision import DecisionEngine, DecisionInput
from titan.risk import RiskEngine, RiskInput, RiskProfile
from titan.events.models import EventRisk
from titan.trading.models import TradeQualification, TradeScore, ScoreBand, TradeStatus

# Build inputs from upstream engines
tq = TradeQualification(
    status=TradeStatus.QUALIFIED,
    trade_score=TradeScore(value=85.0, band=ScoreBand.GOOD),
    confidence=0.8,
    decision_context="Bullish breakout on NIFTY",
    long_qualification=True,
    short_qualification=False,
    institutional_alignment=True,
)

risk = RiskEngine().analyze(
    risk_input=RiskInput(trade_qualification=tq),
    risk_profile=RiskProfile.INSTITUTIONAL,
)

decision_input = DecisionInput(
    trade_qualification=tq,
    risk_analysis=risk,
    symbol="NIFTY",
)

# Execute decision pipeline
engine = DecisionEngine()
result = engine.decide(decision_input=decision_input)

print(f"Decision: {result.decision.value.upper()}")
print(f"Rank: {result.rank.value}")
print(f"Direction: {result.trade_direction.value}")
print(f"Instrument: {result.instrument_type.value}")
print(f"Confidence: {result.confidence:.1%}")
print(f"Trade Score: {result.trade_score:.0f}/100")
```

## Decision Explanation

Every `TradeDecision` includes a `DecisionExplanation` with six sections:

| Section | Description |
|---------|-------------|
| `decision_summary` | One-line summary of the decision |
| `supporting_intelligence` | Key intelligence inputs |
| `risk_summary` | Risk factors affecting the decision |
| `why_this_trade` | Rationale for the selected trade |
| `why_alternatives_rejected` | Rationale for rejected alternatives |
| `execution_guidance` | Entry, stop, and target guidance |

## Dependencies

**Runtime:** Trade Qualification Engine, Risk Intelligence Engine, and upstream intelligence modules.

**Test:** pytest.

Zero broker dependencies. Zero API calls. Pure orchestration.

## Future Enhancements

### Short Term
- Multi-symbol ranking across candidate instruments
- AI ensemble voting for decision consensus
- Probability calibration against historical outcomes

### Medium Term
- Portfolio-aware decisions (net exposure, cross-correlation)
- Reinforcement learning overlays for entry timing
- Dynamic holding style from market microstructure

### Long Term
- Automated multi-leg strategy selection
- Decision backtesting framework
- Real-time decision re-evaluation on market data updates

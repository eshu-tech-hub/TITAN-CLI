# Trade Qualification Engine

## Overview

The Trade Qualification Engine determines whether a trading opportunity
deserves consideration by consuming ALL completed intelligence modules.

It does **not** calculate indicators, Greeks, or raw candles.
It does **not** produce entry prices, stop losses, targets, strikes,
or CE/PE recommendations.

Its sole responsibility is to answer: *"Is this trade qualified?"*

## Architecture

```
TradeQualificationInput
        │
        ▼
TradeQualificationEngine
        │
        ├── TradeFilterEngine      ──  Hard reject/accept filters
        ├── ConfirmationEngine     ──  Cross-source agreement check
        └── TradeScoringEngine     ──  0–100 normalised score
        │
        ▼
TradeQualification
```

## Inputs

The engine accepts a `TradeQualificationInput` containing all
intelligence module outputs. All fields are optional:

| Module | Type |
|--------|------|
| Market Regime | `MarketRegimeAnalysis` |
| Option Chain | `OptionChainAnalysis` |
| Greeks | `GreeksAnalysis` |
| Liquidity | `LiquidityAnalysis` |
| Volatility | `VolatilityAnalysis` |
| Dealer Positioning | `DealerPositioningAnalysis` |
| Gamma Exposure | `GammaExposureAnalysis` |
| Vanna Exposure | `VannaExposureAnalysis` |
| Charm Exposure | `CharmExposureAnalysis` |
| Event Analysis | `EventAnalysis` |
| News Analysis | `NewsAnalysis` |
| Intelligence Fusion | `IntelligenceFusion` |

## Output

`TradeQualification` contains:

| Field | Description |
|-------|-------------|
| `status` | QUALIFIED, REJECTED, WATCHLIST, WAIT |
| `trade_score` | 0–100 score with band (EXCELLENT/GOOD/AVERAGE/WEAK/REJECT) |
| `confidence` | 0.0–1.0 overall confidence |
| `decision_context` | Summary string |
| `passed_filters` | Reasons for passed filters |
| `failed_filters` | Reasons for failed filters |
| `confirmations` | Per-source confirmation results |
| `long_qualification` | Whether long trades are qualified |
| `short_qualification` | Whether short trades are qualified |
| `option_buying_qualification` | Whether option buying is qualified |
| `option_selling_qualification` | Whether option selling is qualified |
| `institutional_alignment` | Whether institutional signals align |
| `evidence` | Evidence for Intelligence Fusion Engine |
| `explanation` | Structured human-readable explanation |
| `warnings` | Non-fatal warnings |
| `metadata` | Producer context |

## Hard Filters

Any single filter failure → REJECTED:

1. **High Event Risk** — Extreme event risk or avoid-new-positions.
2. **Extreme Liquidity Risk** — Execution grade F or UNKNOWN.
3. **Low Confidence** — Average confidence < 0.2.
4. **Conflicting Intelligence** — Fusion engine detected conflicts.
5. **Insufficient Evidence** — < 3 modules available.
6. **Unknown Market Regime** — Regime is UNKNOWN.

## Confirmation Sources

Each source produces a `ConfirmationResult` with `confirmed: bool`,
`score: float`, and `confidence: float`:

| Source | Check |
|--------|-------|
| MARKET | `DecisionContext.favorable_for_{direction}` |
| OPTIONS | `OptionChainAnalysis.overall_bias` aligns with direction |
| DEALER | `DealerPositioningAnalysis.dealer_bias` aligns with direction |
| VOLATILITY | `overall_bias` or `buying_bias`/`selling_bias` aligns |
| NEWS | `MarketReactionResult.reaction` aligns with direction |
| EVENTS | `DecisionContext` does not block positioning |
| EVIDENCE | `IntelligenceFusion.overall_signal` aligns with direction |
| FUSION | `IntelligenceFusion` overall score and signal align |

## Trade Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Base Score | 100% | Agreement ratio (40%) + average confirmation score (60%) |
| Confidence Adj | ±10 | Average confidence relative to 0.5 midpoint |
| Institutional Adj | +0–15 | Market, dealer, and fusion alignment bonus |
| Warning Penalty | −0–30 | Penalty per module warning |

## Status Determination

```
Score ≥ 60 AND confirmations ≥ 4  →  QUALIFIED
Score ≥ 20                        →  WATCHLIST
Score < 20                        →  WAIT
Any hard filter failure           →  REJECTED
```

## Usage

```python
from titan.trading import TradeQualificationEngine, TradeQualificationInput

engine = TradeQualificationEngine()
inputs = TradeQualificationInput(
    market_regime=regime_analysis,
    option_chain=chain_analysis,
    dealer_positioning=dealer_analysis,
    volatility=vol_analysis,
    event_analysis=event_analysis,
    news_analysis=news_analysis,
    intelligence_fusion=fusion_result,
)
result = engine.qualify(inputs)

if result.status == "qualified":
    print(f"Score: {result.trade_score.value:.0f} ({result.trade_score.band.value})")
    print(f"Long: {result.long_qualification}")
    print(f"Short: {result.short_qualification}")
```

## Testing

Run the trade qualification test suite:

```bash
pytest tests/test_trade_qualification.py -v
```

Test scenarios:
- Qualified trade (all positive signals)
- Rejected trade (each hard filter independently)
- Watchlist (partial confirmations, score ≥ 20)
- Wait (low score, score < 20)
- Evidence generation
- Explanation generation
- Serialisation round-trip
- Direction qualification (long, short, option buying, option selling)
- Graceful degradation with missing modules

## Dependencies

**Runtime:** None beyond the intelligence modules it consumes.

**Test:** pytest.

The engine has zero broker dependencies and zero API call requirements.

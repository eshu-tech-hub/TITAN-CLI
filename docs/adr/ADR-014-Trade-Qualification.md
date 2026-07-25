# ADR-014: Trade Qualification Engine

**Status:** Accepted (Milestone M4.2.1)

**Date:** 2026-07-03

**Author:** TITAN Architecture Team

## Context

The TITAN platform produces extensive intelligence across market regime,
option chain, Greeks, liquidity, volatility, dealer positioning, gamma
exposure, vanna exposure, charm exposure, events, news, evidence
aggregation, and intelligence fusion. Each module operates independently
and produces structured, evidence-backed output.

What has been missing is a unified decision point that consumes ALL
completed intelligence and determines whether a trading opportunity
deserves further consideration.

Without this engine, the platform produces raw intelligence but no
actionable qualification signal. Each consumer must independently
interpret the full intelligence surface — a process that is error-prone,
inconsistent, and difficult to audit.

The Trade Qualification Engine exists to solve this problem. It is the
final gate before trade consideration. It does NOT calculate indicators,
Greeks, or raw candles. It does NOT produce entry prices, stop losses,
targets, strikes, or CE/PE recommendations. Its sole responsibility is
to determine whether a trade deserves consideration.

## Decision

We introduce a `titan/trading/` package containing a
`TradeQualificationEngine` that orchestrates three sub-engines:

1. **TradeFilterEngine** — Evaluates hard reject filters.
2. **ConfirmationEngine** — Checks configurable agreement across
   intelligence sources.
3. **TradeScoringEngine** — Produces a normalised 0–100 trade score.

### Package Structure

```
titan/trading/
    __init__.py          # Public API exports
    models.py            # Frozen dataclasses and enums
    exceptions.py        # Domain exceptions
    filters.py           # TradeFilterEngine + hard filter logic
    confirmation.py      # ConfirmationEngine + per-source checks
    scoring.py           # TradeScoringEngine + score bands
    qualification.py     # TradeQualificationEngine (orchestrator)
```

### Trade Qualification Input

The engine accepts a single `TradeQualificationInput` frozen dataclass
that aggregates all intelligence module outputs. Every field is optional
— missing components degrade gracefully:

- MarketRegimeAnalysis
- OptionChainAnalysis
- GreeksAnalysis
- LiquidityAnalysis
- VolatilityAnalysis
- DealerPositioningAnalysis
- GammaExposureAnalysis
- VannaExposureAnalysis
- CharmExposureAnalysis
- EventAnalysis
- NewsAnalysis
- IntelligenceFusion

### Hard Filters

Any single hard filter failure immediately disqualifies the trade
(status: REJECTED):

1. **High Event Risk** — EventAnalysis.overall_risk == EXTREME or
   decision context recommends avoiding new positions.
2. **Extreme Liquidity Risk** — Execution grade is F or UNKNOWN.
3. **Low Confidence** — Weighted average confidence across available
   modules is below 0.2.
4. **Conflicting Intelligence** — IntelligenceFusion has detected
   conflicting evidence.
5. **Insufficient Evidence** — Fewer than 3 intelligence modules are
   available.
6. **Unknown Market Regime** — Market regime classification is UNKNOWN.

### Confirmation Rules

The ConfirmationEngine checks agreement across eight sources for a
given trade direction (LONG, SHORT, OPTION_BUYING, OPTION_SELLING):

- **Market**: DecisionContext.favorable_for_{direction}
- **Options**: OptionChainAnalysis.overall_bias alignment
- **Dealer**: DealerPositioningAnalysis.dealer_bias alignment
- **Volatility**: VolatilityAnalysis.overall_bias / buying_bias / selling_bias
- **News**: MarketReactionResult.reaction alignment
- **Events**: DecisionContext allows positioning
- **Evidence**: IntelligenceFusion.overall_signal alignment
- **Fusion**: IntelligenceFusion overall score and signal alignment

### Trade Score Bands

| Band       | Range |
|------------|-------|
| EXCELLENT  | ≥ 80  |
| GOOD       | ≥ 60  |
| AVERAGE    | ≥ 40  |
| WEAK       | ≥ 20  |
| REJECT     | < 20  |

### Qualification Status

| Status     | Meaning |
|------------|---------|
| QUALIFIED  | Passed all filters, score ≥ 60, sufficient confirmations |
| REJECTED   | Failed one or more hard filters |
| WATCHLIST  | Passed filters, score ≥ 20, but insufficient confirmations |
| WAIT       | Passed filters, score < 20, insufficient evidence |

### Evidence Generation

Each qualification run produces a single `Evidence` object with:
- **Category**: `TRADE_QUALIFICATION` (added to `EvidenceCategory` enum)
- **Source**: `TradeQualificationEngine`
- **Signal**: Derived from score and status
- **Score**: Normalised trade score
- **Confidence**: Confirmation ratio (confirmed / total sources)

### Explanation

The output includes a structured `TradeQualificationExplanation` with
six sections: Overall Qualification, Confirmations, Rejections, Risk
Factors, Institutional Alignment, and Final Assessment.

## Alternatives Considered

### Alternative A: Rule-based classifier in a single file

A single engine class with inline filter and scoring logic.

**Rejected** because: It would violate separation of concerns, make
testing difficult, and prevent independent evolution of filters,
confirmation rules, and scoring algorithms.

### Alternative B: Plugin-based architecture with dynamic loading

Allow external plugins to contribute custom filters and scoring rules.

**Rejected** because: Premature abstraction. The current requirements
are well-understood and stable. Plugin support can be added later
without redesign because the three sub-engines already provide clean
extension points.

### Alternative C: Market-data-aware engine

Allow the engine to access raw candles or Greeks directly.

**Rejected** because: This would violate the core architectural
principle that the Trade Qualification Engine consumes completed
intelligence only. Raw data access would couple the engine to market
data sources, prevent testing without data, and create duplicate
calculations.

## Consequences

### Positive

1. Single, auditable decision point for trade qualification.
2. All intelligence modules are consumed — no missing signals.
3. Clean separation: filters, confirmation, and scoring are independent.
4. Direction-aware qualification (long, short, option buying, option selling).
5. Graceful degradation when intelligence modules are unavailable.
6. Evidence generation for downstream fusion and audit trails.
7. All models are frozen dataclasses — no mutation, clear contracts.
8. Zero broker or API dependencies — pure orchestration.

### Negative

1. Adds a new `titan/trading/` package and `TRADE_QUALIFICATION` evidence category.
2. Confirmation source weights are hard-coded in the scoring engine.
3. Qualification produces additional evidence that must be fused upstream.

### Neutral

1. The engine introduces the concept of "trade direction" to the
   qualification process, which is new to the platform.
2. The minimum evidence threshold (3 modules) is a sensible default
   but may need tuning.

## Future Evolution

### Short Term

- Add configurable confirmation source weights.
- Support strategy-specific qualification thresholds.
- Add portfolio-aware filtering (correlation, concentration limits).

### Medium Term

- Add AI ranking overlay that scores qualification candidates.
- Add probability model integration for expected value qualification.
- Add historical validation pass to track qualification accuracy.

### Long Term

- Machine learning overlay for filter and scoring optimisation.
- Real-time re-qualification on intelligence updates.
- Backtesting framework for qualification rule tuning.

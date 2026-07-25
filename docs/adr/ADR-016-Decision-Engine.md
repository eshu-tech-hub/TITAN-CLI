# ADR-016: Decision Engine

**Status:** Accepted (Milestone M4.2.3)

**Date:** 2026-07-03

**Author:** TITAN Architecture Team

## Context

The TITAN platform now produces trade qualification outputs (ADR-014) and
comprehensive risk intelligence plans (ADR-015). What has been missing is
a final decision-making layer that consumes all upstream intelligence to
answer the single question: *"What should we do?"*

Without this engine, each consumer must independently interpret risk
analysis, reconcile intelligence signals, determine instrument selection,
estimate confidence and probability, and assess institutional grade — a
fragmented process that produces inconsistent decisions and prevents
systematic trade planning.

The Decision Engine exists to solve this problem. It is the final
orchestration stage before the Broker Layer. It does NOT execute trades,
call broker APIs, perform market analysis, or calculate indicators. Its
sole responsibility is to produce a complete, institutional-grade trade
decision that can be executed by downstream systems.

## Decision

We introduce a `titan/decision/` package containing a `DecisionEngine`
that orchestrates three sub-engines:

1. **DecisionValidationEngine** — Enforces hard rejection rules: risk
   engine avoidance, qualification rejection, conflicting intelligence,
   insufficient confidence, and extreme event risk.
2. **DecisionRankingEngine** — Scores and ranks the opportunity
   (BEST / GOOD / ACCEPTABLE / REJECT) using weighted trade quality,
   risk alignment, bias alignment, and confidence metrics.
3. **DecisionSelectionEngine** — Produces the final `TradeDecision`
   with action, instrument type, direction, holding style, entry
   strategy, stop/target references, confidence, probability,
   institutional grade, evidence, and structured explanation.

### Package Structure

```
titan/decision/
    __init__.py       # Public API exports
    models.py         # Frozen dataclasses and enums (TradeDecision,
                      #   DecisionInput, DecisionExplanation, enums)
    exceptions.py     # Domain exceptions
    validation.py     # DecisionValidationEngine
    ranking.py        # DecisionRankingEngine
    selection.py      # DecisionSelectionEngine
    decision.py       # DecisionEngine orchestrator
```

### Data Flow

```
Qualification ──┐
Risk Analysis ──┤
Intelligence   ──┤──► DecisionInput ──► DecisionEngine ──► TradeDecision
Fusion        ──┘
```

### Action Determination

The selection engine determines the final action through a priority
order:

1. **Validation failures** → NO_TRADE (or WATCHLIST/WAIT if the
   qualification status so indicates).
2. **REJECT rank** → NO_TRADE.
3. **ACCEPTABLE rank + HIGH risk** → WATCHLIST.
4. **ACCEPTABLE rank + EXTREME risk** → NO_TRADE.
5. **Qualification status** → WATCHLIST or WAIT when status matches.
6. **Directional qualification** → BUY if long-qualified, SELL if
   short-qualified, volatility bias used to disambiguate when both
   are qualified.
7. **Fallback** → BUY for qualified status, NO_TRADE otherwise.

### Instrument Selection Priority

1. Options are selected when volatility or gamma data indicates
   favourable conditions AND option buying is qualified.
2. Compression + Bullish → CALL_OPTION.
3. Compression + Bearish → PUT_OPTION.
4. Positive gamma + Bullish → CALL_OPTION.
5. Negative gamma + Bearish → PUT_OPTION.
6. Fallback → UNDERLYING.

### Ranking Formula

```
rank_score = quality * 0.40 + risk_alignment * 0.25
           + bias_alignment * 0.20 + confidence * 0.15
```

Where:
- **quality** (0–100): Derived from the trade score band
  (EXCELLENT=100, GOOD=75, AVERAGE=50, WEAK=25, REJECT=0).
- **risk_alignment** (0–100): Inverse of risk score band
  (VERY_LOW=100, LOW=80, MODERATE=60, HIGH=30, EXTREME=0).
- **bias_alignment** (0–100): Average of directional signals from
  fusion, option chain, greeks, and dealer positioning.
- **confidence** (0–100): Average of qualification confidence, risk
  assessment confidence, and fusion confidence.

### Ranking Thresholds

| Score Range | Rank |
|-------------|------|
| 80–100 | BEST |
| 60–79 | GOOD |
| 40–59 | ACCEPTABLE |
| 0–39 | REJECT |

### Evidence Generation

The engine produces a single `Evidence` object with:
- `source`: "DecisionEngine"
- `category`: `TRADE_QUALIFICATION`
- `signal`: BULLISH for BUY, BEARISH for SELL, NEUTRAL for others
- `score`: From the trade qualification score
- `confidence`: From the computed decision confidence

### Explanation Structure

`DecisionExplanation` contains six sections:
- `decision_summary`: One-line summary
- `supporting_intelligence`: Market regime, volatility, fusion signal
- `risk_summary`: Risk score and hedging requirements
- `why_this_trade`: Rationale for the selected action
- `why_alternatives_rejected`: Alternative rationale
- `execution_guidance`: Entry strategy, stop loss, and targets

## Alternatives Considered

### Monolithic Decision Function

A single function that combines validation, ranking, and selection logic.

- *Rejected due to:* Poor separation of concerns, difficult to test
  independently, hard to extend with new validation rules or ranking
  signals.

### Plugin-Based Decision Architecture

Each decision sub-component as a pluggable module registered at startup.

- *Rejected due to:* Over-engineered for current requirements. Plugins
  add configuration surface without immediate benefit. Can be introduced
  when multi-symbol ranking or AI ensemble voting is added.

### External Decision Service

A separate microservice that consumes TITAN outputs and produces
decisions.

- *Rejected due to:* Premature distribution. The decision layer has no
  external dependencies and benefits from in-process execution speed.
  A service boundary can be introduced later if needed.

## Consequences

### Positive

1. Single, authoritative decision layer for the entire TITAN platform.
2. Hard rejection rules ensure capital preservation before any
   selection logic runs.
3. Ranking is independent of validation — an opportunity can be highly
   ranked but still rejected, preserving signal for analytics.
4. Evidence generation feeds the Intelligence Fusion Engine for
   cross-pipeline traceability.
5. Structured explanation provides full transparency into the decision.
6. Instrument selection and holding style are data-driven from
   intelligence inputs.
7. Institutional grade flag enables compliance and audit workflows.
8. Future-ready for multi-symbol ranking without architecture changes.
9. Frozen dataclasses throughout — no mutation, clear contracts.

### Negative

1. Adds a new `titan/decision/` package with seven modules.
2. Currently single-symbol only — multi-symbol ranking requires
   batch processing on the caller side.
3. Probability estimation is a simple blend of confidence and trade
   score — calibrated probability requires historical backtesting.

### Neutral

1. Decision action thresholds (confidence 0.3, rank boundaries) are
   hard-coded; configurable thresholds can be added later.
2. Instrument selection does not yet support FUTURES.
3. `_determine_instrument` uses gamma regime and volatility bias as
   proxies until full options surface analysis is integrated.

## Future Evolution

### Short Term

- Multi-symbol ranking across candidate instruments.
- AI ensemble voting for decision consensus.
- Probability calibration against historical outcomes.
- Configurable validation thresholds from external configuration.

### Medium Term

- Portfolio-aware decisions (net exposure, cross-correlation checks).
- Reinforcement learning overlays for entry timing optimisation.
- Dynamic holding style from market microstructure analysis.
- Support for multi-leg strategy decisions (spreads, collars, etc.).

### Long Term

- Automated strategy selection from opportunity characteristics.
- Decision backtesting framework for parameter optimisation.
- Real-time decision re-evaluation on streaming intelligence updates.
- Integration with execution management for fill-aware decisions.

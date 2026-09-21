# Option Analytics Foundation

## Architecture

The option analytics foundation is a broker-independent domain layer. Every
analyzer consumes only `OptionChainSnapshot` and returns `AnalysisResult`.

Broker adapters, API clients, and raw option-chain vendors must normalize data
before it reaches this package. This keeps option analytics reusable across
YFinance, other brokers, historical backtests, simulations, and offline
research.

## Responsibilities

- `OptionAnalyzer`: abstract contract for all option analytics.
- `OptionChainSnapshot`: normalized option-chain input model.
- `OptionStrikeSnapshot`: normalized strike-level input model.
- `AnalysisResult`: common result model for every analyzer.
- `OpenInterestAnalyzer`: open-interest structure and support/resistance context.
- `PCRAnalyzer`: put-call ratio analysis.
- `SupportResistanceAnalyzer`: support and resistance from highest Put/Call OI.
- `OptionChainAnalyzer`: coordinator that aggregates analyzer output into
  `OptionChainAnalysis`, `Evidence`, and `OptionChainExplanation`.
- `MaxPainAnalyzer`: placeholder for max-pain analysis.
- `BuildUpAnalyzer`: placeholder for long and short buildup detection.
- `WritingAnalyzer`: placeholder for option writing pressure.
- `LiquidityAnalyzer`: placeholder for liquidity quality checks.
- `StrikeRankAnalyzer`: placeholder for ranking important strikes.
- `SentimentAnalyzer`: placeholder for aggregate option-chain sentiment.

## Class Diagram

```text
+-------------------+       +----------------------+
| OptionAnalyzer    |<------| Concrete Analyzers   |
|-------------------|       |----------------------|
| +analyze(snapshot)|       | OI, PCR, MaxPain, ...|
+---------+---------+       +----------+-----------+
          |                            |
          v                            v
+-------------------+       +----------------------+
| OptionChainSnapshot|----->| AnalysisResult       |
|-------------------|       |----------------------|
| underlying        |       | score/confidence     |
| expiry/timestamp  |       | bullish/bearish/...  |
| strikes           |       | reasons/warnings     |
+---------+---------+       +----------------------+
          |
          v
+-------------------+
| OptionStrikeSnapshot|
|-------------------|
| strike price      |
| OI/volume/price   |
+-------------------+
```

## Option Chain Intelligence

`OptionChainAnalyzer` coordinates the production analyzers for M2.1.5:

- `PCRAnalyzer`
- `SupportResistanceAnalyzer`
- `OpenInterestAnalyzer`

The coordinator does not calculate raw market metrics itself. It delegates
calculation and interpretation to analyzers, converts each `AnalysisResult` into
universal `Evidence`, aggregates evidence through `EvidenceAggregator`, and
returns `OptionChainAnalysis`.

`OptionChainAnalysis` includes:

- overall bias and confidence
- support and resistance
- PCR
- highest Put and Call OI strikes
- bullish, bearish, and neutral scores
- warnings
- evidence tuple
- structured explanation

`OptionChainExplanation` contains a concise summary, evidence-backed key
points, and warnings. This keeps the path explicit:

```text
OptionChainSnapshot
        |
        v
Independent Analyzers
        |
        v
AnalysisResult
        |
        v
Evidence
        |
        v
OptionChainAnalysis + OptionChainExplanation
```

## Future Calculations

This milestone intentionally avoids production formulas. Future milestones can
add:

- PCR thresholds and trend-sensitive interpretation.
- Open-interest concentration and change analysis.
- Max-pain calculation using strike-level payoff estimates.
- Long buildup, short buildup, short covering, and long unwinding detection.
- Call and put writing pressure by strike and expiry.
- Liquidity scoring using volume, spread, and open-interest quality.
- Strike ranking for support, resistance, and magnet levels.
- Aggregate sentiment from weighted analyzer outputs.

## Boundary Rule

This package must not import broker packages, yfinance, YFinance modules, or
make API calls. It only operates on normalized `OptionChainSnapshot` data.


## TUI Integration

The Market Intelligence Screen in the TITAN TUI provides a read-only operational dashboard visualizing the output of this engine/component. No business logic or analytics are executed in the presentation layer.

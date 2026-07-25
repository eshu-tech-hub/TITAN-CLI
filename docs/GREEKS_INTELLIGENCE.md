# Greeks Intelligence Engine

## Status

M2.1.6 implements broker-independent Greeks Intelligence.

The engine consumes Greeks only when they are supplied by normalized upstream
data. It does not implement Black-Scholes, estimate missing Greeks, or call any
broker API.

## Inputs

`OptionStrikeSnapshot` supports optional call and put values for:

- delta
- gamma
- theta
- vega
- rho
- implied volatility

All values may be `None`. Missing values are treated as unavailable evidence,
not as zero.

## Components

`GreeksAnalyzer` coordinates:

- `DeltaAnalyzer`
- `GammaAnalyzer`
- `ThetaAnalyzer`
- `VegaAnalyzer`

Each analyzer returns `AnalysisResult`, can convert that result into universal
`Evidence`, and generates explanation text from structured values.

The coordinator returns `GreeksAnalysis` with aggregate evidence and a
structured `GreeksExplanation`.

## Institutional Interpretation

### Delta

Delta measures directional sensitivity to the underlying. TITAN calculates:

- net delta
- average delta
- ATM delta when `underlying_price` is supplied
- directional exposure

Positive net delta is interpreted as bullish directional exposure. Negative net
delta is interpreted as bearish directional exposure. Near-zero net delta is
neutral.

### Gamma

Gamma measures convexity and the rate of change in delta. TITAN calculates:

- net gamma
- average gamma
- gamma concentration by strike

High concentration warns that sensitivity is clustered around a limited area of
the chain. The current implementation prepares metadata fields for future GEX
and dealer gamma, but does not calculate them.

### Theta

Theta measures time-decay sensitivity. TITAN calculates:

- net theta
- average theta
- time decay risk
- near-expiry warning

Negative net theta can indicate elevated decay risk. Near expiry is warned
separately because time decay can accelerate into expiry.

### Vega

Vega measures volatility sensitivity. TITAN calculates:

- net vega
- average vega
- volatility sensitivity
- high vega risk
- low vega opportunity

High absolute vega warns that the chain is sensitive to implied volatility
changes. Low average vega is marked as a possible low-vega opportunity state,
not a trade recommendation.

## Evidence

Aggregate Greeks evidence uses:

- source: `Greeks`
- category: `OPTION_CHAIN`
- signal: derived from weighted component evidence
- score: weighted by `EvidenceAggregator`
- confidence: weighted by `EvidenceAggregator`
- reasons: generated from component analyzer reasons
- warnings: generated from missing data and risk conditions

## Explanation

`GreeksExplanation` contains five sections:

- Delta
- Gamma
- Theta
- Vega
- Overall

Every section is generated from structured analyzer output. Conclusions are not
hardcoded.

## Current Limitations

The current engine does not calculate:

- Black-Scholes Greeks
- gamma exposure
- dealer positioning
- volatility surface
- volatility smile
- volatility skew
- charm
- vanna
- vomma

These are future-compatible extension points, not M2.1.6 implementations.

## Boundary Rule

Greeks Intelligence imports no broker packages and makes no API calls. Broker
or data adapters must normalize external data into `OptionChainSnapshot` before
analytics begins.


## TUI Integration

The Market Intelligence Screen in the TITAN TUI provides a read-only operational dashboard visualizing the output of this engine/component. No business logic or analytics are executed in the presentation layer.

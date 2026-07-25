# Liquidity Intelligence Engine

## Status

M2.1.7 implements broker-independent Liquidity Intelligence for one option
contract.

The engine evaluates execution quality only. It does not decide whether to
trade, size a position, route an order, connect to a broker, or consume a live
order book.

## Inputs

`OptionLiquiditySnapshot` supports optional values for:

- bid_price
- ask_price
- bid_quantity
- ask_quantity
- last_traded_price
- volume
- open_interest

All values may be `None`. Missing values reduce confidence and generate
warnings. Missing values are not interpreted as zero liquidity.

## Components

`LiquidityAnalyzer` coordinates:

- `SpreadAnalyzer`
- `DepthAnalyzer`
- `SlippageAnalyzer`
- `ExecutabilityAnalyzer`

Each component is deterministic, typed, and broker-independent.

## Institutional Interpretation

### Spread

Spread analysis calculates:

- bid/ask spread
- spread percentage relative to midpoint
- spread quality

Tight spreads indicate lower immediate crossing cost. Wide spreads indicate
higher execution friction and lower quality. A crossed or incomplete market is
warned rather than repaired.

### Depth

Depth analysis evaluates displayed top-of-book quantity:

- bid size
- ask size
- order book balance
- depth quality

Balanced two-sided displayed size is scored higher than thin or one-sided
depth. This is a top-of-book framework only; it does not infer hidden size.

### Slippage

Slippage analysis estimates expected slippage from:

- half-spread cost
- displayed-depth penalty
- activity penalty from volume and open interest

The estimate is an execution-quality heuristic. It is not a fill simulation and
does not forecast market movement.

### Execution

Executability analysis combines spread, depth, and slippage into:

- execution score
- execution grade
- execution risk

The grade communicates suitability for execution quality only. It is not a
directional trading signal.

## Output

`LiquidityAnalysis` contains:

- spread
- spread_percent
- depth_score
- slippage_score
- execution_score
- execution_grade
- confidence
- warnings
- metadata
- evidence
- explanation

## Evidence

Aggregate liquidity evidence uses:

- source: `Liquidity`
- category: `OPTION_CHAIN`
- signal: derived from weighted execution-quality score
- score: weighted by `EvidenceAggregator`
- confidence: weighted by `EvidenceAggregator`
- warnings: generated from missing or poor-quality liquidity inputs

The evidence signal uses the existing universal evidence contract. In this
module, bullish/bearish labels mean favorable/unfavorable execution quality,
not market direction.

## Explanation

`LiquidityExplanation` contains four sections:

- Spread
- Depth
- Slippage
- Execution

Every section is generated from analyzer outputs and remains available when
confidence is low.

## Current Implementation

The current framework uses only normalized option-contract fields supplied by
upstream data. It performs no network access and imports no broker packages.

Current calculations include:

- top-of-book bid/ask spread
- spread percentage
- displayed bid/ask quantity
- top-of-book balance
- heuristic slippage estimate
- weighted execution score and grade

## Future Enhancements

The architecture reserves metadata and component boundaries for:

- Level-2 market depth
- live order book
- VWAP
- iceberg detection
- hidden liquidity
- broker latency

These are extension points only. M2.1.7 does not implement them.

## Boundary Rule

Broker or data adapters must normalize external data into
`OptionLiquiditySnapshot` before analytics begins. Liquidity Intelligence does
not call broker APIs, subscribe to market data, or place orders.

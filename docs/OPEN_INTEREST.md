# Open Interest Intelligence Engine

## What Open Interest Measures

Open interest is the number of outstanding option contracts at a strike and
expiry. In TITAN, call and put open interest are treated as institutional
positioning clues, not as trade signals by themselves.

High put open interest can identify support zones. High call open interest can
identify resistance zones. Changes in open interest help separate static
positioning from fresh activity, but this milestone keeps change interpretation
conservative until intraday and historical context are added.

## How TITAN Interprets OI

The engine separates three responsibilities:

- calculation of raw option-chain metrics
- interpretation into bias, reasons, warnings, score, and confidence
- conversion into universal `Evidence`

Current interpretation is intentionally conservative:

- stronger put OI biases bullish
- stronger call OI biases bearish
- balanced OI remains neutral
- empty or thin snapshots generate warnings
- support comes from the highest put OI strike
- resistance comes from the highest call OI strike

## Current Implementation

`OpenInterestAnalyzer.analyze(snapshot)` returns `AnalysisResult` with metadata:

- `total_call_oi`
- `total_put_oi`
- `call_oi_change`
- `put_oi_change`
- `highest_call_oi_strike`
- `highest_put_oi_strike`
- `highest_call_change`
- `highest_put_change`
- `support_strike`
- `resistance_strike`
- `market_bias`

`OpenInterestAnalyzer.to_evidence(result)` converts the result to `Evidence`
using:

- source: `Open Interest`
- category: `OPTION_CHAIN`
- signal: derived from market bias
- score: validated by the evidence engine
- confidence: validated by the evidence engine

## Future Enhancements

Future milestones can add without redesign:

- OI change decomposition by strike
- intraday OI trend detection
- historical OI baselines
- dynamic support and resistance scoring
- expiry-aware interpretation
- liquidity-adjusted confidence
- regime-specific thresholds

## Boundary Rule

The Open Interest Intelligence Engine does not import broker code, yfinance, or
live data clients. It only analyzes `OptionChainSnapshot` objects.


## TUI Integration

The Market Intelligence Screen in the TITAN TUI provides a read-only operational dashboard visualizing the output of this engine/component. No business logic or analytics are executed in the presentation layer.

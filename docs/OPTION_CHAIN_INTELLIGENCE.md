# Option Chain Intelligence

## Status

M2.1.5 is implemented as an evidence-backed coordination layer.

## Purpose

Option Chain Intelligence combines independent option analytics into one
broker-independent view of option-chain conditions. It does not produce trade
entries, exits, position sizing, or broker-specific instructions.

## Flow

```text
OptionChainSnapshot
        |
        v
PCRAnalyzer / SupportResistanceAnalyzer / OpenInterestAnalyzer
        |
        v
AnalysisResult
        |
        v
Evidence
        |
        v
EvidenceAggregator
        |
        v
OptionChainAnalysis + OptionChainExplanation
```

## Coordinator

`OptionChainAnalyzer` integrates the production analyzers currently available
for M2.1.5:

- `PCRAnalyzer`
- `SupportResistanceAnalyzer`
- `OpenInterestAnalyzer`

Each analyzer remains responsible for its own calculation and interpretation.
The coordinator is responsible for:

- validating the normalized snapshot
- running configured analyzers
- converting analyzer results into universal `Evidence`
- aggregating score, confidence, and bias
- exposing support, resistance, PCR, and highest OI strikes
- generating a structured explanation from evidence reasons

## Output

`OptionChainAnalysis` contains:

- `overall_bias`
- `confidence`
- `support`
- `resistance`
- `pcr`
- `highest_put_strike`
- `highest_call_strike`
- `bullish_score`
- `bearish_score`
- `neutral_score`
- `warnings`
- `evidence`
- `explanation`
- `metadata`

## Boundary Rule

Option Chain Intelligence imports no broker code and makes no API calls. Broker
adapters must normalize external option-chain data into `OptionChainSnapshot`
before analytics begins.

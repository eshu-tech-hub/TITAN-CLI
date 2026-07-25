# ADR-005: Vanna Exposure Intelligence Engine

## Status

Accepted

## Context

M2.2.7 requires a Vanna Exposure Intelligence Engine that consumes per-strike Vanna values from supplied option analytics and produces institutional-grade Vanna intelligence. The system must:

1. Classify the net Vanna regime (positive, negative, balanced, or unknown)
2. Assess the dealer hedging pressure implied by Vanna (low, medium, high, extreme)
3. Integrate with the Evidence Engine, Intelligence Fusion Engine, and existing modules (Gamma Exposure, Dealer Positioning)
4. Support future extensions for Charm, Dealer Hedging Flow, 0DTE Options, Intraday Flow, Cross-expiry Vanna, and Historical Vanna
5. Be broker-independent with no API calls, no Black-Scholes estimation, and no Vanna calculation from raw data
6. Pass Ruff, Black, MyPy, and Pytest quality checks

## Decision

We will implement the Vanna Exposure Intelligence Engine as three separate components:

### 1. VannaRegimeAnalyzer

- Computes `net_vanna = Σ(call_vanna × call_open_interest) + Σ(put_vanna × put_open_interest)` from `OptionChainSnapshot`
- Classifies regime based on `net_vanna` sign:
  - `> 0.001` → `POSITIVE`
  - `< -0.001` → `NEGATIVE`
  - Otherwise → `BALANCED`
- Falls back to `UNKNOWN` regime when no per-strike Vanna data is available
- Confidence reflects data completeness (proportion of strikes with valid vanna)

### 2. VannaPressureAnalyzer

- Takes `VannaExposureInput` and `VannaRegime` as input
- Computes `iv_sensitivity (0-1)`: based on Vanna sign and Gamma regime
  - POSITIVE Vanna + short Gamma → high IV sensitivity (0.8)
  - POSITIVE Vanna + long Gamma → moderate IV sensitivity (0.5)
  - NEGATIVE Vanna + short Gamma → high IV sensitivity (0.8)
  - NEGATIVE Vanna + long Gamma → moderate IV sensitivity (0.5)
  - No Gamma regime → baseline based on Vanna sign
- Computes `price_sensitivity (0-1)`: based on Gamma regime, Vanna sign, and dealer hedging pressure
  - Short Gamma → high (0.7)
  - Long Gamma → low (0.3)
  - POSITIVE Vanna → amplifies (×1.3)
  - NEGATIVE Vanna → dampens (×0.7)
  - High hedging pressure → amplifies
- Classifies pressure level from sensitivity thresholds (0.3/0.6/0.8)
- Generates dealer response narrative string

### 3. VannaExposureAnalyzer (Orchestrator)

- Creates `VannaExposureInput` from keyword arguments
- Calls `VannaRegimeAnalyzer.analyze()` then `VannaPressureAnalyzer.analyze()`
- Generates `Evidence` with:
  - Source: `"Vanna Exposure"`
  - Category: `OPTION_CHAIN`
  - Signal: POSITIVE→BULLISH, NEGATIVE→BEARISH, BALANCED→NEUTRAL, UNKNOWN→UNKNOWN
  - Base score: POSITIVE→65, NEGATIVE→35, BALANCED→50, UNKNOWN→50
  - Score adjusted +5 when pressure is HIGH or EXTREME
  - Confidence weighted: regime (0.5) + pressure (0.5)
  - Reasons from regime + pressure reasons
- Generates `VannaExplanation` with 6 sections (overall vanna, dealer sensitivity, IV impact, price impact, institutional interpretation, risk assessment)
- Generates metadata warnings for missing data

## Alternatives Considered

### Alternative A: Extending VannaRegimeAnalyzer into VannaPressureAnalyzer

- **Rejected because:** Regime (what the net Vanna position is) and Pressure (what it means for dealer hedging) are distinct concerns with different algorithms, inputs, and test surfaces. Keeping them separate allows independent testing and future extension.

### Alternative B: Single combined VannaExposureAnalyzer

- **Rejected because:** This would create a monolith with multiple responsibilities, violating the Single Responsibility Principle. The architecture of the existing analytics (GEX, Dealer Positioning) uses separate analyzers per concern.

### Alternative C: Requiring per-strike Vanna always (no fallback)

- **Rejected because:** Not all data providers supply per-strike Vanna. The system should degrade gracefully to UNKNOWN regime with appropriate warnings rather than crashing or producing misleading results.

## Consequences

### Positive

- **Testability:** Each analyzer can be tested independently with minimal mocking
- **Extensibility:** New analyzers (Charm, Dealer Hedging Flow) can be added as additional sub-analyzers without modifying existing code
- **Reusability:** Sub-analyzers can be used independently by other components
- **Graceful degradation:** Missing per-strike Vanna produces UNKNOWN regime with reduced confidence, not errors
- **Self-documenting:** Clear separation of concerns makes the architecture obvious

### Negative

- **Indirection:** Three classes instead of one, increasing import complexity
- **Duplication:** Some validation logic is repeated across analyzers

### Neutral

- **Dependency chain:** `VannaExposureAnalyzer` depends on `VannaRegimeAnalyzer` and `VannaPressureAnalyzer`; `VannaPressureAnalyzer` depends on `VannaRegime` from `VannaRegimeAnalyzer`
- **Input model growth:** `VannaExposureInput` mirrors the existing pattern of passing all optional context to sub-analyzers

## Future Evolution

This design supports the following roadmap without structural changes:

- **Charm Analysis:** Add `CharmAnalyzer` with `DealerCharmAnalysis` model; `VannaPressureAnalyzer` consumes for improved price sensitivity
- **Dealer Hedging Flow:** Add `DealerHedgingFlowAnalyzer` consuming Vanna + Gamma + Vega output
- **0DTE Options:** Extend `OptionStrikeSnapshot` with intraday fields; `VannaRegimeAnalyzer` uses same algorithm
- **Intraday Flow:** `VannaExposureAnalyzer` stores historical results for trend detection
- **Cross-expiry Vanna:** `VannaRegimeAnalyzer` aggregates across multiple snapshots
- **Historical Vanna:** Use `VannaExposureAnalysis` persistent store for time-series analysis

## References

- [Vanna Exposure Documentation](../VANNA_EXPOSURE.md)
- M2.2.6 Gamma Exposure Intelligence (GEX engine)
- `titan/options/analytics/vanna_regime.py`
- `titan/options/analytics/vanna_pressure.py`
- `titan/options/analytics/vanna.py`
- `titan/options/analytics/gex.py`
- `titan/options/analytics/models.py`

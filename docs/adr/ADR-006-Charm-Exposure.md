# ADR-006: Charm Exposure Intelligence Engine

## Status

Accepted

## Context

M2.2.8 requires a Charm Exposure Intelligence Engine that consumes per-strike Charm values from supplied option analytics and produces institutional-grade Charm intelligence. The system must:

1. Classify the net Charm regime (positive, negative, balanced, or unknown)
2. Assess the time-driven dealer hedging pressure implied by Charm (low, medium, high, extreme)
3. Compute dealer delta decay magnitude (0-1)
4. Detect near-expiry Charm risk
5. Integrate with the Evidence Engine, Intelligence Fusion Engine, and existing modules (Gamma Exposure, Vanna Exposure, Dealer Positioning)
6. Support future extensions for Dealer Hedging Flow, 0DTE Options, Intraday Charm, Cross-expiry Charm, Historical Charm, and Time-series Flow Analysis
7. Be broker-independent with no API calls, no Black-Scholes estimation, and no Charm calculation from raw data
8. Pass Ruff, Black, MyPy, and Pytest quality checks

## Decision

We will implement the Charm Exposure Intelligence Engine using the same architectural pattern as the Vanna Exposure Intelligence Engine (ADR-005):

### 1. CharmRegimeAnalyzer

- Computes `net_charm = Σ(call_charm × call_open_interest) + Σ(put_charm × put_open_interest)` from `OptionChainSnapshot`
- Classifies regime based on `net_charm` sign:
  - `> 1e-8` → `POSITIVE`
  - `< -1e-8` → `NEGATIVE`
  - Otherwise → `BALANCED`
- Falls back to `UNKNOWN` regime when no per-strike Charm data is available
- Confidence reflects data completeness (proportion of strikes with valid charm)

### 2. CharmPressureAnalyzer

- Takes `CharmExposureInput` and `CharmRegime` as input
- Computes `time_sensitivity (0-1)`: based on Charm sign, Gamma regime, Vanna context
  - POSITIVE/NEGATIVE Charm → 0.5 base
  - BALANCED → 0.1 base
  - Short Gamma → amplifies (+0.2)
  - Long Gamma → mild (+0.1)
  - Vanna context available → +0.1
  - Regime confidence > 0.5 → +0.1
- Computes `near_expiry_risk (bool)`: True when expiry is within 7 days and Charm regime is active
- Pressure level from time_sensitivity + near_expiry boost (0.2 if near_expiry)
- Generates dealer response narrative string

### 3. CharmExposureAnalyzer (Orchestrator)

- Creates `CharmExposureInput` from keyword arguments (adds `vanna_exposure` field)
- Calls `CharmRegimeAnalyzer.analyze()` then `CharmPressureAnalyzer.analyze()`
- Computes `dealer_delta_decay` from time_sensitivity + near_expiry boost + charm signal boost
- Generates `Evidence` with:
  - Source: `"Charm Exposure"`
  - Category: `OPTION_CHAIN`
  - Signal: POSITIVE→BULLISH, NEGATIVE→BEARISH, BALANCED→NEUTRAL, UNKNOWN→UNKNOWN
  - Base score: POSITIVE→60, NEGATIVE→40, BALANCED→50, UNKNOWN→50
  - Score adjusted +5 when pressure is HIGH or EXTREME
  - Confidence weighted: regime (0.5) + pressure (0.5)
  - Reasons from regime + pressure + delta_decay + near_expiry
- Generates `CharmExplanation` with 6 sections (overall charm, dealer delta decay, time decay impact, near expiry risk, institutional interpretation, risk assessment)
- Generates metadata warnings for missing data

### Data Models

Extended `OptionStrikeSnapshot` with `call_charm: float | None` and `put_charm: float | None` fields.

New models in `models.py`:

- `CharmRegimeType` enum: POSITIVE, NEGATIVE, BALANCED, UNKNOWN
- `CharmPressureLevel` enum: LOW, MEDIUM, HIGH, EXTREME, UNKNOWN
- `CharmRegime`: regime_type, net_charm, confidence, reasons
- `CharmPressure`: pressure_level, dealer_response, time_sensitivity, near_expiry_risk, confidence, reasons
- `CharmExplanation`: overall_charm, dealer_delta_decay, time_decay_impact, near_expiry_risk, institutional_interpretation, risk_assessment
- `CharmExposureInput`: dealer_positioning, gamma_exposure, vanna_exposure, greeks, surface, option_chain, option_chain_snapshot
- `CharmExposureAnalysis`: net_charm, regime, pressure, dealer_delta_decay, near_expiry_risk, confidence, warnings, metadata, evidence, explanation — with `neutral_placeholder()` classmethod

## Alternatives Considered

### Alternative A: Extending CharmRegimeAnalyzer into CharmPressureAnalyzer

- **Rejected because:** Regime (what the net Charm position is) and Pressure (what it means for delta decay hedging) are distinct concerns with different algorithms, inputs, and test surfaces. This mirrors the Vanna architecture (ADR-005).

### Alternative B: Single combined CharmExposureAnalyzer

- **Rejected because:** Would create a monolith with multiple responsibilities. The existing analytics architecture (GEX, Vanna, Dealer Positioning) uses separate analyzers per concern.

### Alternative C: Omitting near_expiry_risk as a distinct field

- **Rejected because:** Near-expiry Charm acceleration is a critical institutional concern. Making it an explicit boolean field on both `CharmPressure` and `CharmExposureAnalysis` ensures it is surfaced to consumers and testable in isolation.

## Consequences

### Positive

- **Testability:** Each analyzer can be tested independently with minimal mocking
- **Extensibility:** New analyzers (Dealer Hedging Flow, 0DTE) can be added as additional sub-analyzers
- **Reusability:** Sub-analyzers can be used independently by other components
- **Graceful degradation:** Missing per-strike Charm produces UNKNOWN regime with reduced confidence
- **Near-expiry awareness:** Explicit detection of near-expiry risk enables alerting and position sizing adjustments

### Negative

- **Indirection:** Three classes instead of one, increasing import complexity
- **Vanna dependency:** `CharmExposureInput` and `CharmPressureAnalyzer` depend on `VannaExposureAnalysis`, creating a dependency on M2.2.7

### Neutral

- **Dependency chain:** `CharmExposureAnalyzer` depends on `CharmRegimeAnalyzer` and `CharmPressureAnalyzer`; `CharmPressureAnalyzer` depends on `CharmRegime` and Vanna/Gamma/Dealer inputs
- **Input model growth:** `CharmExposureInput` contains 7 optional fields, following established patterns

## Future Evolution

This design supports the following roadmap without structural changes:

- **Dealer Hedging Flow:** Add `DealerHedgingFlowAnalyzer` consuming Charm + Gamma + Vanna output
- **0DTE Options:** Extend `OptionStrikeSnapshot` with intraday charm; `CharmRegimeAnalyzer` uses same algorithm with accelerated thresholds
- **Intraday Charm:** `CharmExposureAnalyzer` stores historical results for intraday trend detection
- **Cross-expiry Charm:** `CharmRegimeAnalyzer` aggregates across multiple snapshots with term weighting
- **Historical Charm:** Use `CharmExposureAnalysis` persistent store for time-series analysis
- **Time-series Flow Analysis:** Predict dealer hedging flow direction from regime shifts over time

## References

- [Charm Exposure Documentation](../CHARM_EXPOSURE.md)
- ADR-005 Vanna Exposure Intelligence (architectural pattern)
- M2.2.6 Gamma Exposure Intelligence (GEX engine)
- M2.2.7 Vanna Exposure Intelligence (VEX engine)
- `titan/options/analytics/charm_regime.py`
- `titan/options/analytics/charm_pressure.py`
- `titan/options/analytics/charm.py`
- `titan/options/analytics/models.py`

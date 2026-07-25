# Volatility Surface Intelligence Engine

## Purpose

The Volatility Surface Intelligence Engine is the institutional
volatility orchestrator. It consumes the outputs of four existing
analyzers — VolatilityAnalyzer, SmileAnalyzer, SkewAnalyzer, and
TermStructureAnalyzer — and produces a unified, institutional-grade
assessment of the entire volatility surface.

This engine explicitly does **not** recalculate any volatility metric,
smile curvature, skew, or term structure computation. It is a pure
orchestrator.

## Why an Orchestrator

Each existing analyzer produces an isolated assessment:

| Analyzer | Output |
|---|---|
| VolatilityAnalyzer | Current IV, HV, IV rank, regime, trend |
| SmileAnalyzer | Smile curvature, symmetry, regime |
| SkewAnalyzer | Skew direction, strength, risk reversal |
| TermStructureAnalyzer | Curve shape, strength, event premium |

A trader or portfolio manager needs to know whether these assessments
agree or conflict, how healthy the overall surface is, and whether
anomalies exist. The Surface Intelligence Engine provides that
synthesis.

## Architecture

```text
+-------------------+  +---------------+  +-------------+  +-------------------+
| VolatilityAnalysis|  | SmileAnalysis |  | SkewAnalysis |  |TermStructureAnalysis|
+--------+----------+  +-------+-------+  +------+------+  +---------+---------+
         |                     |                  |                    |
         +---------------------+------------------+--------------------+
                               |
                               v
                  +----------------------------+
                  |  VolatilitySurfaceInput    |
                  |  (4 optional component     |
                  |   analysis objects)        |
                  +------------+---------------+
                               |
            +------------------+------------------+
            |                  |                  |
            v                  v                  v
+-------------------+ +-----------------+ +-------------------+
|SurfaceHealth      | |SurfaceConsistency| |SurfaceAnomaly    |
|Analyzer           | |Analyzer          | |Analyzer           |
|                   | |                  | |                   |
|Data availability  | |Cross-module      | |Extreme smile/skew |
|Component confidence| |signal agreement  | |Broken term struct |
|Health: HEALTHY /  | |Consistent /      | |Conflicting signals|
|GOOD / CAUTION /   | |Partially /       | |Missing intelligence|
|UNHEALTHY / UNKNOWN| |Inconsistent      | |Low confidence     |
+--------+----------+ +--------+----------+ +--------+----------+
         |                     |                      |
         +---------------------+----------------------+
                               |
                               v
                  +----------------------------+
                  | SurfaceIntelligenceAnalyzer|
                  |       (orchestrator)       |
                  +------------+---------------+
                               |
                               v
                  +----------------------------+
                  |SurfaceIntelligenceAnalysis |
                  |                            |
                  | health / consistency       |
                  | overall_bias               |
                  | institutional_confidence   |
                  | component_scores           |
                  | anomalies                  |
                  | evidence / explanation     |
                  +----------------------------+
```

## Surface Health

Surface Health assesses the availability and quality of the four
volatility intelligence components.

### Criteria

| Level | Condition |
|---|---|
| HEALTHY | All 4 components present, all confidence >= 0.7 |
| GOOD | 3+ components present, avg confidence >= 0.5 |
| CAUTION | 2+ components present, or some confidence < 0.5 |
| UNHEALTHY | 0-1 components available |
| UNKNOWN | No components available |

### Component Quality

Each component is individually graded:

| Quality | Condition |
|---|---|
| `healthy` | Available and confidence >= 0.7 |
| `good` | Available and confidence >= 0.5 |
| `caution` | Available and confidence >= 0.3 |
| `low_confidence` | Available and confidence < 0.3 |
| `missing` | Component not provided |
| `unknown` | Status cannot be determined |

## Surface Consistency

Surface Consistency evaluates cross-module signal agreement.

### Criteria

| Level | Condition |
|---|---|
| CONSISTENT | All components agree on signal direction (all bullish, all bearish, or all neutral) |
| PARTIALLY_CONSISTENT | Some directional agreement but not universal |
| INCONSISTENT | Clear conflict: some components bullish, others bearish |
| UNKNOWN | No signals available |

### Signal Mapping

Each component's `evidence.signal` is mapped to a directional bias:

| EvidenceSignal | MarketBias |
|---|---|
| VERY_BULLISH, BULLISH | BULLISH |
| VERY_BEARISH, BEARISH | BEARISH |
| NEUTRAL, UNKNOWN | NEUTRAL |

## Surface Anomalies

The anomaly detector checks for six types of surface anomalies:

| Anomaly Type | Detection Criteria |
|---|---|
| EXTREME_SMILE | `smile_shape == EXTREME` |
| EXTREME_SKEW | `skew_strength == EXTREME` |
| BROKEN_TERM_STRUCTURE | `term_structure.shape == INVERTED` AND strength >= HIGH |
| CONFLICTING_SIGNALS | One or more components bullish while others bearish |
| MISSING_INTELLIGENCE | Any component is None |
| LOW_CONFIDENCE | Any component confidence < 0.3 |

## Institutional Interpretation

The orchestrator generates a derived overall bias from component
signal voting. The bias feeds both the `Evidence` signal and the
institutional interpretation section:

- **Bullish overall bias** → "Components consistently indicate bullish
  bias. Consider upside strategies."
- **Bearish overall bias** → "Components consistently indicate bearish
  bias. Consider defensive positioning."
- **Inconsistent signals** → "Conflicting signals across components
  suggest an uncertain or transitioning market regime."
- **Low health** → "Surface quality is insufficient for reliable
  analysis. Seek alternative data sources."

## Data Model

### SurfaceIntelligenceAnalysis

| Field | Type | Description |
|---|---|---|
| `health` | `SurfaceHealthLevel` | Overall surface health |
| `consistency` | `SurfaceConsistencyLevel` | Cross-module signal agreement |
| `overall_bias` | `MarketBias` | Derived aggregate bias |
| `institutional_confidence` | `float` | Average component confidence (0-1) |
| `component_scores` | `tuple[SurfaceComponentScore, ...]` | Per-component breakdown |
| `anomalies` | `tuple[SurfaceAnomaly, ...]` | Detected anomalies |
| `warnings` | `tuple[str, ...]` | Non-fatal warnings |
| `metadata` | `Mapping[str, Any]` | Producer context |
| `evidence` | `Evidence \| None` | Evidence for fusion engine |
| `explanation` | `SurfaceExplanation \| None` | Structured explanation |

### SurfaceComponentScore

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Component name (Volatility, Smile, Skew, Term Structure) |
| `score` | `float` | Component evidence score (0-100) |
| `confidence` | `float` | Component confidence (0-1) |
| `signal` | `EvidenceSignal \| None` | Component directional signal |
| `available` | `bool` | Whether component was provided |

### SurfaceAnomaly

| Field | Type | Description |
|---|---|---|
| `type` | `SurfaceAnomalyType` | Type of anomaly |
| `source` | `str` | Component name where anomaly was found |
| `description` | `str` | Human-readable description |

### SurfaceExplanation

| Field | Type | Description |
|---|---|---|
| `overall_surface` | `str` | Summary of the surface assessment |
| `health` | `str` | Health assessment explanation |
| `consistency` | `str` | Consistency assessment explanation |
| `anomalies` | `str` | Anomaly descriptions |
| `institutional_interpretation` | `str` | Market context interpretation |
| `risk_assessment` | `str` | Risk management guidance |

### Enums

| Enum | Values |
|---|---|
| `SurfaceHealthLevel` | HEALTHY, GOOD, CAUTION, UNHEALTHY, UNKNOWN |
| `SurfaceConsistencyLevel` | CONSISTENT, PARTIALLY_CONSISTENT, INCONSISTENT, UNKNOWN |
| `SurfaceAnomalyType` | EXTREME_SMILE, EXTREME_SKEW, BROKEN_TERM_STRUCTURE, CONFLICTING_SIGNALS, MISSING_INTELLIGENCE, LOW_CONFIDENCE |

## API Examples

### Basic Usage — All Components Healthy

```python
from titan.options.analytics import SurfaceIntelligenceAnalyzer

# Assume these come from the respective analyzers
analysis = SurfaceIntelligenceAnalyzer().analyze(
    volatility=vol_analysis,
    smile=smile_analysis,
    skew=skew_analysis,
    term_structure=term_analysis,
)

print(f"Health: {analysis.health}")           # Health: HEALTHY
print(f"Consistency: {analysis.consistency}") # Consistency: CONSISTENT
print(f"Bias: {analysis.overall_bias}")        # Bias: NEUTRAL
print(f"Confidence: {analysis.institutional_confidence:.0%}")
```

### Detecting Conflicts

```python
analysis = SurfaceIntelligenceAnalyzer().analyze(
    volatility=vol_with_bullish_signal,
    smile=smile_with_bearish_signal,
    skew=skew_with_bearish_signal,
    term_structure=term_with_neutral_signal,
)

print(f"Consistency: {analysis.consistency}")
# Consistency: INCONSISTENT
print(f"Anomalies: {len(analysis.anomalies)}")
# Anomalies: 1  (CONFLICTING_SIGNALS)
```

### Missing Component

```python
analysis = SurfaceIntelligenceAnalyzer().analyze(
    volatility=vol_analysis,
    smile=smile_analysis,
    # skew and term_structure not provided
)

print(f"Health: {analysis.health}")  # Health: CAUTION
anomalies = [a for a in analysis.anomalies
             if a.type == SurfaceAnomalyType.MISSING_INTELLIGENCE]
print(f"Missing: {[a.source for a in anomalies]}")
# Missing: ['Skew', 'Term Structure']
```

### Evidence and Explanation

```python
analysis = SurfaceIntelligenceAnalyzer().analyze(
    volatility=vol_analysis,
    smile=smile_analysis,
    skew=skew_analysis,
    term_structure=term_analysis,
)

# Evidence for fusion engine
evidence = analysis.evidence
print(f"Signal: {evidence.signal}")
print(f"Score: {evidence.score}")
print(f"Reasons: {evidence.reasons}")

# Structured explanation
explanation = analysis.explanation
print(explanation.institutional_interpretation)
print(explanation.risk_assessment)
```

## Missing Data Handling

| Scenario | Behaviour |
|---|---|
| All components None | Neutral placeholder, warning |
| 3 of 4 components present | Health = GOOD |
| 2 of 4 components present | Health = CAUTION |
| 0-1 components present | Health = UNHEALTHY |
| Component with no evidence | Score = 50.0, confidence = 0.0 |
| Conflicting signals | Consistency = INCONSISTENT, anomaly detected |
| Low confidence component | Anomaly detected (LOW_CONFIDENCE) |
| Extreme smile/skew/term | Anomaly detected |

## Evidence Integration

The `SurfaceIntelligenceAnalyzer` produces `Evidence` consumable by the
Intelligence Fusion Engine:

| Property | Value |
|---|---|
| **Source** | "Volatility Surface" |
| **Category** | `EvidenceCategory.OPTION_CHAIN` |
| **Signal** | Derived from component voting (BULLISH / BEARISH / NEUTRAL / UNKNOWN) |
| **Score** | Weighted average of component scores (weighted by confidence) |
| **Confidence** | Average of component confidences |
| **Weight** | 1.0 |
| **Reasons** | Health, consistency, bias, active components, anomaly count |
| **Warnings** | Combined warnings from all components |

## Migration Impact

**None.** This is a purely additive change:

- All four analysis modules (Volatility, Smile, Skew, Term Structure)
  are unmodified.
- All existing analyzers continue unchanged.
- `SurfaceIntelligenceAnalyzer` consumes existing outputs — it does
  not depend on any specific analyzer implementation.
- Evidence Engine and Intelligence Fusion integration unchanged.
- No broker dependencies introduced.

## Quality

- Strict typing throughout (Python 3.14+).
- Frozen dataclasses with slots.
- No broker dependencies, no API calls.
- No numpy, no scipy, no Black-Scholes.
- No duplicated volatility calculations — pure orchestration.
- Ruff clean, Black clean, MyPy clean (0 new errors).
- Full test coverage in `tests/test_surface_intelligence.py`
  (59 tests, 15 test classes).
- Forbidden import checks cover all new modules.

## Future Roadmap

### Supported Without Redesign

| Feature | How |
|---|---|
| Dealer Positioning | New sub-analyzer, consumed by orchestrator |
| Gamma Exposure | New sub-analyzer (GEX), consumed by orchestrator |
| Vanna / Charm | New sub-analyzers, consumed by orchestrator |
| Volatility Surface Snapshot | Extend input to include `VolatilitySurfaceSnapshot` |
| Forward Volatility | New sub-analyzer, consumed by orchestrator |
| Variance Risk Premium | New sub-analyzer, consumed by orchestrator |
| Surface History | Track surface assessments over time |

### Extending the Orchestrator

To add a new sub-analyzer to the surface intelligence pipeline:

1. Create a new analyzer class (e.g., `GammaExposureAnalyzer`).
2. Add its analysis type to `VolatilitySurfaceInput`.
3. Add a sub-analyzer call in `SurfaceIntelligenceAnalyzer.analyze()`.
4. Add its results to `component_scores`, health, consistency, and
   anomaly checks.

No existing code needs to change.

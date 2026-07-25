# Intelligence Fusion Engine

## Purpose

The Intelligence Fusion Engine is the central hub for TITAN's market
intelligence. It consumes `Evidence` objects from every intelligence module
and fuses them into a unified `IntelligenceFusion` result.

It does **not** generate BUY or SELL decisions. It does **not** calculate
entries, stop-losses, or trade qualification. It only fuses intelligence.

## Architecture

```text
+------------------+       +-------------------+
| Option Chain     |       |                   |
| Open Interest    |       |   FusionEngine    |
| Greeks           |------>|                   |------> IntelligenceFusion
| Liquidity        |       |   add_evidence()  |         - overall_score
| Volatility       |       |   remove_evidence()|        - overall_confidence
| News             |       |   validate()       |         - overall_signal
| Market Structure |       |   fuse()           |         - supporting_evidence
| Market Regime    |       |   summary()        |         - conflicting_evidence
| Risk             |       |   to_explanation() |         - missing_categories
+------------------+       +--------+----------+         - warnings
                                     |                   - explanation
                                     v
                          +-------------------+
                          |  FusionExplainer  |
                          |-------------------|
                          |  Strongest        |
                          |  Weakest          |
                          |  Conflicts        |
                          |  Missing Info     |
                          |  Overall Assessment|
                          +-------------------+
```

## Evidence Lifecycle

1. **Produce** — Each intelligence module converts its output into `Evidence`.
2. **Submit** — Evidence is added to the `FusionEngine` via `add_evidence()`.
3. **Weight** — The engine applies a `WeightProvider` strategy (equal by default).
4. **Validate** — Evidence is checked for validity, low confidence, duplicates.
5. **Detect conflicts** — Directional, low-confidence, and duplicate conflicts.
6. **Fuse** — Weighted scores and confidences are aggregated.
7. **Explain** — A structured explanation is generated.

## FusionEngine API

### add_evidence(evidence: Evidence) -> None

Add a single evidence item. Raises `FusionEngineError` if the evidence is
invalid or a duplicate (same source + category already exists).

### remove_evidence(source: str, category: EvidenceCategory | None = None) -> int

Remove evidence items by source and optional category. Returns count removed.

### validate() -> list[str]

Return non-fatal warnings about current evidence (low/excessive confidence).

### fuse() -> IntelligenceFusion

Execute fusion. Produces the complete `IntelligenceFusion` result.

### summary() -> Evidence

Return an aggregate `Evidence` summary of the current fusion state.

### to_explanation() -> str

Generate a structured multi-section explanation string.

## Models

### IntelligenceFusion

| Field | Type | Description |
|---|---|---|
| `overall_score` | `Score` | Weighted aggregate score (0-100). |
| `overall_confidence` | `Confidence` | Weighted aggregate confidence (0.0-1.0). |
| `overall_signal` | `EvidenceSignal` | Aggregate directional signal. |
| `supporting_evidence` | `tuple[Evidence, ...]` | Evidence aligned with the overall signal. |
| `conflicting_evidence` | `tuple[EvidenceConflict, ...]` | Detected conflicts. |
| `missing_categories` | `tuple[EvidenceCategory, ...]` | Expected but absent categories. |
| `warnings` | `tuple[str, ...]` | Non-fatal fusion warnings. |
| `metadata` | `Mapping[str, Any]` | Producer-owned context. |
| `timestamp` | `datetime` | Fusion computation timestamp. |
| `evidence_count` | `int` | Total evidence items fused. |
| `explanation` | `str \| None` | Structured explanation (populated by `to_explanation()`). |

### EvidenceWeight

| Field | Type | Description |
|---|---|---|
| `category` | `EvidenceCategory` | Target evidence category. |
| `weight` | `float` | Aggregation weight multiplier. |
| `enabled` | `bool` | Whether this category is active in fusion. |

### EvidenceConflict

| Field | Type | Description |
|---|---|---|
| `conflict_type` | `ConflictType` | Classification (bullish_vs_bearish, low_confidence, duplicate_source, missing_category). |
| `reason` | `str` | Human-readable description. |
| `evidence_items` | `tuple[Evidence, ...]` | The conflicting evidence items. |

## Weighting System

Default: equal weighting (all evidence has weight 1.0).

The architecture supports these strategies via the `WeightProvider` ABC:

- **Static weights** — Fixed per-category multipliers (`StaticWeightProvider`).
- **Dynamic weights** — Subclass `WeightProvider` to compute weights from state.
- **Regime-dependent weights** — Adjust weights when market regime changes.
- **User-defined weights** — Load from configuration files.

All strategies implement `get_weight(evidence: Evidence) -> float`.

## Weighting Examples

```python
# Equal weighting (default)
engine = FusionEngine()

# Static per-category weighting
provider = StaticWeightProvider([
    EvidenceWeight(category=EvidenceCategory.OPTION_CHAIN, weight=2.0),
    EvidenceWeight(category=EvidenceCategory.INDICATOR, weight=1.5),
    EvidenceWeight(category=EvidenceCategory.NEWS, weight=0.5,
                   enabled=False),
])
engine = FusionEngine(weight_provider=provider)
```

## Conflict Detection

| Type | Condition |
|---|---|
| `BULLISH_VS_BEARISH` | At least one bullish and one bearish evidence item present. |
| `LOW_CONFIDENCE` | Any evidence item with confidence < 0.1. |
| `DUPLICATE_SOURCE` | Same source + category pair added twice. |
| `MISSING_CATEGORY` | Required categories absent from the evidence set. |

## Explanation Sections

`FusionExplainer` generates:

1. **Overall** — Signal, score, confidence, evidence count, conflict count.
2. **Strongest Evidence** — The evidence with highest score * confidence.
3. **Weakest Evidence** — The evidence with lowest score * confidence.
4. **Conflicts** — All detected conflicts with descriptions.
5. **Missing Information** — Categories expected but absent.
6. **Overall Assessment** — Narrative summary of the fused intelligence.

## Future Compatibility

The architecture supports these consumers without redesign:

- **Decision Engine** — Consumes `IntelligenceFusion.overall_signal` and scores.
- **Trade Qualification** — Uses supporting/conflicting evidence for filtering.
- **Portfolio Manager** — Reads overall confidence and warnings.
- **Risk Engine** — Consumes evidence and metadata for risk assessment.
- **AI Reasoning Layer** — Consumes `IntelligenceFusion` and explanation.

## Boundary Rule

`FusionEngine` knows only `Evidence`. It must never import:

- Option modules
- Indicators
- Broker code
- News modules
- Market modules
- Portfolio code
- Risk code

## Quality

- Strict typing throughout.
- Dataclasses with `slots=True` and `frozen=True` where appropriate.
- Enums for signal, category, and conflict type.
- Ruff clean.
- Full test coverage: empty, single, multiple, conflicting, missing
  categories, weighting, validation, explanation.
- No broker imports, no API calls, no duplicated logic.

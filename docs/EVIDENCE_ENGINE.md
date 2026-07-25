# Evidence Engine Foundation

## Why TITAN Uses Evidence

TITAN modules must communicate through one universal language. Indicators,
option analytics, market structure, volume, news, risk, and future decision
systems should not pass dictionaries, broker payloads, or module-specific
objects between each other.

`Evidence` gives every module a stable contract:

- where the information came from
- what category it belongs to
- the directional signal
- a normalized score
- confidence and weight
- reasons, warnings, metadata, and timestamp

## Architecture

```text
+------------------+       +--------------------+
| Evidence Producer|------>| Evidence           |
|------------------|       |--------------------|
| Indicator        |       | category           |
| Option Analytics |       | signal             |
| News             |       | score/confidence   |
| Risk             |       | reasons/warnings   |
+------------------+       +---------+----------+
                                      |
                                      v
                            +--------------------+
                            | EvidenceAggregator |
                            |--------------------|
                            | add/extend/clear   |
                            | overall score      |
                            | overall confidence |
                            | grouped evidence   |
                            +--------------------+
```

The aggregator only knows about `Evidence`. It does not import indicators,
options, brokers, news, market calculations, or the future decision engine.

## Producer Rule

Every future module must convert its internal output into `Evidence` before
crossing a subsystem boundary.

Example:

```python
Evidence(
    source="SMA",
    category=EvidenceCategory.INDICATOR,
    signal=EvidenceSignal.BULLISH,
    score=Score(70),
    confidence=Confidence(0.65),
    reasons=("Fast trend is above baseline.",),
)
```

## Aggregation

`EvidenceAggregator` supports:

- adding and extending evidence collections
- clearing state
- weighted average score
- weighted average confidence
- aggregate signal determination
- grouping by category with newest evidence first
- producing a synthetic summary `Evidence`

## Future Extensions

- Evidence serialization for persistence and audit logs.
- Immutable metadata normalization.
- Category-specific weighting policies outside the aggregator.
- Explainability reports built from reasons and warnings.
- Time decay and regime-aware aggregation policies.

## Boundary Rule

The evidence engine must remain independent. It must not import broker code,
SmartAPI, market calculations, option formulas, news providers, or the decision
engine.


## TUI Integration

The Market Intelligence Screen in the TITAN TUI provides a read-only operational dashboard visualizing the output of this engine/component. No business logic or analytics are executed in the presentation layer.

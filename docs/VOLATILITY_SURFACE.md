# Volatility Surface Foundation

## Purpose

The Volatility Surface Foundation provides the data infrastructure for
volatility surface analysis. It introduces `VolatilitySurfaceSnapshot` as
an immutable collection of `VolatilitySnapshot` objects keyed by option
expiry.

This milestone (M2.2.0) is **data infrastructure only**. No analytics,
no interpolation, no smile/skew/term-structure calculations.

## Why VolatilitySurfaceSnapshot Exists

The existing `VolatilityAnalyzer` operates on a single `VolatilitySnapshot`
at a time. Real-world volatility analysis requires understanding how
volatility changes across expiries — the volatility surface.

`VolatilitySurfaceSnapshot` fills this gap by:

- Grouping per-expiry snapshots into a single validated structure.
- Enforcing data quality (unique expiries, chronological order,
  non-empty).
- Providing a stable input contract for future analyzers (Smile, Skew,
  Term Structure).
- Supporting serialization for persistence and wire transfer.

## Architecture

```text
+-----------------------------+
|     VolatilitySnapshot      |  (single expiry, existing)
|-----------------------------|
| implied_volatility          |
| historical_volatility       |
| iv_rank / iv_percentile     |
| implied_volatilities[]       |
+-----------+-----------------+
            |
            | (one per expiry)
            v
+-----------------------------+
|  VolatilitySurfaceSnapshot  |  (NEW — multiple expiries)
|-----------------------------|
| entries: (expiry, snapshot)*|
| metadata: {}                |
| validation: sorted, unique  |
+-----------+-----------------+
            |
            v
+-----------------------------+
|  VolatilitySurface          |  (NEW — mutable builder)
|-----------------------------|
| add / remove / clear        |
| build() -> immutable        |
+-----------------------------+
```

## Data Model

### VolatilitySurfaceSnapshot

| Field | Type | Description |
|---|---|---|
| `entries` | `tuple[tuple[datetime, VolatilitySnapshot], ...]` | Sorted expiry-snapshot pairs |
| `metadata` | `Mapping[str, Any]` | Surface-level context |

**Validation (applied in `__post_init__`)**:

| Rule | Behaviour |
|---|---|
| Empty entries | Raises `ValueError` |
| Non-datetime expiry | Raises `TypeError` |
| Non-VolatilitySnapshot value | Raises `TypeError` |
| Duplicate expiry | Raises `ValueError` |
| Unsorted entries | Auto-sorted chronologically |

**Accessors**:

| Method | Returns |
|---|---|
| `surface[expiry]` | `VolatilitySnapshot` or raises `KeyError` |
| `expiry in surface` | `bool` |
| `len(surface)` | `int` |
| `iter(surface)` | `Iterator[tuple[datetime, VolatilitySnapshot]]` |
| `surface.expiries` | `tuple[datetime, ...]` (sorted) |
| `surface.snapshots` | `tuple[VolatilitySnapshot, ...]` |
| `surface.get(expiry, default)` | `VolatilitySnapshot \| None` |

**Serialization**:

| Method | Description |
|---|---|
| `surface.to_dict()` | JSON-compatible dictionary |
| `VolatilitySurfaceSnapshot.from_dict(data)` | Reconstruct from dict |
| `json.dumps(surface.to_dict(), default=str)` | JSON string |
| `VolatilitySurfaceSnapshot.from_dict(json.loads(s))` | Reconstruct from JSON |

Tuple fields (`implied_volatilities`, `historical_volatilities`) are
automatically restored from JSON lists during deserialization.

### VolatilitySurface (Builder)

| Method | Description |
|---|---|
| `add(expiry, snapshot)` | Add or replace an expiry |
| `remove(expiry)` | Remove an expiry (raises `KeyError` if missing) |
| `clear()` | Remove all entries |
| `build()` | Return validated `VolatilitySurfaceSnapshot` |

## How Future Analyzers Will Consume This

### Smile Analyzer (future)

```python
def analyze(surface: VolatilitySurfaceSnapshot) -> SmileAnalysis:
    for expiry, snapshot in surface:
        per_strike_iv = ...  # extract strike-specific IV
        skew = calculate_skew(per_strike_iv)
```

### Term Structure Analyzer (future)

```python
def analyze(surface: VolatilitySurfaceSnapshot) -> TermStructureAnalysis:
    tenors = surface.expiries
    atm_ivs = [s.implied_volatility for s in surface.snapshots]
    curve = fit_curve(tenors, atm_ivs)
```

### Skew Analyzer (future)

```python
def analyze(surface: VolatilitySurfaceSnapshot) -> SkewAnalysis:
    for expiry, snapshot in surface:
        skew = snapshot.metadata.get("call_iv") - snapshot.metadata.get("put_iv")
```

## Migration Impact

**None.** This is a purely additive change:

- `VolatilitySnapshot` is not modified.
- `VolatilityAnalyzer` API is unchanged.
- All existing analyzers continue to work without changes.
- Existing `VolatilityAnalysis` output is unaffected.
- Evidence Engine and Intelligence Fusion integration unchanged.
- The `VolatilitySurface` and `VolatilitySurfaceSnapshot` are new
  optional imports.

## Quality

- Strict typing throughout (Python 3.14+).
- Frozen dataclass with slots (consistent with existing models).
- No broker dependencies, no API calls.
- No numpy, no scipy, no Black-Scholes.
- Ruff clean, Black clean, MyPy clean.
- Full test coverage in `tests/test_volatility_surface.py`.
- Forbidden import checks extended to cover surface modules.

## Future Extension Points

The current design supports these without redesign:

| Extension | How |
|---|---|
| Volatility Smile | Add per-strike IV fields to metadata, or create a `SmileAnalyzer` consuming `VolatilitySurfaceSnapshot` |
| Term Structure | New analyzer consuming `VolatilitySurfaceSnapshot.expiries` and `.snapshots` |
| Stripped/Interpolated Surface | New model wrapping `VolatilitySurfaceSnapshot` with interpolation |
| Surface Evolution | New snapshot type carrying multiple `VolatilitySurfaceSnapshot` objects over time |
| Variance Risk Premium | New model consuming `VolatilitySurfaceSnapshot` for forward vol calculations |

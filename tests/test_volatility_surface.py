import json
from datetime import UTC, datetime

import pytest

from titan.options.analytics import (
    VolatilitySnapshot,
    VolatilitySurface,
    VolatilitySurfaceSnapshot,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_snapshot(
    *,
    implied_volatility: float | None = 0.25,
    historical_volatility: float | None = 0.20,
    iv_rank: float | None = 50.0,
    iv_percentile: float | None = 50.0,
) -> VolatilitySnapshot:
    return VolatilitySnapshot(
        implied_volatility=implied_volatility,
        historical_volatility=historical_volatility,
        iv_rank=iv_rank,
        iv_percentile=iv_percentile,
    )


def expiry_30() -> datetime:
    return datetime(2026, 7, 31, tzinfo=UTC)


def expiry_60() -> datetime:
    return datetime(2026, 8, 31, tzinfo=UTC)


def expiry_90() -> datetime:
    return datetime(2026, 9, 30, tzinfo=UTC)


def make_surface(
    *expiry_days: tuple[int, float, float],
) -> VolatilitySurfaceSnapshot:
    entries: list[tuple[datetime, VolatilitySnapshot]] = []
    for day, iv, hv in expiry_days:
        d = datetime(2026, 1, 1, tzinfo=UTC).replace(day=min(day, 28))
        d = d.replace(month=1 + (day // 28))
        entries.append(
            (d, make_snapshot(implied_volatility=iv, historical_volatility=hv))
        )
    return VolatilitySurfaceSnapshot(entries=tuple(entries))


# ---------------------------------------------------------------------------
# VolatilitySurfaceSnapshot
# ---------------------------------------------------------------------------


class TestVolatilitySurfaceSnapshot:
    def test_valid_surface(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.30)

        surface = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))

        assert len(surface) == 2
        assert surface[e1] == s1
        assert surface[e2] == s2

    def test_auto_sorts_expiries(self) -> None:
        e1, e2 = expiry_60(), expiry_30()
        s1 = make_snapshot(implied_volatility=0.30)
        s2 = make_snapshot(implied_volatility=0.20)

        surface = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))

        assert surface.expiries == (expiry_30(), expiry_60())

    def test_duplicate_expiries_raises(self) -> None:
        expiry = expiry_30()

        with pytest.raises(ValueError, match="Duplicate expiry"):
            VolatilitySurfaceSnapshot(
                entries=(
                    (expiry, make_snapshot(implied_volatility=0.20)),
                    (expiry, make_snapshot(implied_volatility=0.30)),
                )
            )

    def test_empty_surface_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one expiry"):
            VolatilitySurfaceSnapshot(entries=())

    def test_non_datetime_expiry_raises(self) -> None:
        with pytest.raises(TypeError, match="Expiry must be datetime"):
            VolatilitySurfaceSnapshot(
                entries=(("not-a-datetime", make_snapshot()),)  # type: ignore[arg-type]
            )

    def test_non_snapshot_value_raises(self) -> None:
        with pytest.raises(TypeError, match="Snapshot must be VolatilitySnapshot"):
            VolatilitySurfaceSnapshot(
                entries=((expiry_30(), "not-a-snapshot"),)  # type: ignore[arg-type]
            )

    def test_frozen(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))

        with pytest.raises(AttributeError):
            surface.entries = ()  # type: ignore[misc]

        with pytest.raises(AttributeError):
            surface.metadata = {}  # type: ignore[misc]

    def test_getitem(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.30)
        surface = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))

        assert surface[e1] == s1
        assert surface[e2] == s2

    def test_getitem_missing_raises_keyerror(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))

        with pytest.raises(KeyError, match="Expiry not found"):
            _ = surface[expiry_60()]

    def test_contains(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))

        assert expiry_30() in surface
        assert expiry_60() not in surface

    def test_len(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))
        assert len(surface) == 1

        surface2 = VolatilitySurfaceSnapshot(
            entries=(
                (expiry_30(), make_snapshot()),
                (expiry_60(), make_snapshot()),
            )
        )
        assert len(surface2) == 2

    def test_iter(self) -> None:
        e1, e2, e3 = expiry_30(), expiry_60(), expiry_90()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.30)
        s3 = make_snapshot(implied_volatility=0.40)
        surface = VolatilitySurfaceSnapshot(entries=((e2, s2), (e3, s3), (e1, s1)))

        pairs = list(iter(surface))
        assert pairs == [(e1, s1), (e2, s2), (e3, s3)]

    def test_expiries_property(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        surface = VolatilitySurfaceSnapshot(
            entries=((e2, make_snapshot()), (e1, make_snapshot()))
        )

        assert surface.expiries == (e1, e2)

    def test_snapshots_property(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.30)
        surface = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))

        assert surface.snapshots == (s1, s2)

    def test_get_found(self) -> None:
        e1 = expiry_30()
        s1 = make_snapshot(implied_volatility=0.20)
        surface = VolatilitySurfaceSnapshot(entries=((e1, s1),))

        assert surface.get(e1) == s1

    def test_get_not_found(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))

        assert surface.get(expiry_60()) is None

    def test_get_with_default(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))
        default_snapshot = make_snapshot(implied_volatility=0.99)

        result = surface.get(expiry_60(), default_snapshot)
        assert result is default_snapshot

    def test_equality_same(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.30)

        a = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))
        b = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))

        assert a == b
        assert a == b

    def test_equality_different_entries(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.30)
        s3 = make_snapshot(implied_volatility=0.40)

        a = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))
        b = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s3)))

        assert a != b

    def test_equality_different_length(self) -> None:
        e1 = expiry_30()
        s1 = make_snapshot(implied_volatility=0.20)

        a = VolatilitySurfaceSnapshot(entries=((e1, s1),))
        b = VolatilitySurfaceSnapshot(
            entries=((e1, s1), (expiry_60(), make_snapshot()))
        )

        assert a != b

    def test_equality_not_implemented(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))

        assert surface.__eq__("not-a-surface") is NotImplemented

    def test_metadata(self) -> None:
        e1 = expiry_30()
        s1 = make_snapshot(implied_volatility=0.20)
        meta = {"underlying": "SPY", "source": "test"}
        surface = VolatilitySurfaceSnapshot(entries=((e1, s1),), metadata=meta)

        assert surface.metadata["underlying"] == "SPY"
        assert surface.metadata["source"] == "test"

    def test_single_expiry(self) -> None:
        e1 = expiry_30()
        s1 = make_snapshot(implied_volatility=0.20)

        surface = VolatilitySurfaceSnapshot(entries=((e1, s1),))

        assert len(surface) == 1
        assert surface[e1] == s1

    def test_varying_data_completeness(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = VolatilitySnapshot()  # all None
        s2 = make_snapshot(implied_volatility=0.45, iv_rank=85.0)

        surface = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))

        assert surface[e1].implied_volatility is None
        assert surface[e2].implied_volatility == 0.45
        assert surface[e2].iv_rank == 85.0


# ---------------------------------------------------------------------------
# serialization
# ---------------------------------------------------------------------------


class TestVolatilitySurfaceSnapshotSerialization:
    def test_to_dict_roundtrip(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20, iv_rank=45.0)
        s2 = make_snapshot(implied_volatility=0.35, iv_rank=70.0)
        original = VolatilitySurfaceSnapshot(
            entries=((e1, s1), (e2, s2)),
            metadata={"underlying": "SPY"},
        )

        data = original.to_dict()
        restored = VolatilitySurfaceSnapshot.from_dict(data)

        assert original == restored

    def test_to_dict_structure(self) -> None:
        e1 = expiry_30()
        s1 = make_snapshot(implied_volatility=0.20)
        surface = VolatilitySurfaceSnapshot(
            entries=((e1, s1),), metadata={"key": "value"}
        )

        data = surface.to_dict()

        assert "entries" in data
        assert "metadata" in data
        assert len(data["entries"]) == 1
        assert data["entries"][0]["expiry"] == e1.isoformat()
        assert data["entries"][0]["snapshot"]["implied_volatility"] == 0.20
        assert data["metadata"]["key"] == "value"

    def test_from_dict_restores_tuples(self) -> None:
        s1 = VolatilitySnapshot(
            implied_volatility=0.25,
            implied_volatilities=(0.20, 0.22, 0.25),
            historical_volatilities=(0.18, 0.19, 0.20),
        )
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), s1),))

        data = surface.to_dict()
        restored = VolatilitySurfaceSnapshot.from_dict(data)

        assert isinstance(restored[expiry_30()].implied_volatilities, tuple)
        assert restored[expiry_30()].implied_volatilities == (0.20, 0.22, 0.25)
        assert restored[expiry_30()].historical_volatilities == (0.18, 0.19, 0.20)

    def test_json_serializable(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.35)
        surface = VolatilitySurfaceSnapshot(entries=((e1, s1), (e2, s2)))

        data = surface.to_dict()
        json_str = json.dumps(data, default=str)
        parsed = json.loads(json_str)
        restored = VolatilitySurfaceSnapshot.from_dict(parsed)

        assert restored == surface

    def test_from_dict_with_partial_snapshot(self) -> None:
        data = {
            "entries": [
                {
                    "expiry": "2026-07-31T00:00:00+00:00",
                    "snapshot": {
                        "implied_volatility": None,
                        "historical_volatility": None,
                        "realized_volatility": None,
                        "implied_volatilities": [],
                        "historical_volatilities": [],
                        "iv_rank": None,
                        "iv_percentile": None,
                        "volatility_index": None,
                        "underlying_price": None,
                        "metadata": {},
                    },
                }
            ],
            "metadata": {},
        }

        restored = VolatilitySurfaceSnapshot.from_dict(data)

        assert len(restored) == 1
        assert restored[datetime(2026, 7, 31, tzinfo=UTC)] is not None

    def test_equality_after_serialization_with_metadata(self) -> None:
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.35)
        original = VolatilitySurfaceSnapshot(
            entries=((e1, s1), (e2, s2)),
            metadata={"underlying": "SPY", "timestamp": "2026-07-02"},
        )

        data = original.to_dict()
        restored = VolatilitySurfaceSnapshot.from_dict(data)

        assert restored.metadata["underlying"] == "SPY"

    def test_from_dict_empty_entries_raises(self) -> None:
        data = {"entries": [], "metadata": {}}

        with pytest.raises(ValueError, match="at least one expiry"):
            VolatilitySurfaceSnapshot.from_dict(data)


# ---------------------------------------------------------------------------
# VolatilitySurface (builder)
# ---------------------------------------------------------------------------


class TestVolatilitySurface:
    def test_add_and_build(self) -> None:
        surface = VolatilitySurface()
        e1, e2 = expiry_30(), expiry_60()
        s1 = make_snapshot(implied_volatility=0.20)
        s2 = make_snapshot(implied_volatility=0.30)

        surface.add(e1, s1)
        surface.add(e2, s2)

        assert surface.count == 2

        snapshot = surface.build()
        assert isinstance(snapshot, VolatilitySurfaceSnapshot)
        assert snapshot[e1] == s1
        assert snapshot[e2] == s2

    def test_add_replaces_existing(self) -> None:
        surface = VolatilitySurface()
        expiry = expiry_30()

        surface.add(expiry, make_snapshot(implied_volatility=0.20))
        surface.add(expiry, make_snapshot(implied_volatility=0.50))

        assert surface.count == 1
        snapshot = surface.build()
        assert snapshot[expiry].implied_volatility == 0.50

    def test_add_type_errors(self) -> None:
        surface = VolatilitySurface()

        with pytest.raises(TypeError, match="expiry must be datetime"):
            surface.add("bad-expiry", make_snapshot())  # type: ignore[arg-type]

        with pytest.raises(TypeError, match="snapshot must be VolatilitySnapshot"):
            surface.add(expiry_30(), "bad-snapshot")  # type: ignore[arg-type]

    def test_remove(self) -> None:
        surface = VolatilitySurface()
        e1, e2 = expiry_30(), expiry_60()
        surface.add(e1, make_snapshot())
        surface.add(e2, make_snapshot())

        surface.remove(e1)

        assert surface.count == 1
        assert surface.get(e1) is None
        assert surface.get(e2) is not None

    def test_remove_missing_raises(self) -> None:
        surface = VolatilitySurface()

        with pytest.raises(KeyError, match="Expiry not found"):
            surface.remove(expiry_30())

    def test_clear(self) -> None:
        surface = VolatilitySurface()
        surface.add(expiry_30(), make_snapshot())
        surface.add(expiry_60(), make_snapshot())

        surface.clear()

        assert surface.count == 0

    def test_build_empty_raises(self) -> None:
        surface = VolatilitySurface()

        with pytest.raises(ValueError, match="Cannot build surface with no entries"):
            surface.build()

    def test_expiries_property(self) -> None:
        surface = VolatilitySurface()
        e1, e2 = expiry_60(), expiry_30()
        surface.add(e1, make_snapshot())
        surface.add(e2, make_snapshot())

        assert surface.expiries == (e2, e1)

    def test_get(self) -> None:
        surface = VolatilitySurface()
        e1 = expiry_30()
        s1 = make_snapshot(implied_volatility=0.20)
        surface.add(e1, s1)

        assert surface.get(e1) == s1
        assert surface.get(expiry_60()) is None

    def test_build_validates(self) -> None:
        surface = VolatilitySurface()
        surface.add(expiry_30(), make_snapshot())

        result = surface.build()
        assert isinstance(result, VolatilitySurfaceSnapshot)


# ---------------------------------------------------------------------------
# backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_snapshot_api_unchanged(self) -> None:
        snapshot = VolatilitySnapshot(
            implied_volatility=0.25,
            historical_volatility=0.20,
            iv_rank=50.0,
            iv_percentile=60.0,
        )

        assert snapshot.implied_volatility == 0.25
        assert snapshot.historical_volatility == 0.20
        assert snapshot.iv_rank == 50.0
        assert snapshot.iv_percentile == 60.0

    def test_snapshot_default_all_none(self) -> None:
        snapshot = VolatilitySnapshot()

        assert snapshot.implied_volatility is None
        assert snapshot.historical_volatility is None
        assert snapshot.iv_rank is None
        assert snapshot.iv_percentile is None
        assert snapshot.volatility_index is None

    def test_snapshot_frozen(self) -> None:
        snapshot = VolatilitySnapshot()

        with pytest.raises(AttributeError):
            snapshot.implied_volatility = 0.5  # type: ignore[misc]

    def test_surface_holds_existing_snapshots(self) -> None:
        s1 = VolatilitySnapshot(implied_volatility=0.20, iv_rank=45.0)
        s2 = VolatilitySnapshot(implied_volatility=0.35, iv_rank=70.0)

        surface = VolatilitySurfaceSnapshot(
            entries=(
                (expiry_30(), s1),
                (expiry_60(), s2),
            )
        )

        assert surface[expiry_30()].implied_volatility == 0.20
        assert surface[expiry_60()].iv_rank == 70.0

    def test_surface_works_with_empty_snapshot(self) -> None:
        empty_snapshot = VolatilitySnapshot()
        full_snapshot = make_snapshot(implied_volatility=0.25)

        surface = VolatilitySurfaceSnapshot(
            entries=(
                (expiry_30(), empty_snapshot),
                (expiry_60(), full_snapshot),
            )
        )

        assert surface[expiry_30()].implied_volatility is None
        assert surface[expiry_60()].implied_volatility == 0.25


# ---------------------------------------------------------------------------
# immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_snapshot_is_frozen(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))

        with pytest.raises(AttributeError):
            surface.entries = ()  # type: ignore[misc]

    def test_nested_snapshots_are_frozen(self) -> None:
        surface = VolatilitySurfaceSnapshot(entries=((expiry_30(), make_snapshot()),))

        with pytest.raises(AttributeError):
            surface[expiry_30()].implied_volatility = 0.99  # type: ignore[misc]

    def test_surface_returns_new_on_build(self) -> None:
        builder = VolatilitySurface()
        builder.add(expiry_30(), make_snapshot())

        snapshot = builder.build()
        builder.add(expiry_60(), make_snapshot())

        assert len(snapshot) == 1
        assert expiry_60() not in snapshot

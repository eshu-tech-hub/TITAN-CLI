from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Self

from titan.options.analytics.models import VolatilitySnapshot


@dataclass(frozen=True, slots=True)
class VolatilitySurfaceSnapshot:
    """Immutable collection of VolatilitySnapshot objects keyed by expiry.

    This is the foundational data structure for the Volatility Surface.
    It stores per-expiry volatility snapshots with validation for:

    - Unique expiries (no duplicate tenors)
    - Chronological ordering (auto-sorted on construction)
    - Non-empty collection (at least one expiry required)

    Future analyzers (Smile, Skew, Term Structure) will consume this
    surface as their primary input without modification to this structure.

    Attributes:
        entries: Sorted tuple of (expiry, snapshot) pairs.
        metadata: Additional surface-level context.
    """

    entries: tuple[tuple[datetime, VolatilitySnapshot], ...] = field(
        default_factory=tuple
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("Surface must contain at least one expiry.")

        seen: set[datetime] = set()
        sorted_entries = sorted(self.entries, key=lambda x: x[0])

        for expiry, snapshot in sorted_entries:
            if not isinstance(expiry, datetime):
                raise TypeError(
                    f"Expiry must be datetime, got {type(expiry).__name__}."
                )
            if not isinstance(snapshot, VolatilitySnapshot):
                raise TypeError(
                    f"Snapshot must be VolatilitySnapshot, "
                    f"got {type(snapshot).__name__}."
                )
            if expiry in seen:
                raise ValueError(f"Duplicate expiry: {expiry}.")
            seen.add(expiry)

        object.__setattr__(self, "entries", tuple(sorted_entries))

    @property
    def expiries(self) -> tuple[datetime, ...]:
        """Chronologically sorted tuple of all expiries."""
        return tuple(entry[0] for entry in self.entries)

    @property
    def snapshots(self) -> tuple[VolatilitySnapshot, ...]:
        """Tuple of snapshots in expiry order."""
        return tuple(entry[1] for entry in self.entries)

    def __getitem__(self, expiry: datetime) -> VolatilitySnapshot:
        """Look up a snapshot by expiry.

        Args:
            expiry: Target expiry to look up.

        Returns:
            VolatilitySnapshot for the given expiry.

        Raises:
            KeyError: If the expiry is not in the surface.
        """
        for e, s in self.entries:
            if e == expiry:
                return s
        raise KeyError(f"Expiry not found: {expiry}.")

    def __contains__(self, expiry: datetime) -> bool:
        """Check if an expiry exists in the surface."""
        return any(e == expiry for e, _ in self.entries)

    def __len__(self) -> int:
        """Number of expiries in the surface."""
        return len(self.entries)

    def __iter__(self) -> Iterator[tuple[datetime, VolatilitySnapshot]]:
        """Iterate over (expiry, snapshot) pairs in chronological order."""
        return iter(self.entries)

    def get(
        self, expiry: datetime, default: VolatilitySnapshot | None = None
    ) -> VolatilitySnapshot | None:
        """Get snapshot for an expiry, returning default if not found.

        Args:
            expiry: Target expiry to look up.
            default: Value to return if expiry is not found.

        Returns:
            The snapshot for the given expiry, or the default.
        """
        for e, s in self.entries:
            if e == expiry:
                return s
        return default

    def to_dict(self) -> dict[str, Any]:
        """Serialize the surface to a JSON-compatible dictionary.

        Returns:
            Dictionary with 'entries' (list of expiry/snapshot dicts)
            and 'metadata'.
        """
        return {
            "entries": [
                {
                    "expiry": expiry.isoformat(),
                    "snapshot": asdict(snapshot),
                }
                for expiry, snapshot in self.entries
            ],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create a VolatilitySurfaceSnapshot from a serialized dictionary.

        Args:
            data: Dictionary returned by ``to_dict()``.

        Returns:
            A new VolatilitySurfaceSnapshot instance with reconstructed
            VolatilitySnapshot objects.
        """
        entries: list[tuple[datetime, VolatilitySnapshot]] = []
        for entry_data in data["entries"]:
            expiry = datetime.fromisoformat(entry_data["expiry"])
            snapshot_data = entry_data["snapshot"]
            snapshot = VolatilitySurfaceSnapshot._reconstruct_snapshot(snapshot_data)
            entries.append((expiry, snapshot))

        metadata = data.get("metadata", {})
        return cls(entries=tuple(entries), metadata=metadata)

    @staticmethod
    def _reconstruct_snapshot(
        data: dict[str, Any],
    ) -> VolatilitySnapshot:
        """Reconstruct a VolatilitySnapshot from a dict, restoring tuple fields."""
        kwargs: dict[str, Any] = dict(data)

        for list_field in (
            "implied_volatilities",
            "historical_volatilities",
        ):
            val = kwargs.get(list_field)
            if isinstance(val, list):
                kwargs[list_field] = tuple(val)

        return VolatilitySnapshot(**kwargs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VolatilitySurfaceSnapshot):
            return NotImplemented
        return self.entries == other.entries and self.metadata == other.metadata

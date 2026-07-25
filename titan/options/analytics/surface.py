from datetime import datetime

from titan.options.analytics.models import VolatilitySnapshot
from titan.options.analytics.surface_models import VolatilitySurfaceSnapshot


class VolatilitySurface:
    """Mutable container for building VolatilitySurfaceSnapshot instances.

    Provides incremental construction with validation. Once finalized via
    ``build()``, returns an immutable ``VolatilitySurfaceSnapshot``.

    This class enables assembling volatility data across expiries from
    different sources before freezing the surface for analysis.

    Attributes:
        name: Identifier for this surface container.
    """

    name = "VolatilitySurface"

    def __init__(self) -> None:
        self._entries: dict[datetime, VolatilitySnapshot] = {}

    def add(self, expiry: datetime, snapshot: VolatilitySnapshot) -> None:
        """Add or replace a volatility snapshot for the given expiry.

        Args:
            expiry: Option expiry datetime.
            snapshot: Volatility data for this expiry.

        Raises:
            TypeError: If expiry is not datetime or snapshot is not
                VolatilitySnapshot.
        """
        if not isinstance(expiry, datetime):
            raise TypeError(f"expiry must be datetime, got {type(expiry).__name__}.")
        if not isinstance(snapshot, VolatilitySnapshot):
            raise TypeError(
                f"snapshot must be VolatilitySnapshot, "
                f"got {type(snapshot).__name__}."
            )
        self._entries[expiry] = snapshot

    def remove(self, expiry: datetime) -> None:
        """Remove the snapshot for the given expiry.

        Args:
            expiry: Expiry to remove.

        Raises:
            KeyError: If the expiry is not in the surface.
        """
        if expiry not in self._entries:
            raise KeyError(f"Expiry not found: {expiry}.")
        del self._entries[expiry]

    def clear(self) -> None:
        """Remove all entries from the surface."""
        self._entries.clear()

    @property
    def expiries(self) -> tuple[datetime, ...]:
        """Chronologically sorted tuple of expiries."""
        return tuple(sorted(self._entries.keys()))

    @property
    def count(self) -> int:
        """Number of expiries currently in the surface."""
        return len(self._entries)

    def get(self, expiry: datetime) -> VolatilitySnapshot | None:
        """Get snapshot for an expiry, returning None if not found.

        Args:
            expiry: Target expiry to look up.

        Returns:
            The VolatilitySnapshot for the expiry, or None.
        """
        return self._entries.get(expiry)

    def build(self) -> VolatilitySurfaceSnapshot:
        """Build and return an immutable VolatilitySurfaceSnapshot.

        Validates that the surface is non-empty and all expiries are
        unique. The returned snapshot auto-sorts entries chronologically.

        Returns:
            A validated, immutable surface snapshot.

        Raises:
            ValueError: If the surface has no entries.
        """
        if not self._entries:
            raise ValueError("Cannot build surface with no entries.")

        sorted_pairs = sorted(self._entries.items(), key=lambda x: x[0])
        return VolatilitySurfaceSnapshot(entries=tuple(sorted_pairs))

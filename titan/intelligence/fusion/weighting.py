from abc import ABC, abstractmethod
from collections.abc import Sequence

from titan.core.evidence.evidence import Evidence
from titan.core.evidence.models import EvidenceCategory
from titan.intelligence.fusion.models import EvidenceWeight


class WeightProvider(ABC):
    """Abstract weight provider for the Fusion Engine.

    Subclass to implement custom weighting strategies:
      - StaticWeightProvider: fixed per-category weights.
      - Dynamic weight providers (future): adapt weights based on state.
      - Regime-dependent weight providers (future): adjust per market regime.
      - User-defined weight providers (future): from external configuration.
    """

    @abstractmethod
    def get_weight(self, evidence: Evidence) -> float:
        """Return the weight for a single evidence item.

        Args:
            evidence: The evidence item to weight.

        Returns:
            Non-negative weight value.
        """


class EqualWeightProvider(WeightProvider):
    """Default weight provider that assigns equal weight to all evidence."""

    def get_weight(self, evidence: Evidence) -> float:
        return 1.0


class StaticWeightProvider(WeightProvider):
    """Weight provider with fixed per-category weights.

    Args:
        weights: Sequence of EvidenceWeight configurations.
    """

    def __init__(self, weights: Sequence[EvidenceWeight]) -> None:
        self._weights: dict[EvidenceCategory, EvidenceWeight] = {
            w.category: w for w in weights
        }

    def get_weight(self, evidence: Evidence) -> float:
        weight = self._weights.get(evidence.category)

        if weight is None or not weight.enabled:
            return 0.0

        return weight.weight

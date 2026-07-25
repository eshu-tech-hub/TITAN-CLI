from abc import ABC, abstractmethod

from titan.options.analytics.models import AnalysisResult, OptionChainSnapshot


class OptionAnalyzer(ABC):
    """Abstract base class for option-chain analytics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the analyzer name."""

    def analyze(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Analyze an option-chain snapshot.

        Args:
            snapshot: Broker-independent option-chain snapshot.

        Returns:
            Analysis result for the snapshot.
        """

        return self._placeholder_result(snapshot)

    def _validate_snapshot(self, snapshot: OptionChainSnapshot) -> None:
        """Validate that the analyzer received a snapshot model.

        Args:
            snapshot: Candidate snapshot.

        Raises:
            TypeError: If snapshot is not an OptionChainSnapshot.
            ValueError: If required snapshot fields are empty.
        """

        if not isinstance(snapshot, OptionChainSnapshot):
            raise TypeError("snapshot must be an OptionChainSnapshot.")
        if not snapshot.underlying.strip():
            raise ValueError("snapshot underlying cannot be empty.")

    def _placeholder_result(self, snapshot: OptionChainSnapshot) -> AnalysisResult:
        """Return a neutral placeholder result after snapshot validation.

        Args:
            snapshot: Broker-independent option-chain snapshot.

        Returns:
            Neutral placeholder analysis result.
        """

        self._validate_snapshot(snapshot)
        return AnalysisResult.neutral_placeholder(self.name)

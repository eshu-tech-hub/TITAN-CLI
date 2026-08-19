from unittest.mock import MagicMock, patch

import pytest

from titan.core.exceptions import ConfigurationError
from titan.deployment.startup import ProductionBootstrapper


def test_bootstrapper_success():
    """Verify the bootstrapper calls readiness checks before starting the engine."""
    mock_engine = MagicMock()
    bootstrapper = ProductionBootstrapper(engine=mock_engine)

    with patch(
        "titan.deployment.startup.ProductionReadinessReview.run_pre_flight_checks"
    ) as mock_review:
        bootstrapper.boot()
        mock_review.assert_called_once()
        mock_engine.start.assert_called_once()


def test_bootstrapper_fail_fast():
    """Verify the bootstrapper aborts completely if pre-flight checks fail."""
    mock_engine = MagicMock()
    bootstrapper = ProductionBootstrapper(engine=mock_engine)

    with patch(
        "titan.deployment.startup.ProductionReadinessReview.run_pre_flight_checks",
        side_effect=ConfigurationError("Fail"),
    ):
        with pytest.raises(ConfigurationError):
            bootstrapper.boot()

        # Ensure the engine is never started if readiness fails
        mock_engine.start.assert_not_called()

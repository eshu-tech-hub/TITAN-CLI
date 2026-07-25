from unittest.mock import MagicMock, patch

from titan.config.manager import ConfigManager
from titan.config.validators import (
    ConfigurationValidator,
    EnvironmentValidator,
    DirectoryValidator,
)
from titan.config.validation_models import ValidationLevel


def test_environment_validator_python_version():
    # Mock sys.version_info to simulate old python
    with patch("sys.version_info", (3, 10)):
        results = EnvironmentValidator.validate()
        assert len(results) == 1
        assert results[0].level == ValidationLevel.ERROR
        assert "Python 3.14+" in results[0].message


def test_directory_validator_missing_dirs():
    manager = MagicMock(spec=ConfigManager)

    with patch("pathlib.Path.exists", return_value=False):
        results = DirectoryValidator.validate(manager)
        # Should generate WARNINGS for all missing dirs
        assert all(r.level == ValidationLevel.WARNING for r in results)
        assert len(results) == 5  # config, logs, data, reports, checkpoints


def test_configuration_validator_master_report():
    manager = MagicMock(spec=ConfigManager)
    type(manager).profile = None

    validator = ConfigurationValidator(manager)
    report = validator.validate_all()

    # Since profile is missing, it should be an ERROR
    assert not report.is_valid
    assert len(report.blocking_errors) >= 1
    assert any(
        "active configuration profile" in e.message for e in report.blocking_errors
    )

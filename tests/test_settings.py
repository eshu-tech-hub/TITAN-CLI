import pytest

from titan.config.settings import Settings
from titan.core.exceptions import ConfigurationError


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANGEL_API_KEY", raising=False)

    with pytest.raises(ConfigurationError):
        Settings().angel_api_key


def test_missing_client_id(monkeypatch):
    monkeypatch.delenv("ANGEL_CLIENT_ID", raising=False)

    with pytest.raises(ConfigurationError):
        Settings().angel_client_id
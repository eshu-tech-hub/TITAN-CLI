import pytest

SmartConnect = pytest.importorskip("SmartApi").SmartConnect


def test_import():
    api = SmartConnect(api_key="TEST")
    assert api is not None

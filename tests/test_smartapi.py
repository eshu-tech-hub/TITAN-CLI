from SmartApi import SmartConnect


def test_import():
    api = SmartConnect(api_key="TEST")
    assert api is not None

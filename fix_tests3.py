
path = 'tests/test_tui_runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if "from unittest.mock import patch" not in content and "from unittest.mock import MagicMock, patch" not in content:
    content = content.replace("from unittest.mock import MagicMock", "from unittest.mock import MagicMock, patch")

target = """    def test_refresh_state_without_builder(self) -> None:
        screen = RuntimeScreen()
        screen._refresh_state()
        assert screen.state.engine.status == "Unknown\""""

replacement = """    @patch("titan.runtime.local_transport.LocalTransport.status", side_effect=ConnectionRefusedError)
    def test_refresh_state_without_builder(self, mock_status) -> None:
        screen = RuntimeScreen()
        screen._refresh_state()
        assert screen.state.engine.status == "Unknown\""""

content = content.replace(target, replacement)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

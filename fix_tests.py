
path = 'tests/test_tui_dashboard.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def test_refresh_state_without_builder(self) -> None:
        screen = DashboardScreen()
        screen._refresh_state()
        assert screen.state.runtime.status == "Unknown\""""

replacement = """    @patch("titan.runtime.local_transport.LocalTransport.status", side_effect=ConnectionRefusedError)
    def test_refresh_state_without_builder(self, mock_status) -> None:
        screen = DashboardScreen()
        screen._refresh_state()
        assert screen.state.runtime.status == "Unknown\""""

content = content.replace(target, replacement)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

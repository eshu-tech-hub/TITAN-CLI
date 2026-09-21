import re

rt_path = 'titan/tui/screens/runtime.py'
with open(rt_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_rt_refresh = """    def _refresh_state(self) -> None:
        if getattr(self, "_state_builder", None) is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = RuntimeScreenState()
        else:
            from titan.tui.layout import _get_runtime_data, build_runtime_state
            raw_data = _get_runtime_data()
            if raw_data:
                self._state = build_runtime_state(raw_data)
            else:
                self._state = RuntimeScreenState()
        self._update_widgets()
        self._update_refresh_indicator()"""

content = re.sub(r"    def _refresh_state\(self\) -> None:[\s\S]*?(?=\n    def _update_widgets)", new_rt_refresh, content)
with open(rt_path, 'w', encoding='utf-8') as f:
    f.write(content)

db_path = 'titan/tui/screens/dashboard.py'
with open(db_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_db_refresh = """    def _refresh_state(self) -> None:
        if getattr(self, "_state_builder", None) is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = DashboardState()
        else:
            from titan.tui.layout import _get_dashboard_data, build_dashboard_state
            raw_data = _get_dashboard_data()
            if raw_data:
                self._state = build_dashboard_state(raw_data)
            else:
                self._state = DashboardState()
        self._update_widgets()
        self._update_refresh_indicator()"""

content = re.sub(r"    def _refresh_state\(self\) -> None:[\s\S]*?(?=\n    def _update_widgets)", new_db_refresh, content)
with open(db_path, 'w', encoding='utf-8') as f:
    f.write(content)

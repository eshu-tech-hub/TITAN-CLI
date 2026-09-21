
layout_path = 'titan/tui/layout.py'
with open(layout_path, 'r', encoding='utf-8') as f:
    content = f.read()

getters = """
def _get_runtime_data():
    def _fetch_runtime_ipc():
        from titan.runtime.local_transport import LocalTransport
        try:
            client = LocalTransport()
            return client.status()
        except Exception as e:
            with open("tui_ipc_debug.log", "a") as f:
                f.write(f"Runtime IPC Error: {type(e).__name__}: {e}\\n")
            raise

    try:
        from titan.tui.layout import _ipc_executor
        future = _ipc_executor.submit(_fetch_runtime_ipc)
        return future.result(timeout=1.0)
    except TimeoutError:
        return None

def _get_dashboard_data():
    def _fetch_dashboard_ipc():
        from titan.runtime.local_transport import LocalTransport
        try:
            client = LocalTransport()
            return client.status()
        except Exception as e:
            with open("tui_ipc_debug.log", "a") as f:
                f.write(f"Dashboard IPC Error: {type(e).__name__}: {e}\\n")
            raise

    try:
        from titan.tui.layout import _ipc_executor
        future = _ipc_executor.submit(_fetch_dashboard_ipc)
        return future.result(timeout=1.0)
    except TimeoutError:
        return None

"""
if "def _get_runtime_data" not in content:
    content = content.replace("def _get_paper_data", getters + "def _get_paper_data")

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)

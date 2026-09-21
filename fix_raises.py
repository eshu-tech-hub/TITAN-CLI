
layout_path = 'titan/tui/layout.py'
with open(layout_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("            raise\n\n    try:\n        from titan.tui.layout import _ipc_executor\n        future = _ipc_executor.submit(_fetch_runtime_ipc)", "            return None\n\n    try:\n        from titan.tui.layout import _ipc_executor\n        future = _ipc_executor.submit(_fetch_runtime_ipc)")
content = content.replace("            raise\n\n    try:\n        from titan.tui.layout import _ipc_executor\n        future = _ipc_executor.submit(_fetch_dashboard_ipc)", "            return None\n\n    try:\n        from titan.tui.layout import _ipc_executor\n        future = _ipc_executor.submit(_fetch_dashboard_ipc)")

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)

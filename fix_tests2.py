
path = 'tests/test_tui_dashboard.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if "from unittest.mock import patch" not in content and "from unittest.mock import MagicMock, patch" not in content:
    content = content.replace("from unittest.mock import MagicMock", "from unittest.mock import MagicMock, patch")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

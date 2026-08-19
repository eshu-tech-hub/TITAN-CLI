import re

files = [
    'titan/events/risk.py',
    'titan/execution/router.py',
    'titan/execution/state.py',
    'titan/logging/context.py',
    'titan/logging/formatter.py',
    'titan/tui/layout.py',
    'titan/tui/screens/ai_assistant.py',
    'titan/tui/screens/help.py',
    'titan/tui/screens/market.py'
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Import ClassVar if missing
    if 'ClassVar' not in content:
        if 'from typing import ' in content:
            content = re.sub(r'from typing import (.*)', r'from typing import ClassVar, \1', content, count=1)
        else:
            content = content.replace('from __future__ import annotations\n', 'from __future__ import annotations\n\nfrom typing import ClassVar\n')

    # Specific replacements
    content = re.sub(r'RISK_BY_IMPORTANCE: dict', 'RISK_BY_IMPORTANCE: ClassVar[dict', content)
    content = re.sub(r'_STATUS_MAP: dict', '_STATUS_MAP: ClassVar[dict', content)
    content = re.sub(r'_TRANSITIONS: dict', '_TRANSITIONS: ClassVar[dict', content)
    content = re.sub(r'_TERMINAL_STATES: frozenset', '_TERMINAL_STATES: ClassVar[frozenset', content)
    content = re.sub(r'_FIELDS = \{', '_FIELDS: ClassVar[dict] = {', content)
    content = re.sub(r'_LEVEL_COLORS: dict', '_LEVEL_COLORS: ClassVar[dict', content)
    
    # Textual BINDINGS and DEFAULT_CSS for the new files
    if file not in ['titan/tui/screens/market.py']:
        content = re.sub(r'\bBINDINGS\s*=\s*\[', 'BINDINGS: ClassVar[list] = [', content)
        content = re.sub(r'\bDEFAULT_CSS\s*=\s*([\"\'\w]+)', r'DEFAULT_CSS: ClassVar[str] = \1', content)

    # For market.py, fix the ClassVar[list] issue if it was typed differently by textual
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

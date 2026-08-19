import re

files = [
    'titan/tui/screens/audit.py',
    'titan/tui/screens/configuration.py',
    'titan/tui/screens/dashboard.py',
    'titan/tui/screens/decision.py',
    'titan/tui/screens/decision_replay.py',
    'titan/tui/screens/live.py',
    'titan/tui/screens/market.py',
    'titan/tui/screens/monitor.py',
    'titan/tui/screens/paper.py',
    'titan/tui/screens/portfolio.py',
    'titan/tui/screens/portfolio_replay.py',
    'titan/tui/screens/runtime.py',
    'titan/tui/screens/strategy_eval.py',
    'titan/tui/screens/trade_journal.py',
    'titan/tui/shell.py',
    'titan/tui/widgets/sidebar.py'
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

    # Add ClassVar to BINDINGS
    content = re.sub(r'\bBINDINGS\s*=\s*\[', 'BINDINGS: ClassVar[list] = [', content)
    # Add ClassVar to SECTIONS
    content = re.sub(r'\bSECTIONS\s*=\s*\[', 'SECTIONS: ClassVar[list] = [', content)
    # Add ClassVar to DEFAULT_CSS
    content = re.sub(r'\bDEFAULT_CSS\s*=\s*([\"\'\w]+)', r'DEFAULT_CSS: ClassVar[str] = \1', content)
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

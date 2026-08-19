import re

files = [
    'titan/analysis/factory.py',
    'titan/brokers/angelone/history.py',
    'titan/events/entities.py',
    'titan/events/impact.py'
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
    content = re.sub(r'_registry: dict', '_registry: ClassVar[dict', content)
    content = re.sub(r'_INTERVAL_MAP: dict', '_INTERVAL_MAP: ClassVar[dict', content)
    content = re.sub(r'ENTITY_MAP: list', 'ENTITY_MAP: ClassVar[list', content)
    content = re.sub(r'VOLATILITY_MAP: dict', 'VOLATILITY_MAP: ClassVar[dict', content)
    content = re.sub(r'LIQUIDITY_MAP: dict', 'LIQUIDITY_MAP: ClassVar[dict', content)
    content = re.sub(r'GAP_RISK_MAP: dict', 'GAP_RISK_MAP: ClassVar[dict', content)
    content = re.sub(r'DURATION_MAP: dict', 'DURATION_MAP: ClassVar[dict', content)
    content = re.sub(r'ASSET_MAP: dict', 'ASSET_MAP: ClassVar[dict', content)
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

import re

files = [
    'tests/test_trade_pipeline.py',
    'titan/analysis/pipeline.py',
    'titan/validation/runner.py'
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Import UTC if missing
    if 'UTC' not in content:
        if 'from datetime import ' in content:
            content = re.sub(r'from datetime import (.*)', r'from datetime import UTC, \1', content, count=1)
        else:
            content = "from datetime import UTC\n" + content

    # Replace datetime.utcnow() with datetime.now(UTC)
    content = content.replace('datetime.utcnow()', 'datetime.now(UTC)')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

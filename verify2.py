import os
import re

pattern = re.compile(r'(?i)angelone|angel_one|smartapi|smart_api|AngelOne')
found = False
for root, _, files in os.walk('.'):
    if '.git' in root or '.pytest_cache' in root or '__pycache__' in root or root == '.': continue
    for file in files:
        if file.endswith(('.py', '.toml', '.md', '.env')):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if pattern.search(line):
                        print(f"Found in {path}")
                        found = True
                        break
if not found:
    print("Zero matches for Angel One / SmartAPI")

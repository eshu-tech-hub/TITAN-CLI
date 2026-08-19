import re

file_path = 'titan/tui/layout.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace all blind xcept Exception: that return fallback state objects or empty tuples
text = re.sub(
    r'except Exception:',
    r'except (RuntimeError, OSError, ValueError, TypeError, AttributeError, KeyError):',
    text
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

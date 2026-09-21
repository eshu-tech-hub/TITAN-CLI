
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    _gemini_last_called: dict[str, float] = field(default_factory=dict, init=False)"""
replacement = """    _gemini_last_called: dict[str, float] = field(default_factory=dict, init=False)
    _ai_enabled: bool = field(default=False, init=False)"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

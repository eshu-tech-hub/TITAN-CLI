
path = 'titan/ai/providers/gemini.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        model_name: str = "gemini-3.6-flash","""
replacement = """        model_name: str = "gemini-2.5-flash","""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

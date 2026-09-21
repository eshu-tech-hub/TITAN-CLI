
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("f.write(f\"Stream Start Error: {traceback.format_exc()}\n\")", "f.write(f\"Stream Start Error: {traceback.format_exc()}\\n\")")
content = content.replace("f.write(f\"Runtime Start Error: {traceback.format_exc()}\n\")", "f.write(f\"Runtime Start Error: {traceback.format_exc()}\\n\")")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

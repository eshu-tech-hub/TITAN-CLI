
path = 'titan/cli/commands/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    engine = get_runtime_engine()
    if symbol:
        engine.target_symbol = symbol.upper()"""

replacement = """    engine = get_runtime_engine()
    if symbols:
        engine.watchlist = [s.upper() for s in symbols]"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

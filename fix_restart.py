
path = 'titan/cli/commands/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    logger.info("Runtime restart command executed")
    engine = get_runtime_engine()
    if symbols:
        engine.watchlist = [s.upper() for s in symbols]
    service = RuntimeService(engine)"""

replacement = """    logger.info("Runtime restart command executed")
    engine = get_runtime_engine()
    service = RuntimeService(engine)"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

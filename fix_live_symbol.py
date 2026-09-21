
path = 'titan/cli/commands/live.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        set_runtime_engine(engine)
        engine.start()"""

replacement1 = """        set_runtime_engine(engine)
        engine.target_symbol = symbol.upper()
        engine.start()"""

content = content.replace(target1, replacement1)

target2 = """            set_runtime_engine(engine)
            engine.start()"""

replacement2 = """            set_runtime_engine(engine)
            engine.target_symbol = symbol.upper()
            engine.start()"""

content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

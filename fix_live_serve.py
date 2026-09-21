
path = 'titan/cli/commands/live.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        engine = RuntimeEngine(
            broker=broker,
            pipeline=pipeline,
            target_symbol=symbol.upper(),
            target_exchange=exchange.upper(),
        )
        server = LocalTransportServer(RuntimeService(engine))
        try:
            engine.target_symbol = symbol.upper()"""

replacement = """        engine = RuntimeEngine(
            broker=broker,
            pipeline=pipeline,
            watchlist=[s.upper() for s in symbols] if symbols else ["RELIANCE"],
            target_exchange=exchange.upper(),
        )
        server = LocalTransportServer(RuntimeService(engine))
        try:
            engine.watchlist = [s.upper() for s in symbols] if symbols else ["RELIANCE"]"""

content = content.replace(target, replacement)

target2 = """            engine = RuntimeEngine(
                broker=broker,
                pipeline=pipeline,
                target_symbol=symbol.upper(),
                target_exchange=exchange.upper(),
            )
            server = LocalTransportServer(RuntimeService(engine))
            try:
                engine.target_symbol = symbol.upper()"""

replacement2 = """            engine = RuntimeEngine(
                broker=broker,
                pipeline=pipeline,
                watchlist=[s.upper() for s in symbols] if symbols else ["RELIANCE"],
                target_exchange=exchange.upper(),
            )
            server = LocalTransportServer(RuntimeService(engine))
            try:
                engine.watchlist = [s.upper() for s in symbols] if symbols else ["RELIANCE"]"""

content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

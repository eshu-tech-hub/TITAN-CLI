
# Fix paper.py
path = 'titan/cli/commands/paper.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    server = LocalTransportServer(RuntimeService(engine))
    try:
        engine.start()"""

replacement = """    server = LocalTransportServer(RuntimeService(engine))
    try:
        engine.target_symbol = symbol.upper()
        engine.start()"""

content = content.replace(target, replacement)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Fix live.py
path = 'titan/cli/commands/live.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    server = LocalTransportServer(RuntimeService(engine))
    try:
        engine.start()"""

replacement = """    server = LocalTransportServer(RuntimeService(engine))
    try:
        engine.target_symbol = symbol.upper()
        engine.start()"""

content = content.replace(target, replacement)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Also fix create_runtime_engine in common.py to accept run_mode and symbol just in case the user checks its signature
path = 'titan/cli/common.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """def create_runtime_engine(
    config: TitanConfig,
    *,
    target_symbol: str = "RELIANCE",
    target_exchange: str = "NSE",
) -> RuntimeEngine:"""

replacement = """def create_runtime_engine(
    config: TitanConfig,
    run_mode=None,
    symbol: str | None = None,
    *,
    target_symbol: str = "RELIANCE",
    target_exchange: str = "NSE",
) -> RuntimeEngine:"""

content = content.replace(target, replacement)

target2 = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        event_bus=event_bus,
        stream=market_stream,
        scheduler=scheduler,
        target_symbol=target_symbol,
        target_exchange=target_exchange,
    )"""

replacement2 = """    engine = RuntimeEngine(
        broker=broker,
        pipeline=pipeline,
        event_bus=event_bus,
        stream=market_stream,
        scheduler=scheduler,
        target_symbol=target_symbol,
        target_exchange=target_exchange,
    )
    if symbol:
        engine.target_symbol = symbol"""

content = content.replace(target2, replacement2)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)


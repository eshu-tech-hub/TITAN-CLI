
# 1. Update models.py
path1 = 'titan/runtime/models.py'
with open(path1, 'r', encoding='utf-8') as f:
    content1 = f.read()

target1 = """class MarketStatus:
    stream_status: str = "disconnected"
    active_subscriptions: int = 0
    last_quote_time: datetime | None = None"""

replacement1 = """class MarketStatus:
    stream_status: str = "disconnected"
    active_subscriptions: int = 0
    last_quote_time: datetime | None = None
    stream_connected: bool = False
    symbols: tuple[str, ...] = field(default_factory=tuple)"""

content1 = content1.replace(target1, replacement1)
with open(path1, 'w', encoding='utf-8') as f:
    f.write(content1)


# 2. Update runtime.py
path2 = 'titan/runtime/runtime.py'
with open(path2, 'r', encoding='utf-8') as f:
    content2 = f.read()

target2 = """        market_status = MarketStatus(
            stream_status=stream_status_str,
            active_subscriptions=self.subscriptions.count(),
            last_quote_time=(
                self.stream.last_quote_time if self.stream is not None else None
            ),
        )"""

replacement2 = """        market_status = MarketStatus(
            stream_status=stream_status_str,
            active_subscriptions=self.subscriptions.count(),
            last_quote_time=(
                self.stream.last_quote_time if self.stream is not None else None
            ),
            stream_connected=getattr(self.stream, 'connected', getattr(self.stream, 'is_connected', False)) if self.stream else False,
            symbols=tuple(getattr(self.stream, 'symbols', getattr(self.stream, 'subscribed_symbols', []))) if self.stream else (),
        )"""

content2 = content2.replace(target2, replacement2)
with open(path2, 'w', encoding='utf-8') as f:
    f.write(content2)


# 3. Update local_transport.py
path3 = 'titan/runtime/local_transport.py'
with open(path3, 'r', encoding='utf-8') as f:
    content3 = f.read()

target3 = """        market = MarketStatus(
            stream_status=data.get("market", {}).get("stream_status", "disconnected"),
            active_subscriptions=data.get("market", {}).get("active_subscriptions", 0),
            last_quote_time=parse_dt(data.get("market", {}).get("last_quote_time")),
        )"""

replacement3 = """        market = MarketStatus(
            stream_status=data.get("market", {}).get("stream_status", "disconnected"),
            active_subscriptions=data.get("market", {}).get("active_subscriptions", 0),
            last_quote_time=parse_dt(data.get("market", {}).get("last_quote_time")),
            stream_connected=data.get("market", {}).get("stream_connected", False),
            symbols=tuple(data.get("market", {}).get("symbols", [])),
        )"""

content3 = content3.replace(target3, replacement3)
with open(path3, 'w', encoding='utf-8') as f:
    f.write(content3)

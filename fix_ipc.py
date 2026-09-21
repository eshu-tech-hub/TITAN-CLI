
path = 'titan/ipc/models.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'from pydantic import Field' not in content:
    content = content.replace('from pydantic import BaseModel', 'from pydantic import BaseModel, Field')

target = """class PaperSessionPayload(BaseModel):
    running: bool
    connected: bool
    session_uptime_seconds: float
    start_time: datetime | None"""

replacement = """class PaperSessionPayload(BaseModel):
    running: bool
    connected: bool
    stream_connected: bool = False
    stream_symbols: list[str] = Field(default_factory=list)
    session_uptime_seconds: float
    start_time: datetime | None"""

content = content.replace(target, replacement)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

path2 = 'titan/runtime/local_transport.py'
with open(path2, 'r', encoding='utf-8') as f:
    content2 = f.read()

target2 = """        session_payload = PaperSessionPayload(
            running=self.service.engine.is_running,
            connected=broker.is_connected(),
            session_uptime_seconds=self.service.engine.uptime_seconds,
            start_time=getattr(self.service.engine, "_start_time", datetime.now(UTC)),
        )"""

replacement2 = """        session_payload = PaperSessionPayload(
            running=self.service.engine.is_running,
            connected=broker.is_connected(),
            stream_connected=getattr(self.service.engine.stream, 'connected', getattr(self.service.engine.stream, 'is_connected', False)),
            stream_symbols=getattr(self.service.engine.stream, 'symbols', getattr(self.service.engine.stream, 'subscribed_symbols', [])),
            session_uptime_seconds=self.service.engine.uptime_seconds,
            start_time=getattr(self.service.engine, "_start_time", datetime.now(UTC)),
        )"""

content2 = content2.replace(target2, replacement2)
with open(path2, 'w', encoding='utf-8') as f:
    f.write(content2)

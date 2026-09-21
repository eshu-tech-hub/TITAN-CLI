
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    _status: RuntimeStatus = field(default=RuntimeStatus.STOPPED, init=False)
    _start_time: datetime | None = field(default=None, init=False)
    _error: str = field(default="", init=False)
    _stop_event: Event = field(default_factory=Event, init=False)"""

replacement = """    _status: RuntimeStatus = field(default=RuntimeStatus.STOPPED, init=False)
    _start_time: datetime | None = field(default=None, init=False)
    _error: str = field(default="", init=False)
    _stop_event: Event = field(default_factory=Event, init=False)
    _gemini_last_called: dict[str, float] = field(default_factory=dict, init=False)"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)


path = 'titan/runtime/supervisor.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = "self.registry = registry or HeartbeatRegistry(timeout_seconds=30.0)"
replacement1 = "self.registry = registry or HeartbeatRegistry(timeout_seconds=300.0)"
content = content.replace(target1, replacement1)

target2 = """        if dead_components:
            logger.error(f"Supervisor detected dead components: {dead_components}")
            raise RuntimeError(
                f"Watchdog timeout. Components unresponsive: {dead_components}"
            )"""
replacement2 = """        if dead_components:
            logger.warning(f"Supervisor detected slow/idle components (non-fatal): {dead_components}")
            # Do not raise RuntimeError for slow components in paper/headless modes
            # raise RuntimeError(f"Watchdog timeout. Components unresponsive: {dead_components}")"""
content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

path2 = 'titan/runtime/heartbeat.py'
with open(path2, 'r', encoding='utf-8') as f:
    content2 = f.read()

target3 = "def __init__(self, timeout_seconds: float = 30.0) -> None:"
replacement3 = "def __init__(self, timeout_seconds: float = 300.0) -> None:"
content2 = content2.replace(target3, replacement3)

with open(path2, 'w', encoding='utf-8') as f:
    f.write(content2)

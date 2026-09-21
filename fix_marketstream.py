import re

path = 'titan/runtime/stream.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add is_connected
is_connected_prop = """
    @property
    def is_connected(self) -> bool:
        if hasattr(self.source, "is_connected"):
            return self.source.is_connected()
        return getattr(self.source, "_connected", False)

"""
if "def is_connected(self) -> bool:" not in content.split("class MarketStream:")[1]:
    content = content.replace("    def is_running(self) -> bool:", is_connected_prop + "    @property\n    def is_running(self) -> bool:")

# 2. Modify start()
start_code = """    def start(self) -> None:
        \"\"\"Start the market stream in a background thread.\"\"\"
        if self._thread is not None and self._thread.is_alive():
            raise StreamError("Market stream is already running.")

        if hasattr(self.source, "start"):
            self.source.start()

        self._stop_event.clear()
        self._reconnect_attempts = 0
        self._quote_count = 0

        self._thread = threading.Thread(
            target=self._run,
            name="MarketStreamThread",
            daemon=True,
        )
        self._thread.start()"""

content = re.sub(r"    def start\(self\) -> None:[\s\S]*?(?=\n    def stop)", start_code, content)

# 3. Modify stop()
stop_code = """    def stop(self) -> None:
        \"\"\"Gracefully stop the market stream.\"\"\"
        self._stop_event.set()
        
        if hasattr(self.source, "stop"):
            self.source.stop()

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("Market stream thread did not cleanly exit.")
            self._thread = None"""

content = re.sub(r"    def stop\(self\) -> None:[\s\S]*?(?=\n    @property\n    def is_running)", stop_code, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

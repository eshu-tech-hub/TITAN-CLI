
path = 'titan/runtime/local_transport.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    def _publish_status_event(self, event) -> None:
        if self.publisher and not self._stop_event.is_set():
            try:
                status = self._build_paper_status()
                self.publisher.publish("paper.status", status)
            except Exception:  # noqa: BLE001, S110
                pass"""

replacement1 = """    def _publish_status_event(self, event) -> None:
        if self.publisher and not self._stop_event.is_set():
            try:
                status = self._build_paper_status()
                self.publisher.publish("paper.status", status)
            except Exception:  # noqa: BLE001, S110
                pass

    def _publish_trade_event(self, event) -> None:
        if self.publisher and not self._stop_event.is_set():
            try:
                self.publisher.publish("paper.trade", event.data)
            except Exception:  # noqa: BLE001, S110
                pass"""
content = content.replace(target1, replacement1)

target2 = """        self.service.engine.event_bus.subscribe(
            RuntimeEventType.PIPELINE_EXECUTED, self._publish_status_event
        )"""

replacement2 = """        self.service.engine.event_bus.subscribe(
            RuntimeEventType.PIPELINE_EXECUTED, self._publish_status_event
        )
        self.service.engine.event_bus.subscribe(
            RuntimeEventType.TRADE_EXECUTED, self._publish_trade_event
        )"""
content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

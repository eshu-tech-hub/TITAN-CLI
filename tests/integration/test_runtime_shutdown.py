import threading
import time
from unittest.mock import MagicMock
from titan.runtime.runtime import RuntimeEngine
from titan.runtime.models import RuntimeStatus


def test_runtime_engine_shutdown():
    broker_mock = MagicMock()
    from titan.brokers.models import ConnectionStatus

    broker_mock.connect.return_value = ConnectionStatus.CONNECTED
    engine = RuntimeEngine(broker=broker_mock)

    t = threading.Thread(target=engine.start, daemon=True)
    t.start()

    time.sleep(0.5)
    assert engine.status == RuntimeStatus.RUNNING
    engine.stop()
    t.join(timeout=2.0)
    assert engine.status == RuntimeStatus.STOPPED

import threading
from unittest.mock import MagicMock

from titan.runtime.models import RuntimeStatus
from titan.runtime.runtime import RuntimeEngine


def test_runtime_engine_shutdown():
    broker_mock = MagicMock()
    from titan.brokers.models import ConnectionStatus

    broker_mock.connect.return_value = ConnectionStatus.CONNECTED
    engine = RuntimeEngine(broker=broker_mock)

    engine.start()
    t = threading.Thread(target=engine.run_until_stopped)
    t.start()

    assert engine.status == RuntimeStatus.RUNNING
    engine.stop()
    t.join(timeout=2.0)
    assert engine.status == RuntimeStatus.STOPPED

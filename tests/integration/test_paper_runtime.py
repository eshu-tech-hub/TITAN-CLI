import time
import threading
from unittest.mock import MagicMock
from titan.runtime.runtime import RuntimeEngine
from titan.brokers.models import ConnectionStatus

from titan.runtime.service import RuntimeService


def test_paper_runtime_enabling():
    broker_mock = MagicMock()
    broker_mock.connect.return_value = ConnectionStatus.CONNECTED
    engine = RuntimeEngine(broker=broker_mock)
    service = RuntimeService(engine)
    t = threading.Thread(target=service.start, daemon=True)
    t.start()

    time.sleep(0.5)
    # enable_paper is currently a stub, so just test it executes without error
    service.enable_paper()
    service.disable_paper()
    service.stop()
    t.join(timeout=2.0)

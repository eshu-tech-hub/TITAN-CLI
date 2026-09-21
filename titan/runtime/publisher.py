"""ZMQ Pub/Sub state publisher."""

import zmq
from pydantic import BaseModel

from titan.core.logger import logger


class StatePublisher:
    """ZMQ Publisher for system state."""

    _instance = None

    def __new__(cls, *args, **kwargs):  # type: ignore
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, bind_addr: str = "tcp://127.0.0.1:55556") -> None:
        if getattr(self, "_initialized", False):
            return
            
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(bind_addr)
        self._initialized = True
        logger.info(f"StatePublisher bound to {bind_addr}")

    def publish(self, topic: bytes | str, payload: BaseModel | dict) -> None:
        """Publish a Pydantic model or dict to a specific topic."""
        import json
        try:
            if isinstance(topic, str):
                topic = topic.encode("utf-8")
            if hasattr(payload, "model_dump_json"):
                json_bytes = payload.model_dump_json().encode("utf-8")
            else:
                json_bytes = json.dumps(payload).encode("utf-8")
            self.socket.send_multipart([topic, json_bytes])
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to publish to {topic!r}: {e}")

    def close(self) -> None:
        """Close the publisher socket."""
        try:
            self.socket.close(linger=0)
            self._initialized = False
        except Exception:  # noqa: BLE001
            pass

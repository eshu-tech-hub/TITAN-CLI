
path = 'titan/runtime/publisher.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def publish(self, topic: bytes | str, payload: BaseModel) -> None:
        \"\"\"Publish a Pydantic model to a specific topic.\"\"\"
        try:
            if isinstance(topic, str):
                topic = topic.encode("utf-8")
            json_bytes = payload.model_dump_json().encode("utf-8")
            self.socket.send_multipart([topic, json_bytes])
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to publish to {topic!r}: {e}")"""

replacement = """    def publish(self, topic: bytes | str, payload: BaseModel | dict) -> None:
        \"\"\"Publish a Pydantic model or dict to a specific topic.\"\"\"
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
            logger.error(f"Failed to publish to {topic!r}: {e}")"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

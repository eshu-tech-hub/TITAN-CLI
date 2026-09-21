
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def _validate_storage(self) -> None:
        \"\"\"Validate storage connectivity and permissions.\"\"\""""

replacement = """    def _validate_storage(self) -> None:
        \"\"\"Validate storage connectivity and permissions.\"\"\"
        try:
            from titan.storage.trade_persistence import trade_store
            _ = trade_store.db_path
        except Exception as e:
            from titan.core.logger import logger
            logger.warning(f"Failed to eagerly initialize SQLite trades table: {e}")"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

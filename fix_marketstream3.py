
path = 'titan/runtime/stream.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

props = """
    @property
    def symbols(self) -> list[str]:
        if hasattr(self, "subscribed_symbols"): 
            return self.subscribed_symbols
        if hasattr(self.source, "_subscriptions"): 
            return list(self.source._subscriptions)
        return []

    @property
    def connected(self) -> bool:
        return self.is_connected
"""

# Insert before 'def set_on_quote'
content = content.replace("    def set_on_quote(self, callback: QuoteCallback) -> None:", props + "\n    def set_on_quote(self, callback: QuoteCallback) -> None:")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

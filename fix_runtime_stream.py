
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                if hasattr(self.stream.source, "subscribe"):
                    self.stream.source.subscribe([self.target_symbol or "RELIANCE"])"""

replacement = """                target = self.target_symbol or "^NSEI"
                if hasattr(self.stream, "source") and hasattr(self.stream.source, "subscribe"):
                    self.stream.source.subscribe([target])"""

content = content.replace(target, replacement)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

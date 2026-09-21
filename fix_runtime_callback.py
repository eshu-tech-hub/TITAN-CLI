
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                if hasattr(self.stream.source, "subscribe"):
                    self.stream.source.subscribe([self.target_symbol or "RELIANCE"])
                self.stream.start()"""

replacement = """                if hasattr(self.stream.source, "subscribe"):
                    self.stream.source.subscribe([self.target_symbol or "RELIANCE"])
                
                if hasattr(self.stream, "set_on_quote"):
                    self.stream.set_on_quote(self._pipeline_runner)
                elif hasattr(self.stream, "source") and hasattr(self.stream.source, "set_on_quote"):
                    self.stream.source.set_on_quote(self._pipeline_runner)
                    
                self.stream.start()"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

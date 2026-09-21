
path = 'titan_telegram_bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        # Assign attributes safely post-init
        if hasattr(self.engine, "watchlist"):
            self.engine.watchlist = self.watchlist
        self.engine.target_symbol = self.watchlist[0]"""

replacement = """        # Assign attributes safely post-init
        if hasattr(self.engine, "watchlist"):
            self.engine.watchlist = self.watchlist
        elif hasattr(self.engine, "target_symbol"):
            self.engine.target_symbol = self.watchlist[0]"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

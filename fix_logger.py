
path = 'titan/core/logger.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """# File logging
logger.add(
    "logs/titan.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)"""

replacement = """# File logging
logger.add(
    "logs/titan.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
    serialize=True,
)"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

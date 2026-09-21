
path = 'titan/runtime/models.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    # Pipeline events
    PIPELINE_EXECUTED = auto()
    PIPELINE_FAILED = auto()"""

replacement = """    # Pipeline events
    PIPELINE_EXECUTED = auto()
    PIPELINE_FAILED = auto()
    TRADE_EXECUTED = auto()"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

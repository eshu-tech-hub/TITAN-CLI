
path = 'titan/cli/common.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("market_stream.set_on_quote(lambda quote: engine._pipeline_runner())", "market_stream.set_on_quote(engine._pipeline_runner)")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

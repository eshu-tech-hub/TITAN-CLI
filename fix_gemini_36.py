
for path in ['titan/ai/providers/gemini.py', 'system_audit.py', 'test_gemini.py']:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple string replacement for gemini-2.5-flash -> gemini-3.6-flash
        content = content.replace('gemini-2.5-flash', 'gemini-3.6-flash')
        content = content.replace('gemini-1.5-flash', 'gemini-3.6-flash')

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except FileNotFoundError:
        pass

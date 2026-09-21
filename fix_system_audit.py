
path = 'system_audit.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content("Ping")
        print(f"    [+] Gemini API connection successful! Response: {resp.text.strip()}")
    except Exception as e:"""

replacement = """    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Ping"
        )
        print(f"    [+] Gemini API connection successful! Response: {resp.text.strip()}")
    except Exception as e:"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

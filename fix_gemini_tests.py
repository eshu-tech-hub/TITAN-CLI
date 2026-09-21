
for path in ['system_audit.py', 'test_gemini.py']:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if path == 'system_audit.py':
            target = """    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content("Ping")
        status["gemini"] = True if resp.text else False
    except Exception:"""
            replacement = """    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Ping"
        )
        status["gemini"] = True if resp.text else False
    except Exception:"""
            content = content.replace(target, replacement)

        if path == 'test_gemini.py':
            target = """import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("FAIL: GEMINI_API_KEY not found in .env")
        return

    genai.configure(api_key=api_key)
    
    # Using the standard flash model for a quick ping
    model = genai.GenerativeModel("gemini-1.5-flash") 
    response = model.generate_content("Respond with exactly one word: ONLINE.")"""
            replacement = """from google import genai
from dotenv import load_dotenv

load_dotenv()

def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("FAIL: GEMINI_API_KEY not found in .env")
        return

    client = genai.Client(api_key=api_key)
    
    # Using the standard flash model for a quick ping
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Respond with exactly one word: ONLINE."
    )"""
            content = content.replace(target, replacement)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except FileNotFoundError:
        pass

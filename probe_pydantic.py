from titan.ipc.models import PaperStatusResponse
from titan.runtime.local_transport import LocalTransport

print("[1] Fetching daemon payload...")
try:
    client = LocalTransport()
    raw = client.paper_status()
except Exception as e:
    print(f"Network Error: {e}")
    exit(1)

if not isinstance(raw, dict):
    print(f"Payload is not a dict: {type(raw)}")
    exit(1)

target = raw.get("data", raw)
print(f"[2] Target Keys: {list(target.keys())}")

print("[3] Executing Pydantic Validation...")
try:
    model = PaperStatusResponse.model_validate(target)
    print("[+] SUCCESS! Model is perfectly aligned.")
except Exception as e:
    print("\n[!] PYDANTIC VALIDATION ERROR:")
    print(e)

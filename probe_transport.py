import traceback

from titan.runtime.local_transport import LocalTransport

print("Testing LocalTransport instantiation and call...")
try:
    client = LocalTransport()
    print(f"Client initialized. Base URL: {getattr(client, 'base_url', 'N/A')}")
    res = client.paper_status()
    print(f"SUCCESS! Response type: {type(res)}, Data: {res}")
except Exception:
    print("\n[!] LOCAL TRANSPORT CRASHED:")
    traceback.print_exc()

import os

from dotenv import load_dotenv

from titan.runtime.local_transport import LocalTransport

print("--- SYSTEM CLI STATE (No .env) ---")
print(f"OS TITAN_PROFILE: {os.getenv('TITAN_PROFILE')!r}")
t1 = LocalTransport()
print(f"Transport Vars: {vars(t1)}")
if hasattr(t1, "service"):
    print(f"Service Vars: {vars(t1.service)}")

print("\n--- SYSTEM TUI STATE (With .env) ---")
load_dotenv(override=True)
print(f"OS TITAN_PROFILE: {os.getenv('TITAN_PROFILE')!r}")
t2 = LocalTransport()
print(f"Transport Vars: {vars(t2)}")
if hasattr(t2, "service"):
    print(f"Service Vars: {vars(t2.service)}")
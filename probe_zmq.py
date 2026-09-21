
import zmq

from titan.runtime.local_transport import LocalTransport

print("=" * 65)
print("TITAN IPC DUAL-SOCKET TELEMETRY PROBE")
print("=" * 65)

# 1. Test TCP Fallback (Port 55555)
print("[1/2] Probing TCP Port 55555 (Request-Reply Snapshot)...")
try:
    lt = LocalTransport()
    data = lt.paper_status()
    print("      + TCP OK! Daemon is alive.")
    print(f"      + Running: {data.get('running')}, Cash: {data.get('cash_balance')}")
except Exception as e:
    print(f"      ! TCP FAILED: {e}")

# 2. Test ZeroMQ Stream (Port 55556)
print("\n[2/2] Listening on ZeroMQ Port 55556 (Pub/Sub Stream) for 3 seconds...")
ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://127.0.0.1:55556")
sub.setsockopt(zmq.SUBSCRIBE, b"")

poller = zmq.Poller()
poller.register(sub, zmq.POLLIN)

events = poller.poll(3000)
if events:
    topic, payload = sub.recv_multipart()
    print(f"      + ZeroMQ OK! Received topic: {topic.decode()}")
    print(f"      + Payload snippet: {payload[:80].decode()}...")
else:
    print("      ! SILENCE DETECTED: Port 55556 emitted 0 messages in 3 seconds.")

sub.close()
ctx.term()
print("=" * 65)

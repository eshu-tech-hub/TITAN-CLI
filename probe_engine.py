import logging
import sys
import time
import traceback

from titan.enums import RunMode

from titan.cli.common import create_runtime_engine

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

print("\n=== TITAN FOREGROUND ENGINE PROBE ===")
print("[1] Creating RuntimeEngine...")
try:
    engine = create_runtime_engine(RunMode.PAPER, "RELIANCE.NS")
    print(f"Stream source: {type(engine.stream.source)}")
    
    print("[2] Starting daemon in foreground...")
    engine.start()
    
    print("[3] Waiting for polling cycle (20 seconds)...")
    for i in range(5):
        time.sleep(4)
        stats = engine.get_runtime_stats()
        print(f"[{i*4}s] Stream Connected: {engine.stream.is_connected} | Executions: {stats.get('pipeline_executions', 0)}")
        
except Exception:
    print("\n[!] FATAL CRASH CAUGHT:")
    traceback.print_exc()
finally:
    print("\n[4] Stopping engine...")
    try:
        engine.stop()
    except:
        pass

import time

from titan.brokers.yfinance.stream import YFinanceStreamSource

print("\n=== PROBING ^NSEI (AFTER HOURS) ===")
source = YFinanceStreamSource()
source.subscribe(["^NSEI"])

def on_quote(quote):
    print(f"[?] Quote received: {quote}")

source.set_on_quote(on_quote)

print("[1] Starting YFinance stream thread...")
source.start()

print("[2] Waiting 15 seconds for the background poll...")
try:
    for i in range(15):
        time.sleep(1)
        if not source._thread.is_alive():
            print("\n[!] FATAL: Background thread died silently!")
            break
except Exception as e:
    print(f"\n[!] CRASH CAUGHT: {e}")
finally:
    source.stop()
    print("[3] Probe complete.")

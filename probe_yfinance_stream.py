import time

from titan.brokers.yfinance.stream import YFinanceStreamSource

print("[1] Initializing YFinanceStreamSource...")
source = YFinanceStreamSource()
source.subscribe(["RELIANCE.NS"])

def on_quote(quote):
    print(f"[?] Quote received: {quote}")

source.set_on_quote(on_quote)
source.start()

print("[2] Listening for quotes (10s window)...")
time.sleep(10)
source.stop()
print("[3] Stream probe complete.")

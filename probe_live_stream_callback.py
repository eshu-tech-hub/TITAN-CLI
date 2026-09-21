import time

from titan.brokers.yfinance.stream import YFinanceStreamSource

source = YFinanceStreamSource()
source.subscribe(["^NSEI"])

def test_callback(quote):
    print("\n[?] CALLBACK TRIGGERED!")
    print(f"    Type: {type(quote)}")
    print(f"    Value: {quote}")

source.set_on_quote(test_callback)
print("[1] Starting background stream source...")
source.start()

print("[2] Waiting 10 seconds for poll loop...")
time.sleep(10)
source.stop()
print("[3] Test complete.")

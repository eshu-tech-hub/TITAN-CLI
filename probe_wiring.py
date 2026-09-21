import traceback

from titan.enums import RunMode

from titan.cli.common import create_runtime_engine

print("\n=== FACTORY WIRING PROBE 2.0 ===")
try:
    engine = create_runtime_engine(RunMode.PAPER)
    engine.target_symbol = "^NSEI"
    
    print("[1] Engine Built.")
    print(f"    Engine Target Symbol: {engine.target_symbol}")
    print(f"    Stream Object: {engine.stream}")
    
    if engine.stream is not None:
        source = getattr(engine.stream, "source", None)
        print(f"    Stream Source Object: {source}")
        
        if source is not None:
            print(f"    Source has subscribe?: {hasattr(source, 'subscribe')}")
            print("\n[2] Testing Engine Start...")
            engine.start()
            print(f"    Stream Connected: {getattr(engine.stream, 'connected', engine.stream.is_connected)}")
            print(f"    Stream Symbols: {getattr(engine.stream, 'symbols', [])}")
            engine.stop()
        else:
            print("\n[!] FATAL: MarketStream has NO source! The factory forgot to inject YFinanceStreamSource.")
    else:
        print("\n[!] FATAL: Engine has NO stream!")
        
except Exception:
    print("\n[!] CRASH:")
    traceback.print_exc()

import traceback

from titan.tui.layout import _get_paper_data

print("[1] Simulating TUI paper data fetch...")
try:
    result = _get_paper_data()
    print(f"Result: {result}")
except Exception:
    print("\n[!] CRASHED:")
    traceback.print_exc()

import inspect

from titan.tui import layout

print("=" * 65)
print("INSPECTING TUI DTO READERS")
print("=" * 65)

data = layout._get_paper_data()
print(f"Raw data keys: {list(data.keys())}\n")

# Check session
try:
    session_info = layout._read_paper_session(data)
    print(f"Session DTO:  {session_info}")
except Exception as e:
    print(f"Session DTO error: {e}")

# Check accounts
try:
    accounts_info = layout._read_paper_accounts(data)
    print(f"Accounts DTO: {accounts_info}")
except Exception as e:
    print(f"Accounts DTO error: {e}")

# Check portfolio
try:
    portfolio_info = layout._read_paper_portfolio(data)
    print(f"Portfolio DTO: {portfolio_info}")
except Exception as e:
    print(f"Portfolio DTO error: {e}")

print("\n" + "=" * 65)
print("SOURCE: _read_paper_session")
print("=" * 65)
print(inspect.getsource(layout._read_paper_session))

print("=" * 65)
print("SOURCE: _read_paper_accounts")
print("=" * 65)
print(inspect.getsource(layout._read_paper_accounts))

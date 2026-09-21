
layout_path = 'titan/tui/layout.py'
with open(layout_path, 'r', encoding='utf-8') as f:
    content = f.read()

paper_state = """def build_paper_state() -> PaperScreenState:
    from datetime import datetime
    data = _get_paper_data()

    session = _read_paper_session(data)
    account = _read_paper_accounts(data)
    portfolio = _read_paper_portfolio(data)
    performance = _read_paper_performance(data)
    positions = _read_paper_positions(data)
    orders = _read_paper_orders(data)
    trades = _read_paper_trades(data)

    now = datetime.now().strftime("%H:%M:%S")

    return PaperScreenState(
        session=session,
        account=account,
        portfolio=portfolio,
        performance=performance,
        positions=positions,
        orders=orders,
        trades=trades,
        last_refresh=now,
    )

"""

if "def build_paper_state" not in content:
    content = content.replace("def _read_runtime_engine(", paper_state + "def _read_runtime_engine(")

with open(layout_path, 'w', encoding='utf-8') as f:
    f.write(content)

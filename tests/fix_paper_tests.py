"""Final comprehensive fix for test_tui_paper.py migrations."""
import re

with open("tests/test_tui_paper.py", encoding="utf-8") as f:
    content = f.read()

# 1. Fix _make_mock_broker to set __class__ = PaperBroker
OLD_BROKER = (
    "def _make_mock_broker(\n"
    "    connected: bool = True,\n"
    "    initial_cash: Decimal = Decimal(100000),\n"
    ") -> MagicMock:\n"
    "    broker = MagicMock()\n"
    "    broker.is_connected.return_value = connected\n"
    "    broker._initial_cash = initial_cash\n"
    "    return broker"
)
NEW_BROKER = (
    "def _make_mock_broker(\n"
    "    connected: bool = True,\n"
    "    initial_cash: Decimal = Decimal(100000),\n"
    ") -> MagicMock:\n"
    "    from titan.paper.broker import PaperBroker\n"
    "\n"
    "    broker = MagicMock()\n"
    "    broker.__class__ = PaperBroker  # required for _get_paper_data() class-name check\n"
    "    broker.is_connected.return_value = connected\n"
    "    broker._initial_cash = initial_cash\n"
    "    return broker"
)
content = content.replace(OLD_BROKER, NEW_BROKER)

# 2. Replace legacy _get_broker decorator with IPC block + engine mock
OLD_DEC = '    @patch("titan.cli.commands.paper._get_broker")\n'
NEW_DEC = (
    '    @patch("titan.runtime.local_transport.LocalTransport.paper_status",'
    ' side_effect=ConnectionRefusedError)\n'
    '    @patch("titan.cli.common.get_runtime_engine")\n'
)
content = content.replace(OLD_DEC, NEW_DEC)

# 3. Update method signature: mock_broker → mock_engine, mock_ipc
content = re.sub(
    r"(    def test_\w+\(self), mock_broker: MagicMock\) -> None:",
    r"\1, mock_engine: MagicMock, mock_ipc: MagicMock) -> None:",
    content,
)

# 4. Replace `mock_broker.return_value = broker` with full engine setup
OLD_ASSIGN = "        mock_broker.return_value = broker\n"
ENGINE_SETUP = (
    "        from titan.runtime.runtime import RuntimeEngine\n"
    "        engine_mock = MagicMock(spec=RuntimeEngine)\n"
    '        engine_mock.status.name = "RUNNING"\n'
    "        engine_mock.broker = broker\n"
    "        mock_engine.return_value = engine_mock\n"
)
content = content.replace(OLD_ASSIGN, ENGINE_SETUP)

# 5. Fix methods that have _paper_start_time=None (no injection) + paper_status (1 injection)
#    These ended up with 2 args but should only have 1 (mock_ipc)
#    Pattern: the two patches without get_runtime_engine but with 2 mock args
content = re.sub(
    r'(@patch\("titan\.cli\.commands\.paper\._paper_start_time", None\)\n'
    r'    @patch\("titan\.runtime\.local_transport\.LocalTransport\.paper_status",'
    r' side_effect=ConnectionRefusedError\)\n'
    r'    def (\w+)\(self, mock_engine: MagicMock, mock_ipc: MagicMock\) -> None:)',
    lambda m: (
        '@patch("titan.cli.commands.paper._paper_start_time", None)\n'
        '    @patch("titan.runtime.local_transport.LocalTransport.paper_status",'
        ' side_effect=ConnectionRefusedError)\n'
        f"    def {m.group(2)}(self, mock_ipc: MagicMock) -> None:"
    ),
    content,
)

with open("tests/test_tui_paper.py", "w", encoding="utf-8") as f:
    f.write(content)

with open("tests/test_tui_paper.py", encoding="utf-8") as f:
    ls = f.readlines()

remaining = [i + 1 for i, l in enumerate(ls) if "_get_broker" in l]
print(f"Done. {len(ls)} lines. Remaining _get_broker refs: {remaining}")

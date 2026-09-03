import re

with open('tests/test_tui_paper.py', encoding='utf-8') as f:
    content = f.read()

# Replace any remaining _get_broker patches (which have return_value=None or side_effect=...)
# with an IPC block AND a get_runtime_engine mock that raises an error.
content = re.sub(
    r'    @patch\("titan\.cli\.commands\.paper\._get_broker",\s*(return_value=None|side_effect=\w+)\)\n',
    '    @patch("titan.runtime.local_transport.LocalTransport.paper_status", side_effect=ConnectionRefusedError)\n'
    '    @patch("titan.cli.common.get_runtime_engine", side_effect=RuntimeError)\n',
    content
)

with open('tests/test_tui_paper.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('tests/test_tui_paper.py', encoding='utf-8') as f:
    lines = f.readlines()
remaining = [i+1 for i, l in enumerate(lines) if '_get_broker' in l]
print(f'Done. {len(lines)} lines. Remaining _get_broker refs: {remaining}')

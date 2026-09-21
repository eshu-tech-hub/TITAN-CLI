import inspect
import socket

from titan.cli.commands import paper
from titan.runtime.local_transport import LocalTransport

print('=' * 65)
print('TITAN SOCKET & IPC DIAGNOSTIC PROBE')
print('=' * 65)

# Step 1: Physical TCP Port Check
print('[1/4] Checking TCP Port 55555 on 127.0.0.1...')
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1.5)
try:
    s.connect(('127.0.0.1', 55555))
    s.close()
    print('      + TCP Port 55555 is ACTIVE and LISTENING.')
except Exception as exc:
    print(f'      ! TCP Port 55555 is NOT listening: {exc}')

# Step 2: Test LocalTransport.paper_status()
print('\n[2/4] Testing LocalTransport().paper_status()...')
try:
    lt = LocalTransport()
    print(f'      + Client Target Config: {vars(lt)}')
    data = lt.paper_status()
    print(f'      + Received Payload: {data}')
except Exception as exc:
    print(f'      ! LocalTransport call failed: {type(exc).__name__}: {exc}')

# Step 3: Test TUI _get_paper_data()
print('\n[3/4] Testing titan.tui.layout._get_paper_data()...')
try:
    from titan.tui.layout import _get_paper_data
    tui_data = _get_paper_data()
    print(f'      + layout._get_paper_data() returned: {tui_data}')
except Exception as exc:
    print(f'      ! layout._get_paper_data() failed: {type(exc).__name__}: {exc}')

# Step 4: Inspect how the CLI gets paper status
print('\n[4/4] Inspecting CLI paper.status implementation...')
try:
    src = inspect.getsource(paper.status)
    for line in src.splitlines()[:12]:
        print(f'        {line}')
except Exception as exc:
    print(f'      ! Could not inspect: {exc}')

print('=' * 65)

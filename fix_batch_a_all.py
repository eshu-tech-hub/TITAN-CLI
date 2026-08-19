import os


def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified = False
    for i, line in enumerate(lines):
        if 'except Exception:' in line:
            indent = line[:len(line) - len(line.lstrip())]
            
            j = i - 1
            body = []
            while j >= 0 and not lines[j].strip().startswith('try:'):
                body.append(lines[j])
                j -= 1
                
            body = ''.join(reversed(body))
            
            if 'import' in body:
                lines[i] = indent + 'except ImportError:\n'
                modified = True
            elif '.start()' in body or '.stop()' in body or 'AuditManager' in body or 'disconnect' in body:
                lines[i] = indent + 'except (RuntimeError, OSError) as e:\n'
                if i + 1 < len(lines) and 'pass' in lines[i+1]:
                    next_indent = lines[i+1][:len(lines[i+1]) - len(lines[i+1].lstrip())]
                    lines[i+1] = next_indent + 'logger.debug(f"Operation failed: {e}")\n'
                modified = True
            elif 'funds' in body or 'margin' in body or 'positions' in body or 'orders' in body or 'generate_report' in body or 'paper_status' in body or 'entries = ' in body:
                lines[i] = indent + 'except (RuntimeError, ConnectionError, AttributeError) as e:\n'
                if i + 1 < len(lines) and 'pass' in lines[i+1]:
                    next_indent = lines[i+1][:len(lines[i+1]) - len(lines[i+1].lstrip())]
                    lines[i+1] = next_indent + 'logger.debug(f"Fetch failed: {e}")\n'
                modified = True
            elif 'str(val' in body or 'isoformat' in body:
                lines[i] = indent + 'except (ValueError, TypeError, AttributeError):\n'
                modified = True
            else:
                lines[i] = indent + 'except (RuntimeError, ValueError):\n'
                modified = True

        elif 'except Exception as' in line:
            indent = line[:len(line) - len(line.lstrip())]
            if 'json' in line or 'export' in line.lower() or 'with open' in ''.join(lines[i-4:i]) or 'portfolio state' in ''.join(lines[i:i+4]).lower():
                lines[i] = indent + 'except (OSError, TypeError, ValueError, RuntimeError) as e:\n'
            else:
                lines[i] = indent + 'except RuntimeError as e:\n'
            modified = True
            
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

for root, _, files in os.walk('titan/cli/commands'):
    for file in files:
        if file.endswith('.py') and file != 'live.py': # already did live.py
            process_file(os.path.join(root, file))


file_path = 'titan/cli/commands/live.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'except Exception:' in line:
        indent = line[:len(line) - len(line.lstrip())]
        
        # Look backwards to find the try block
        j = i - 1
        body = []
        while j >= 0 and not lines[j].strip().startswith('try:'):
            body.append(lines[j])
            j -= 1
            
        body = ''.join(reversed(body))
        
        if 'import' in body:
            lines[i] = indent + 'except ImportError:\n'
        elif '.start()' in body or '.stop()' in body or 'AuditManager' in body:
            lines[i] = indent + 'except (RuntimeError, OSError) as e:\n'
            # We must replace the pass in the next line if it exists
            if i + 1 < len(lines) and 'pass' in lines[i+1]:
                next_indent = lines[i+1][:len(lines[i+1]) - len(lines[i+1].lstrip())]
                lines[i+1] = next_indent + 'logger.debug(f"Operation failed: {e}")\n'
        elif 'funds' in body or 'margin' in body or 'positions' in body or 'orders' in body or 'generate_report' in body:
            lines[i] = indent + 'except (RuntimeError, ConnectionError, AttributeError) as e:\n'
            if i + 1 < len(lines) and 'pass' in lines[i+1]:
                next_indent = lines[i+1][:len(lines[i+1]) - len(lines[i+1].lstrip())]
                lines[i+1] = next_indent + 'logger.debug(f"Fetch failed: {e}")\n'
        elif 'str(val' in body or 'isoformat' in body:
            lines[i] = indent + 'except (ValueError, TypeError, AttributeError):\n'

    elif 'except Exception as' in line:
        # Some are xcept Exception as e: which log and raise Exit
        indent = line[:len(line) - len(line.lstrip())]
        if 'json' in line or 'export' in line.lower() or 'with open' in ''.join(lines[i-4:i]):
            lines[i] = indent + 'except (OSError, TypeError, ValueError) as e:\n'
        else:
            lines[i] = indent + 'except RuntimeError as e:\n'
            
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

import re

with open('titan/cli/commands/live.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. ImportError for engine
text = re.sub(
    r'(try:\n\s+from titan\.cli\.common import _runtime_engine\n\n\s+engine = _runtime_engine\n\s+)except Exception:',
    r'\1except ImportError:',
    text
)

# 2. Manager start/stop
def replace_manager(match):
    indent = match.group(1)
    return match.group(0).replace('except Exception:\n' + indent + '    pass', f'except (RuntimeError, OSError) as e:\n{indent}    logger.debug(f"Manager operation failed: {{e}}")')

text = re.sub(
    r'(try:\n(\s+)(dm\.(?:start|stop)\(\)|monitoring\.(?:start|stop)\(\)|engine\.(?:stop|start)\(\)|get_(?:deployment|monitoring)_manager\(\)\.(?:start|stop)\(\))\n\s+except Exception:\n\s+pass)',
    replace_manager,
    text
)

# 3. AuditManager
def replace_audit(match):
    indent = match.group(1)
    return match.group(0).replace('except Exception:\n' + indent + '    pass', f'except ImportError:\n{indent}    pass')

text = re.sub(
    r'(try:\n(\s+)from titan\.audit\.manager import AuditManager.*?action="titan_live_[a-z]+",\n\s+\)\n\s+except Exception:\n\s+pass)',
    replace_audit,
    text,
    flags=re.DOTALL
)

# 4. Fetchers
def replace_fetcher(match):
    indent = match.group(2)
    return match.group(0).replace('except Exception:\n' + indent + '    pass', f'except (RuntimeError, ConnectionError, AttributeError) as e:\n{indent}    logger.debug(f"Fetch failed: {{e}}")')

text = re.sub(
    r'(try:\n(\s+)(?:rt_report = engine\.generate_report\(\)|report = engine\.generate_report\(\)|funds = broker\.funds\(\)|margin = broker\.margin\(\)|for p in broker\.positions\(\):|for o in broker\.orders\(\):|dep_report = get_deployment_manager\(\)\.generate_report\(\)|mreport = get_monitoring_manager\(\)\.generate_report\(\)|rreport = get_recovery_manager\(\)\.generate_report\(\)|areport = audit\.generate_report\(\)).*?except Exception:\n\s+pass)',
    replace_fetcher,
    text,
    flags=re.DOTALL
)

# 5. Type Conversions
text = re.sub(
    r'(try:\n\s+return str\(val\)\n\s+)except Exception:',
    r'\1except (ValueError, TypeError):',
    text
)
text = re.sub(
    r'(try:\n\s+if hasattr\(val, "isoformat"\):\n\s+return str\(val\.isoformat\(\)\)\n\s+return str\(val\)\n\s+)except Exception:',
    r'\1except (ValueError, TypeError, AttributeError):',
    text
)

# Replace the specific Exception as e occurrences that are just pass? No, those don't exist.
# Let's save.
with open('titan/cli/commands/live.py', 'w', encoding='utf-8') as f:
    f.write(text)

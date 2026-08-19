import ast

with open('titan/cli/commands/live.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
tree = ast.parse(''.join(lines))
for node in ast.walk(tree):
    if isinstance(node, ast.Try):
        for handler in node.handlers:
            if isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                print(f"--- Line {handler.lineno} ---")
                start = node.lineno - 1
                end = handler.lineno
                print(''.join(lines[start:end]).strip())

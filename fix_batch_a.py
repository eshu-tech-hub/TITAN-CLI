import ast
import os


class ExceptionReplacer(ast.NodeTransformer):
    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        if isinstance(node.type, ast.Name) and node.type.id == 'Exception':
            # See what's inside the try block
            # Since we can't easily see parent node from here without adding a parent pointer,
            # we'll just return the node as is and use a text-based replacement driven by line numbers.
            pass
        return node

def process_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    tree = ast.parse(''.join(lines))
    
    replacements = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                    # Determine replacement based on body
                    body_text = ''.join(lines[node.lineno-1:handler.lineno-1])
                    if 'import' in body_text:
                        replacements.append((handler.lineno, '    except ImportError:\n'))
                    elif '.start()' in body_text or '.stop()' in body_text or 'AuditManager' in body_text:
                        replacements.append((handler.lineno, '    except (RuntimeError, OSError) as e:\n        logger.warning(f"Operation failed: {e}")\n'))
                        # Need to also replace pass if it's the only thing
                        # But wait, we can just replace xcept Exception: with xcept (RuntimeError, OSError):
                    elif 'funds' in body_text or 'margin' in body_text or 'positions' in body_text or 'orders' in body_text or 'report' in body_text:
                        replacements.append((handler.lineno, '    except (RuntimeError, ConnectionError, AttributeError):\n'))
                    elif 'str(val' in body_text:
                        replacements.append((handler.lineno, '    except (ValueError, TypeError, AttributeError):\n'))
                    else:
                        replacements.append((handler.lineno, '    except RuntimeError:\n'))
                        
    # Sort backwards and apply
    replacements.sort(key=lambda x: x[0], reverse=True)
    for lineno, new_text in replacements:
        # lines[lineno-1] is the xcept Exception: line
        indent = len(lines[lineno-1]) - len(lines[lineno-1].lstrip())
        lines[lineno-1] = ' ' * indent + new_text.lstrip()
        
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

for root, _, files in os.walk('titan/cli/commands'):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))

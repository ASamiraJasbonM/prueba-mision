"""Static acceptance check for explicitly forbidden numeric/time APIs."""
import ast
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent / 'backend'
issues = []
for path in root.rglob('*.py'):
    if 'tests' in path.parts:
        continue
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = function.id if isinstance(function, ast.Name) else function.attr if isinstance(function, ast.Attribute) else ''
        if name in ['FloatField', 'float']:
            issues.append(f'{path.relative_to(root)}:{node.lineno}: {name} prohibido')
        if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name) and function.value.id == 'datetime' and function.attr == 'now':
            issues.append(f'{path.relative_to(root)}:{node.lineno}: datetime.now prohibido; usar timezone.now')
print('\n'.join(issues) if issues else 'OK: sin FloatField, float() ni datetime.now() en backend de produccion.')
sys.exit(bool(issues))

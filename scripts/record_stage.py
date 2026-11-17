"""Run acceptance commands, preserve evidence and commit only a passing stage."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
number, summary, commands_json = sys.argv[1:]
commands = json.loads(commands_json)
chunks = [f'# Etapa {number}\n\n{summary}\n', '## Comandos y resultados\n']
for args in commands:
    command = [sys.executable, str(root / 'backend/manage.py'), *args]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
    output = result.stdout + result.stderr
    print(output[-6000:])
    chunks.append(f'### manage.py {" ".join(args)}\n\n```text\n{output}\nexit={result.returncode}\n```\n')
    if result.returncode:
        sys.exit(result.returncode)
paths = ['backend', 'frontend', 'docs', 'scripts', 'README.md', 'requirements.txt', '.env.example', '.gitignore', 'PLAN_CORREGIDO.md']
subprocess.run(['git', 'add', '--', *paths], cwd=root, check=True)
changed = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=root, text=True)
chunks.append('## Archivos creados/modificados\n\n```text\n' + changed + '```\n')
chunks.append('## Código y pendientes\n\nEl código completo está en los archivos listados de este commit. Decisiones y limitaciones acumuladas en README.md y docs/ETAPAS.md.\n')
target = root / 'docs' / 'etapas' / f'{number}.md'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text('\n'.join(chunks), encoding='utf-8')
with (root / 'docs/ETAPAS.md').open('a', encoding='utf-8') as f:
    f.write(f'\n## Etapa {number}: verificada\n\n{summary}\n\nEvidencia completa: [etapas/{number}.md](etapas/{number}.md).\n')
with (root / 'README.md').open('a', encoding='utf-8') as f:
    f.write(f'\n- Etapa {number}: {summary}\n')
subprocess.run(['git', 'add', '--', 'README.md', 'docs'], cwd=root, check=True)
subprocess.run(['git', 'commit', '-m', f'feat(backend): etapa {number} {summary}'], cwd=root, check=True)

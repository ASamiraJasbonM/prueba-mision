"""Verify one observation, preserve full output and create an atomic local commit."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
number, summary, commands_json = sys.argv[1:]
if subprocess.check_output(['git', 'branch', '--show-current'], cwd=root, text=True).strip() != 'feat/backend-datapulse':
    raise RuntimeError('La revisión pertenece a feat/backend-datapulse.')
sections = [f'# Observación {number}\n\n{summary}\n']
for args in json.loads(commands_json):
    command = [sys.executable, *args]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
    output = result.stdout + result.stderr
    print(output[-2500:], flush=True)
    sections.append(f'## {subprocess.list2cmdline(command)}\n\n```text\n{output}\nexit={result.returncode}\n```\n')
    if result.returncode:
        raise SystemExit(result.returncode)
    if 'test' in args and 'Ran 0 tests' in output:
        raise RuntimeError('No se ejecutaron pruebas.')
target = root / 'docs/observaciones' / f'{number}.md'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text('\n'.join(sections), encoding='utf-8')
with (root / 'docs/ETAPAS.md').open('a', encoding='utf-8') as stream:
    stream.write(f'\n## Observación {number}\n\n{summary}\n\nVerificación y salida completa: [observaciones/{number}.md](observaciones/{number}.md).\n')
subprocess.run(['git', 'add', '--', 'backend', 'docs', 'scripts', 'README.md'], cwd=root, check=True)
subprocess.run(['git', 'commit', '-m', f'fix(backend): {number} {summary}'], cwd=root, check=True)

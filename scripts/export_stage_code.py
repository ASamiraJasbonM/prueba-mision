"""Prepare reviewable source snapshots for the per-stage delivery format."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
stages = {
    '00': ('dc20669', ['backend/config/settings.py', 'backend/core/health.py']),
    '01': ('e40fe4c', ['backend/core/models.py', 'backend/core/admin.py']),
    '02': ('cbf51dc', ['backend/core/models.py', 'backend/core/migrations/0002_dominio_economico.py']),
    '03': ('8c46a58', ['backend/core/api.py']),
    '04': ('10de97e', ['backend/core/auth_api.py', 'backend/core/authentication.py', 'backend/core/permissions.py']),
    '05': ('3811b63', ['backend/core/data_api.py', 'backend/core/services/sync.py']),
    '06': ('36a3f9c', ['backend/core/services/risk.py', 'backend/core/risk_api.py']),
    '07': ('eb328df', ['backend/core/services/portfolios.py', 'backend/core/portfolio_api.py', 'backend/core/services/pdf_report.py']),
    '08': ('5f7e979', ['backend/core/dashboard_api.py']),
    '09': ('b0b535a', ['backend/core/observability.py', 'backend/core/services/tasks.py']),
    '10': (None, ['backend/core/management/commands/seed_data.py', 'backend/core/services/risk.py']),
}
target = root / 'docs/etapas/codigo'
target.mkdir(parents=True, exist_ok=True)
for number, (commit, paths) in stages.items():
    lines = [f'# Código completo de archivos clave — etapa {number}\n',
             f'Estado: {commit or "archivos finales de etapa 10"}. Cambios posteriores se conservan en el código actual del backend.\n']
    for path in paths:
        source = (subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=root).decode('utf-8')
                  if commit else (root / path).read_text(encoding='utf-8'))
        lines.append(f'## {path}\n\n```python\n{source}\n```\n')
    (target / f'{number}.md').write_text('\n'.join(lines), encoding='utf-8')
original = subprocess.check_output(['git', 'show', 'e40fe4c:docs/etapas/01.md'], cwd=root).decode('utf-8')
migrations = original.split('### manage.py makemigrations', 1)[1].split('### manage.py test', 1)[0]
(root / 'docs/etapas/migraciones-01.md').write_text(
    '# Migraciones reales de etapa 1\n\n### manage.py makemigrations' + migrations +
    '\nLa primera invocación general detectó cero tests por ejecutarse desde raíz sin paquete backend. Se corrigió el runner y se verificaron los tres tests antes de pasar a etapa 2; ver 01.md.\n', encoding='utf-8')
print('Snapshots completos 00–10 y evidencia de migraciones preparados.')

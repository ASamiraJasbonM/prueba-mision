"""Store bounded operational metadata, never raw provider exceptions or settings."""
import os
import re
from datetime import timedelta
from django.utils import timezone
from core.models import MaintenanceRun, Pais, IndicadorEconomico, TipoCambio

TASKS = ['indicadores', 'tipos_cambio', 'paises']


def start(task):
    commit = os.environ.get('GITHUB_SHA', '')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    return MaintenanceRun.objects.create(tarea=task,
        commit=commit if re.fullmatch(r'[0-9a-f]{40}', commit) else '',
        run_id=run_id if re.fullmatch(r'\d{1,30}', run_id) else '')


def finish(run, result):
    errors = result.get('errores', []) + result.get('riesgo', {}).get('errores', [])
    if result.get('error_code'):
        errors.append({'code': result['error_code']})
    # Whitelist machine labels and discard arbitrary messages, URLs and credentials.
    safe = []
    for error in errors[:100]:
        safe.append({key: str(error[key]) for key in ['pais', 'operacion', 'code', 'causa']
            if key in error and re.fullmatch(r'[A-Za-z0-9_*.-]{1,40}', str(error[key]))})
    count = max(0, int(result.get('actualizados', 0)))
    run.estado = ('PARCIAL' if count else 'FALLIDA') if errors else 'COMPLETADA'
    run.terminado, run.actualizados, run.errores = timezone.now(), count, safe
    run.cobertura = coverage(run.tarea)
    run.save(update_fields=['estado', 'terminado', 'actualizados', 'errores', 'cobertura'])


def coverage(task):
    today = timezone.now().date()
    countries = list(Pais.objects.values('codigo_iso', 'moneda_id'))
    if task == 'indicadores':
        end = today.year-1
        rows = list(IndicadorEconomico.objects.filter(anio__range=(end-4, end)).values('pais_id', 'fuente'))
        return [{'pais': country['codigo_iso'], 'esperados': 30,
            'externos': sum(row['pais_id'] == country['codigo_iso'] and row['fuente'] == 'WORLD_BANK' for row in rows),
            'no_verificados': sum(row['pais_id'] == country['codigo_iso'] and row['fuente'] != 'WORLD_BANK' for row in rows),
            'faltantes': max(0, 30-sum(row['pais_id'] == country['codigo_iso'] for row in rows))} for country in countries]
    if task == 'tipos_cambio':
        rows = list(TipoCambio.objects.filter(moneda_destino='USD', fuente='EXCHANGE_RATE_API',
            fecha__range=(today-timedelta(days=30), today)).values('moneda_origen_id', 'fecha'))
        result = []
        for country in countries:
            dates = {row['fecha'] for row in rows if row['moneda_origen_id'] == country['moneda_id']}
            consecutive = 0
            while consecutive < 31 and today-timedelta(days=consecutive) in dates:
                consecutive += 1
            result.append({'pais': country['codigo_iso'], 'esperados': 31, 'externos': len(dates),
                'dias_consecutivos': consecutive, 'faltantes': 31-len(dates)})
        return result
    return []


def payload(run):
    if run is None:
        return None
    state = run.estado
    if state == 'EJECUTANDO' and run.iniciado < timezone.now()-timedelta(minutes=35):
        state = 'INTERRUMPIDA'
    return {'id': str(run.pk), 'estado': state, 'iniciado': run.iniciado,
        'terminado': run.terminado, 'actualizados': run.actualizados, 'errores': run.errores,
        'cobertura': run.cobertura, 'commit': run.commit, 'ejecucion_url':
        f'https://github.com/ASamiraJasbonM/prueba-mision/actions/runs/{run.run_id}' if run.run_id.isdigit() else None}


def summary():
    return [{'tarea': task,
        'ultima_ejecucion': payload(MaintenanceRun.objects.filter(tarea=task).first()),
        'ultimo_exito': payload(MaintenanceRun.objects.filter(tarea=task, estado='COMPLETADA').first())}
        for task in TASKS]

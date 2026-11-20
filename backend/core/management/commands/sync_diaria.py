"""Run scheduled work outside HTTP workers and fail visibly on provider errors."""
import json
import logging

from django.core.management.base import BaseCommand, CommandError
from core.services import tasks


logger = logging.getLogger('datapulse')


class Command(BaseCommand):
    help = 'Sincroniza indicadores y cambios, recalcula IRPC y falla ante resultados incompletos.'

    def handle(self, *args, **options):
        report = {'ok': True, 'tareas': {}}
        for name, operation in [('indicadores', tasks.sync_and_recalculate),
                                ('tipos_cambio', tasks.exchange_and_recalculate)]:
            try:
                result = operation()
                failed = bool(result.get('errores') or result.get('riesgo', {}).get('errores'))
                report['tareas'][name] = result
            except Exception as exc:
                # Still run the second independent task. Never log exceptions
                # that might contain database credentials or provider headers.
                failed = True
                report['tareas'][name] = {'error_code': type(exc).__name__}
                logger.error('sync_diaria_error', extra={'operacion': name, 'error_code': type(exc).__name__})
            report['ok'] = report['ok'] and not failed
        self.stdout.write(json.dumps(report, ensure_ascii=False))
        if not report['ok']:
            raise CommandError('Sincronización incompleta: consulta el informe; ambas tareas se intentaron.')

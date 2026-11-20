"""Run scheduled work outside HTTP workers and fail visibly on provider errors."""
import json
import logging

from django.core.management.base import BaseCommand, CommandError
from core.services import tasks
from core.services import maintenance


logger = logging.getLogger('datapulse')


class Command(BaseCommand):
    help = 'Sincroniza indicadores y cambios, recalcula IRPC y falla ante resultados incompletos.'

    def add_arguments(self, parser):
        parser.add_argument('--task', choices=['all', 'indicadores', 'tipos_cambio', 'paises'], default='all',
                            help='Seleccionar una tarea para ejecutarla en un job independiente.')

    def handle(self, *args, **options):
        report = {'ok': True, 'tareas': {}}
        for name, operation in [('indicadores', lambda: tasks.sync_and_recalculate(batch=True)),
                                ('tipos_cambio', tasks.exchange_and_recalculate), ('paises', tasks.sync_countries)]:
            if name == 'paises' and options['task'] != 'paises':
                continue
            if options['task'] not in ('all', name):
                continue
            run = maintenance.start(name)
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
            maintenance.finish(run, report['tareas'][name])
            report['ok'] = report['ok'] and not failed
        self.stdout.write(json.dumps(report, ensure_ascii=False))
        if not report['ok']:
            raise CommandError('Sincronización incompleta: consulta el informe; ambas tareas se intentaron.')

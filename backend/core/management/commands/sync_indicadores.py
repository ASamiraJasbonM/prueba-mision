import json
from django.core.management.base import BaseCommand, CommandError
from core.services.tasks import sync_and_recalculate


class Command(BaseCommand):
    help = 'Sincroniza los indicadores, tolerando fallos parciales.'

    def handle(self, *args, **options):
        report = sync_and_recalculate()
        if report['errores'] and report['actualizados'] == 0:
            raise CommandError('Fallo total: ningún indicador se actualizó.')
        self.stdout.write(json.dumps(report, ensure_ascii=False))

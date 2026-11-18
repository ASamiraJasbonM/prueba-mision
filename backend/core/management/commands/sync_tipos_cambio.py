import json
from django.core.management.base import BaseCommand, CommandError
from core.services.tasks import exchange_and_recalculate


class Command(BaseCommand):
    help = 'Sincroniza cambios diarios y recalcula riesgos.'

    def handle(self, *args, **options):
        report = exchange_and_recalculate()
        if report['errores'] and report['actualizados'] == 0:
            raise CommandError('Fallo total: ningún tipo de cambio se actualizó.')
        self.stdout.write(json.dumps(report, ensure_ascii=False))

import json
from django.core.management.base import BaseCommand, CommandError
from core.services.sync import sync_countries


class Command(BaseCommand):
    help = 'Actualiza metadatos desde REST Countries v5.'

    def handle(self, *args, **options):
        report = sync_countries()
        self.stdout.write(json.dumps(report, ensure_ascii=False))
        if report['errores']:
            raise CommandError('Sincronización de países incompleta; consulta el informe seguro.')

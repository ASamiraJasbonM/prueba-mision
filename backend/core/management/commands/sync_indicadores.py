import json
from django.core.management.base import BaseCommand
from core.services.sync import sync_indicators


class Command(BaseCommand):
    help = 'Sincroniza los indicadores, tolerando fallos parciales.'

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(sync_indicators(), ensure_ascii=False))

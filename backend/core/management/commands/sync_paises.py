import json
from django.core.management.base import BaseCommand
from core.services.sync import sync_countries


class Command(BaseCommand):
    help = 'Actualiza metadatos desde REST Countries v5.'

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(sync_countries(), ensure_ascii=False))

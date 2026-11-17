import json
from django.core.management.base import BaseCommand
from core.services.tasks import sync_and_recalculate


class Command(BaseCommand):
    help = 'Sincroniza los indicadores, tolerando fallos parciales.'

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(sync_and_recalculate(), ensure_ascii=False))

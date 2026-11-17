import json
from django.core.management.base import BaseCommand
from core.services.risk import recalculate


class Command(BaseCommand):
    help = 'Recalcula IRPC y genera alertas sin duplicados.'

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(recalculate(), ensure_ascii=False))

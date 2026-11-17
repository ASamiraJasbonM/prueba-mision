import json
from django.core.management.base import BaseCommand
from core.services.tasks import exchange_and_recalculate


class Command(BaseCommand):
    help = 'Sincroniza cambios diarios y recalcula riesgos.'

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(exchange_and_recalculate(), ensure_ascii=False))

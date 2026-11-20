import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
from core.services.sync_jobs import process_next_job


class Command(BaseCommand):
    help = 'Procesa la cola persistente de sincronización ADMIN. Ejecutar junto al servidor HTTP.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        while True:
            if not connection.in_atomic_block:
                close_old_connections()
            worked = process_next_job()
            if options['once']:
                return
            if not worked:
                time.sleep(5)

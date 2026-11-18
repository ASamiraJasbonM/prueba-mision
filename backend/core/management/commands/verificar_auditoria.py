import json
import logging
from django.core.management.base import BaseCommand, CommandError
from core.services.audit_chain import verify


class Command(BaseCommand):
    help = 'Valida hashes, HMAC y cabecera de la cadena de auditoría.'

    def handle(self, **options):
        result = verify()
        self.stdout.write(json.dumps(result))
        logging.getLogger('datapulse').info('audit_verification', extra=result)
        if not result['ok']:
            raise CommandError(f"Cadena inválida: id={result['broken_id']}, causa={result['cause']}")

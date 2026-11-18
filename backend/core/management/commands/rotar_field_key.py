import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Usuario
from core.services.crypto import encrypt, decrypt


class Command(BaseCommand):
    help = 'Recifra MFA usando FIELD_ENCRYPTION_KEY_OLD y FIELD_ENCRYPTION_KEY_NEW (entorno).'

    @transaction.atomic
    def handle(self, **options):
        old = os.environ.get('FIELD_ENCRYPTION_KEY_OLD')
        new = os.environ.get('FIELD_ENCRYPTION_KEY_NEW')
        if not old or not new:
            raise CommandError('Se requieren las claves OLD y NEW en el entorno.')
        count = 0
        for user in Usuario.objects.select_for_update().order_by('pk'):
            changed = []
            for field in ['mfa_secret_enc', 'recovery_codes_enc']:
                value = getattr(user, field)
                if value:
                    setattr(user, field, encrypt(decrypt(value, old), new))
                    changed.append(field)
            if changed:
                user.save(update_fields=changed)
                count += 1
        self.stdout.write(f'Usuarios recifrados: {count}. Actualizar FIELD_ENCRYPTION_KEY antes de reiniciar.')

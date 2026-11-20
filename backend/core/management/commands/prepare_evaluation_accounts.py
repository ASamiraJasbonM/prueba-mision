from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.audit import audit
from core.models import Usuario


ACCOUNTS = [('admin', 'ADMIN'), ('analista', 'ANALISTA'), ('viewer', 'VIEWER')]
DEMO_PASSWORD = 'DataPulse2026!'  # Public test credential required by the exercise.


class Command(BaseCommand):
    help = 'Configura únicamente las tres cuentas públicas de evaluación; no carga ni borra datos.'

    def add_arguments(self, parser):
        parser.add_argument('--confirm-demo', action='store_true',
                            help='Confirmar que esta base contiene solo datos de demostración.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm_demo']:
            raise CommandError('Requiere --confirm-demo; no usar en una base con datos reales.')
        emails = [f'{prefix}@datapulse.com' for prefix, _ in ACCOUNTS]
        existing = {user.email: user for user in
                    Usuario.objects.select_for_update().filter(email__in=emails)}
        if any(user.mfa_enabled for user in existing.values()):
            raise CommandError('Una cuenta tiene MFA habilitado. Se conserva MFA y no se modifica ninguna cuenta.')
        for prefix, role in ACCOUNTS:
            email = f'{prefix}@datapulse.com'
            user = existing.get(email)
            created = user is None
            if created:
                user = Usuario(email=email, nombre_completo=f'{prefix.title()} demo')
            desired = {'rol': role, 'activo': True, 'is_active': True,
                       'is_staff': False, 'is_superuser': False}
            changed = created or not user.check_password(DEMO_PASSWORD) or any(
                getattr(user, key) != value for key, value in desired.items())
            if changed:
                for key, value in desired.items():
                    setattr(user, key, value)
                user.set_password(DEMO_PASSWORD)
                user.full_clean()
                user.save()
                audit(None, 'CREAR' if created else 'EDITAR', user,
                      {'cuenta_evaluacion': True, 'rol': role})
            self.stdout.write(f'{email}: {role}, acceso API de evaluación verificado.')

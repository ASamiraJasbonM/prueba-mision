from django.core.management.base import BaseCommand
from core.models import Usuario


class Command(BaseCommand):
    help = 'Crear administrador de prueba, repetible y solo para entorno demo.'

    def handle(self, *args, **options):
        if not Usuario.objects.filter(email='admin@datapulse.com').exists():
            Usuario.objects.create_superuser('admin@datapulse.com', 'DataPulse2026!', nombre_completo='Admin demo')
        self.stdout.write('Administrador demo disponible.')

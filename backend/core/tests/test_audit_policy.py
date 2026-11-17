from io import StringIO
from django.core.management import call_command
from core.models import LogActividad
from .helpers import APICase, country


class AuditPolicyTests(APICase):
    def test_command_uses_null_and_admin_api_serializes_null(self):
        country()
        call_command('recalcular_irpc', stdout=StringIO())
        event = LogActividad.objects.get(entidad_afectada='IndiceRiesgo')
        self.assertIsNone(event.usuario_id)
        self.authenticate(self.admin)
        response = self.client.get('/api/auditoria/?entidad_afectada=IndiceRiesgo')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertIsNone(response.data['results'][0]['usuario'])
        self.assertEqual(response.data['results'][0]['id'], event.pk)

    def test_audit_api_is_admin_only_and_read_only(self):
        self.assertEqual(self.client.get('/api/auditoria/').status_code, 401)
        self.authenticate()
        self.assertEqual(self.client.get('/api/auditoria/').status_code, 403)
        self.authenticate(self.admin)
        self.assertEqual(self.client.post('/api/auditoria/', {}).status_code, 405)

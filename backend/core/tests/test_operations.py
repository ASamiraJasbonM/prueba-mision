from io import StringIO
from decimal import Decimal
from unittest.mock import patch
from django.core.management import call_command
from core.models import IndiceRiesgo, IndicadorEconomico, LogActividad
from .helpers import APICase, country


class OperationTests(APICase):
    def setUp(self):
        super().setUp()
        self.pais = country()
        self.authenticate()

    def test_request_log_has_metadata_without_body_or_query(self):
        with self.assertLogs('datapulse', level='INFO') as captured:
            self.client.get('/api/paises/?password=secret-value', HTTP_AUTHORIZATION='Bearer secret-token')
        requests = [record for record in captured.records if record.msg == 'request']
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].path, '/api/paises/')
        self.assertEqual(requests[0].usuario_id, self.user.pk)
        self.assertGreaterEqual(requests[0].duracion_ms, 0)
        self.assertNotIn('secret-value', str(requests[0].__dict__))
        self.assertNotIn('secret-token', str(requests[0].__dict__))

    def test_sync_fin_log_includes_processed_countries(self):
        import json
        from core.services.sync import sync_indicators
        from core.observability import JsonFormatter
        payload = [{'pages': 1}, [{'date': '2025', 'value': Decimal('4')}]]
        with patch('core.services.sync.get_json', return_value=payload):
            with self.assertLogs('datapulse', level='INFO') as captured:
                report = sync_indicators()
        fin = [record for record in captured.records if record.msg == 'sync_indicadores_fin']
        self.assertEqual(len(fin), 1)
        self.assertEqual(fin[0].paises_procesados, report['paises_procesados'])
        self.assertEqual(fin[0].paises, report['paises'])
        parsed = json.loads(JsonFormatter().format(fin[0]))
        self.assertEqual(parsed['paises_procesados'], report['paises_procesados'])
        self.assertEqual(parsed['paises'], report['paises'])

    def test_indicator_sync_creates_info_alert(self):
        from core.models import Alerta
        from core.services.sync import sync_indicators
        payload = [{'pages': 1}, [{'date': '2025', 'value': Decimal('4')}]]
        with patch('core.services.sync.get_json', return_value=payload):
            sync_indicators()
        alert = Alerta.objects.get(tipo_alerta='INDICADOR', severidad='INFO')
        self.assertEqual(alert.pais, self.pais)

    def test_sync_command_chains_risk_and_is_repeatable(self):
        payload = [{'pages': 1}, [{'date': '2025', 'value': Decimal('4')}]]
        with patch('core.services.sync.get_json', return_value=payload):
            call_command('sync_indicadores', stdout=StringIO())
            call_command('sync_indicadores', stdout=StringIO())
        self.assertEqual(IndicadorEconomico.objects.count(), 6)
        self.assertEqual(IndiceRiesgo.objects.count(), 1)
        self.assertTrue(LogActividad.objects.filter(entidad_afectada='IndicadorEconomico').exists())

    def test_all_commands_are_available_offline(self):
        with patch('core.services.sync.get_json', side_effect=ValueError('Offline')):
            call_command('sync_tipos_cambio', stdout=StringIO())
            call_command('sync_paises', stdout=StringIO())
        call_command('recalcular_irpc', stdout=StringIO())
        self.assertEqual(IndiceRiesgo.objects.count(), 1)

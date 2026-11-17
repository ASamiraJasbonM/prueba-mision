from io import StringIO
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework.test import APIClient
from core.models import Pais, TipoCambio, IndicadorEconomico, Usuario, Portafolio, Posicion, IndiceRiesgo, Alerta
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SeedTests(TestCase):
    def test_seed_on_later_days_keeps_position_identity_and_actual_rate_variation(self):
        now = timezone.now()
        for offset in range(3):
            with patch('django.utils.timezone.now', return_value=now+timedelta(days=offset)):
                call_command('seed_data', stdout=StringIO())
        self.assertEqual(Posicion.objects.count(), 5)
        today = now.date()+timedelta(days=2)
        latest = TipoCambio.objects.get(moneda_origen_id='COP', fecha=today)
        previous = TipoCambio.objects.get(moneda_origen_id='COP', fecha=today-timedelta(days=1))
        self.assertEqual(latest.tasa, previous.tasa)
        self.assertEqual(latest.variacion_porcentual, Decimal('0.0000'))

    def test_seed_is_complete_and_repeatable_without_network(self):
        call_command('seed_data', stdout=StringIO())
        counts = [model.objects.count() for model in [Pais, TipoCambio, IndicadorEconomico, Usuario, Portafolio, Posicion, IndiceRiesgo, Alerta]]
        call_command('seed_data', stdout=StringIO())
        self.assertEqual(counts, [model.objects.count() for model in [Pais, TipoCambio, IndicadorEconomico, Usuario, Portafolio, Posicion, IndiceRiesgo, Alerta]])
        self.assertEqual(Pais.objects.count(), 10)
        self.assertEqual(IndicadorEconomico.objects.count(), 300)
        self.assertEqual(TipoCambio.objects.count(), 310)
        self.assertEqual(Portafolio.objects.count(), 2)
        self.assertEqual(IndiceRiesgo.objects.count(), 10)
        self.assertEqual(Usuario.objects.count(), 3)
        client = APIClient()
        for email in ['admin@datapulse.com', 'analista@datapulse.com', 'viewer@datapulse.com']:
            cache.clear()
            response = client.post('/api/auth/login/', {'email': email, 'password': 'DataPulse2026!'})
            self.assertEqual(response.status_code, 200)
        client.force_authenticate(Usuario.objects.get(email='analista@datapulse.com'))
        self.assertEqual(client.get('/api/dashboard/mapa/').data['count'], 10)
        self.assertEqual(client.get('/api/dashboard/tendencias/?paises=CO,BR,MX').data['count'], 15)
        self.assertEqual(client.get('/api/riesgo/CO/').status_code, 200)

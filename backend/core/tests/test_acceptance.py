from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from threading import Barrier
from unittest.mock import patch

from django.core.management import call_command
from django.core.cache import cache
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature, override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from core.models import Usuario, Portafolio, Posicion, IndicadorEconomico, IndiceRiesgo
from .helpers import APICase, country


class AcceptanceTests(APICase):
    def setUp(self):
        super().setUp()
        self.pais = country()
        self.authenticate()

    def test_unknown_api_route_has_uniform_error(self):
        response = self.client.get('/api/no-existe/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error']['code'], 'not_found')

    def test_rollback_when_audit_fails(self):
        portfolio = Portafolio.objects.create(usuario=self.user, nombre='Transaccional')
        with patch('core.services.portfolios.audit', side_effect=RuntimeError('Audit failure')):
            response = self.client.post(f'/api/portafolios/{portfolio.pk}/posiciones/', {
                'pais': 'CO', 'tipo_activo': 'RENTA_FIJA', 'monto_inversion_usd': '1000.00',
                'fecha_entrada': str(timezone.now().date()-timedelta(days=1)), 'version': 1})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(Posicion.objects.count(), 0)
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.version, 1)
        self.assertNotIn('Audit failure', str(response.data))

    def test_expired_token(self):
        self.client.force_authenticate(None)
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)

    def test_country_risk_detail_contains_history(self):
        from core.services.risk import recalculate
        recalculate()
        response = self.client.get('/api/riesgo/CO/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['historico']), 1)
        self.assertIn('historico_url', response.data)

    def test_reverted_inputs_create_current_result(self):
        from core.services.risk import recalculate
        indicator = IndicadorEconomico.objects.create(pais=self.pais, tipo='INFLACION', valor='4', unidad='PORCENTAJE', anio=2025)
        recalculate()
        first = IndiceRiesgo.objects.first().indice_compuesto
        indicator.valor = Decimal('60')
        indicator.save(update_fields=['valor'])
        recalculate()
        indicator.valor = Decimal('4')
        indicator.save(update_fields=['valor'])
        recalculate()
        self.assertEqual(IndiceRiesgo.objects.count(), 3)
        ranking = self.client.get('/api/riesgo/').data['results'][0]
        self.assertEqual(ranking['variacion'], '17.50')
        self.assertEqual(ranking['tendencia'], 'SUBE')
        self.assertEqual(IndiceRiesgo.objects.first().indice_compuesto, first)
        recalculate()
        self.assertEqual(IndiceRiesgo.objects.count(), 3)


@skipUnlessDBFeature('has_select_for_update')
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def test_two_writers_same_version_only_one_succeeds(self):
        from core.api import Conflict
        from core.services.portfolios import add_position
        owner = Usuario.objects.create_user('writer@test.com')
        pais = country()
        portfolio = Portafolio.objects.create(usuario=owner, nombre='Concurrente')
        barrier = Barrier(2)
        def write():
            connections.close_all()
            try:
                user = Usuario.objects.get(pk=owner.pk)
                country_row = type(pais).objects.get(pk=pais.pk)
                barrier.wait(timeout=10)
                add_position(user, portfolio.pk, 1, {'pais': country_row, 'tipo_activo': 'RENTA_FIJA',
                    'monto_inversion_usd': Decimal('1000.00'), 'fecha_entrada': timezone.now().date()-timedelta(days=1)})
                return 'created'
            except Conflict:
                return 'conflict'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: write(), range(2)))
        self.assertCountEqual(results, ['created', 'conflict'])
        self.assertEqual(Posicion.objects.count(), 1)
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.version, 2)

    def test_large_decimal_is_preserved(self):
        pais = country()
        row = IndicadorEconomico.objects.create(pais=pais, tipo='PIB', anio=2025,
            valor=Decimal('1234567890123456789012.123456'), unidad='USD')
        row.refresh_from_db()
        self.assertEqual(row.valor, Decimal('1234567890123456789012.123456'))

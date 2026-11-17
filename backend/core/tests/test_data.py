from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase
from core.models import IndicadorEconomico, TipoCambio
from .helpers import APICase, country


class DataTests(APICase):
    def setUp(self):
        super().setUp()
        self.pais = country()
        self.authenticate()

    def test_country_contract_and_filters(self):
        response = self.client.get('/api/paises/?region=ANDINA&search=CO')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['moneda_codigo'], 'COP')
        self.assertIsInstance(response.data['results'][0]['latitud'], str)
        self.assertEqual(self.client.get('/api/paises/?region=CARIBE').data['count'], 0)

    def test_indicators_and_dates(self):
        IndicadorEconomico.objects.create(pais=self.pais, tipo='PIB', anio=2025, valor='123456789.123456', unidad='USD')
        response = self.client.get('/api/paises/CO/indicadores/?tipo=PIB&anio=2025')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['valor'], '123456789.123456')
        self.assertEqual(self.client.get('/api/paises/CO/indicadores/?anio=abc').status_code, 400)
        self.assertEqual(self.client.get('/api/paises/CO/tipo-cambio/?fecha_desde=incorrecta').status_code, 400)

    def test_sync_is_admin_only_and_idempotent_partial_failure(self):
        self.assertEqual(self.client.post('/api/paises/sync-indicadores/').status_code, 403)
        from core.services.sync import sync_indicators
        def response(url, **kwargs):
            if 'NY.GDP.MKTP.CD' in url:
                return [{'pages': 1}, [{'date': '2025', 'value': Decimal('123456789.123456')}]]
            raise ValueError('Servicio no disponible')
        with patch('core.services.sync.get_json', side_effect=response):
            first = sync_indicators()
            second = sync_indicators()
        self.assertEqual(first['actualizados'], 1)
        self.assertEqual(second['actualizados'], 0)
        self.assertEqual(len(first['errores']), 5)
        self.assertEqual(IndicadorEconomico.objects.count(), 1)
        self.assertEqual(IndicadorEconomico.objects.get().unidad, 'USD')

    def test_exchange_inverse_and_previous_utc_day(self):
        from core.services.sync import sync_exchange
        today = date(2026, 11, 17)
        TipoCambio.objects.create(moneda_origen=self.pais.moneda, tasa='0.000200000000', fecha=today-timedelta(days=1))
        payload = {'result': 'success', 'base_code': 'USD', 'time_last_update_unix': 1794873600, 'rates': {'COP': Decimal('4000')}}
        with patch('core.services.sync.get_json', return_value=payload):
            sync_exchange(business_date=today)
            sync_exchange(business_date=today)
        rate = TipoCambio.objects.get(fecha=today)
        self.assertEqual(rate.tasa, Decimal('0.000250000000'))
        self.assertEqual(rate.variacion_porcentual, Decimal('25.0000'))
        self.assertEqual(TipoCambio.objects.count(), 2)


class UnitTests(SimpleTestCase):
    def test_scale_conversion_uses_half_up(self):
        from core.services.numbers import usd_miles_millones_a_usd
        self.assertEqual(usd_miles_millones_a_usd(Decimal('1.000000000005')), Decimal('1000000000.01'))

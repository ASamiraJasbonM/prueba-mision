from decimal import Decimal
from unittest.mock import patch

import requests
from django.test import TestCase
from django.utils import timezone

from core.models import IndicadorEconomico
from core.services.sync import sync_indicators
from .helpers import country


class BatchedSyncTests(TestCase):
    def setUp(self):
        self.colombia = country('CO', 'COP')
        self.brasil = country('BR', 'BRL')
        self.year = timezone.now().year - 1

    def test_batch_routes_values_to_the_right_country_in_six_requests(self):
        payload = [{'pages': 1}, [
            {'country': {'id': 'CO'}, 'date': str(self.year), 'value': Decimal('4.123456')},
            {'country': {'id': 'BR'}, 'date': str(self.year), 'value': Decimal('8.654321')},
        ]]
        with patch('core.services.sync.get_json', return_value=payload) as fetch:
            result = sync_indicators(batch=True)
        self.assertEqual(fetch.call_count, 6)
        self.assertEqual(result['actualizados'], 12)
        self.assertEqual(result['errores'], [])
        self.assertEqual(IndicadorEconomico.objects.get(pais=self.brasil, tipo='PIB').valor, Decimal('8.654321'))
        self.assertEqual(IndicadorEconomico.objects.get(pais=self.colombia, tipo='PIB').valor, Decimal('4.123456'))

    def test_bad_country_row_does_not_discard_other_countries(self):
        payload = [{'pages': 1}, [
            {'country': {'id': 'BR'}, 'date': str(self.year), 'value': 'invalid'},
            {'country': {'id': 'CO'}, 'date': str(self.year), 'value': '4'},
            {'country': {'id': 'XX'}, 'date': str(self.year), 'value': '100'},
        ]]
        with patch('core.services.sync.get_json', return_value=payload):
            result = sync_indicators(batch=True)
        self.assertEqual(result['actualizados'], 6)
        self.assertEqual(len(result['errores']), 6)
        self.assertEqual({error['pais'] for error in result['errores']}, {'BR'})
        self.assertEqual(IndicadorEconomico.objects.filter(pais=self.colombia).count(), 6)
        self.assertEqual(IndicadorEconomico.objects.filter(pais=self.brasil).count(), 0)

    def test_failed_indicator_keeps_existing_data_and_continues_other_indicators(self):
        existing = IndicadorEconomico.objects.create(pais=self.colombia, tipo='INFLACION',
            anio=self.year, valor='7', unidad='PORCENTAJE', fuente='MANUAL')
        def response(url, **kwargs):
            if 'FP.CPI.TOTL.ZG' in url:
                raise requests.ConnectionError('Unavailable')
            return [{'pages': 1}, [{'country': {'id': 'CO'}, 'date': str(self.year), 'value': '4'}]]
        with patch('core.services.sync.get_json', side_effect=response):
            result = sync_indicators(batch=True)
        existing.refresh_from_db()
        self.assertEqual(existing.valor, Decimal('7'))
        self.assertEqual(existing.fuente, 'MANUAL')
        self.assertEqual(result['actualizados'], 5)
        self.assertEqual({error['pais'] for error in result['errores']}, {'CO', 'BR'})

    def test_batch_falls_back_per_country_on_connection_error(self):
        def response(url, **kwargs):
            if ';' in url:
                raise requests.ConnectionError('reset by peer')
            code = url.split('/country/')[1].split('/indicator/')[0]
            return [{'pages': 1}, [{'country': {'id': code}, 'date': str(self.year), 'value': '4'}]]
        with patch('core.services.sync.get_json', side_effect=response) as fetch:
            result = sync_indicators(batch=True)
        self.assertEqual(result['errores'], [])
        self.assertEqual(result['actualizados'], 12)
        self.assertEqual(IndicadorEconomico.objects.count(), 12)
        self.assertEqual(fetch.call_count, 18)

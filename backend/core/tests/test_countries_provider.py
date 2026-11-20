from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from core.models import LogActividad
from core.services.sync import sync_countries
from .helpers import APICase, country


@override_settings(REST_COUNTRIES_API_KEY='test-key-not-real')
class CountriesProviderTests(APICase):
    def setUp(self):
        super().setUp()
        self.pais = country()

    def payload(self):
        return {'data': {'objects': [{'codes': {'alpha_2': 'CO'}, 'names': {'official': 'República de Colombia'},
            'population': 52000000, 'flag': {'url_svg': 'https://flags.restcountries.com/v5/svg/co.svg'},
            'currencies': [{'code': 'COP', 'name': 'Peso colombiano'}],
            'coordinates': {'lat': '4.5709', 'lng': '-74.2973'}}]}}

    def test_demo_response_is_never_persisted_as_real_country_data(self):
        payload = self.payload()
        payload['data']['_demo'] = {'message': 'Sample only'}
        with patch('core.services.sync.get_json', return_value=payload):
            report = sync_countries()
        self.assertEqual(report['actualizados'], 0)
        self.pais.refresh_from_db()
        self.assertEqual(self.pais.nombre, 'CO')

    def test_valid_response_updates_country_and_command_reports_failure(self):
        with patch('core.services.sync.get_json', return_value=self.payload()):
            report = sync_countries()
        self.assertEqual(report['actualizados'], 1)
        self.pais.refresh_from_db()
        self.assertEqual(self.pais.nombre, 'República de Colombia')
        self.assertEqual(self.pais.moneda_id, 'COP')
        self.assertTrue(LogActividad.objects.filter(entidad_afectada='Pais', accion='EDITAR').exists())
        with patch('core.services.sync.get_json', side_effect=ValueError('private provider error')):
            with self.assertRaises(CommandError):
                call_command('sync_paises', stdout=StringIO())

    def test_invalid_response_does_not_stop_remaining_countries(self):
        country('BR', 'BRL')
        valid = self.payload()
        with patch('core.services.sync.get_json', side_effect=lambda url, **kwargs: [] if url.endswith('/BR') else valid):
            report = sync_countries()
        self.assertEqual(report['paises_procesados'], 2)
        self.assertEqual(report['actualizados'], 1)
        self.assertEqual(len(report['errores']), 1)

from datetime import timedelta
from django.test import override_settings
from django.utils import timezone
from core.models import Portafolio, Posicion
from .helpers import APICase, country


class DeleteVersionTests(APICase):
    def setUp(self):
        super().setUp()
        pais = country()
        self.portfolio = Portafolio.objects.create(nombre='Versionado', usuario=self.user)
        self.position = Posicion.objects.create(portafolio=self.portfolio, pais=pais, tipo_activo='RENTA_FIJA',
            monto_inversion_usd='1000.00', fecha_entrada=timezone.now().date()-timedelta(days=1))
        self.url = f'/api/portafolios/{self.portfolio.pk}/'
        self.position_url = self.url+f'posiciones/{self.position.pk}/'
        self.authenticate()

    def advance_version(self):
        response = self.client.put(self.url, {'nombre': 'Cambio', 'descripcion': '', 'es_publico': False, 'version': 1})
        self.assertEqual(response.status_code, 200)

    def test_stale_delete_portfolio_returns_409_using_header(self):
        self.advance_version()
        response = self.client.delete(self.url, {'version': 2}, format='json', HTTP_IF_MATCH='"1"')
        self.assertEqual(response.status_code, 409)
        self.portfolio.refresh_from_db()
        self.assertTrue(self.portfolio.activo)
        self.assertEqual(self.portfolio.version, 2)

    def test_stale_delete_position_returns_409_using_parent_header(self):
        self.advance_version()
        response = self.client.delete(self.position_url, {'version': 2}, format='json', HTTP_IF_MATCH='"1"')
        self.assertEqual(response.status_code, 409)
        self.position.refresh_from_db()
        self.assertIsNone(self.position.fecha_salida)

    def test_current_header_works_without_delete_body(self):
        self.assertEqual(self.client.get(self.url)['ETag'], '"1"')
        self.assertEqual(self.client.get(self.url+'resumen/')['ETag'], '"1"')
        self.assertEqual(self.client.delete(self.position_url, HTTP_IF_MATCH='"1"').status_code, 200)
        self.assertEqual(self.client.get(self.url)['ETag'], '"2"')
        self.assertEqual(self.client.delete(self.url, HTTP_IF_MATCH='"2"').status_code, 204)

    def test_missing_or_invalid_header_cannot_fall_back_to_body(self):
        for url in [self.url, self.position_url]:
            for value in [None, '*', 'W/"1"', '1', '"0"', '"1", "2"', '"abc"']:
                with self.subTest(url=url, header=value):
                    headers = {'HTTP_IF_MATCH': value} if value is not None else {}
                    response = self.client.delete(url, {'version': 1}, format='json', **headers)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('If-Match', str(response.data))
        self.assertTrue(Portafolio.objects.filter(pk=self.portfolio.pk).exists())
        self.position.refresh_from_db()
        self.assertIsNone(self.position.fecha_salida)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:4200'])
    def test_browser_can_send_if_match_and_read_etag(self):
        response = self.client.options(self.url, HTTP_ORIGIN='http://localhost:4200',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='DELETE', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='if-match,authorization')
        self.assertEqual(response.status_code, 200)
        self.assertIn('if-match', response['Access-Control-Allow-Headers'].lower())
        response = self.client.get(self.url, HTTP_ORIGIN='http://localhost:4200')
        self.assertIn('etag', response['Access-Control-Expose-Headers'].lower())

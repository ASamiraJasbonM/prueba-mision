from datetime import timedelta
from django.utils import timezone
from core.models import Portafolio, Posicion
from .helpers import APICase, country


class ClosedPositionTests(APICase):
    def test_put_closed_position_returns_400_without_changing_history(self):
        pais = country()
        portfolio = Portafolio.objects.create(nombre='Histórico', usuario=self.user)
        today = timezone.now().date()
        position = Posicion.objects.create(portafolio=portfolio, pais=pais, tipo_activo='RENTA_FIJA',
            monto_inversion_usd='1000.00', fecha_entrada=today-timedelta(days=2),
            fecha_salida=today-timedelta(days=1), notas='Original')
        self.authenticate()
        response = self.client.put(f'/api/portafolios/{portfolio.pk}/posiciones/{position.pk}/', {
            'pais': pais.pk, 'tipo_activo': 'RENTA_FIJA', 'monto_inversion_usd': '2000.00',
            'fecha_entrada': str(position.fecha_entrada), 'fecha_salida': None, 'notas': 'Cambio', 'version': 1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
        position.refresh_from_db()
        portfolio.refresh_from_db()
        self.assertEqual(position.notas, 'Original')
        self.assertEqual(str(position.monto_inversion_usd), '1000.00')
        self.assertEqual(position.fecha_salida, today-timedelta(days=1))
        self.assertEqual(portfolio.version, 1)

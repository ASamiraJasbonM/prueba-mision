from datetime import timedelta
from django.utils import timezone
from core.models import IndicadorEconomico, TipoCambio
from .helpers import APICase, country


class SearchExtensionTests(APICase):
    def test_indicator_search_filters_by_type_or_source(self):
        pais = country()
        IndicadorEconomico.objects.create(pais=pais, tipo='PIB', anio=2025, valor='100', unidad='USD', fuente='MANUAL')
        IndicadorEconomico.objects.create(pais=pais, tipo='INFLACION', anio=2025, valor='5', unidad='PORCENTAJE', fuente='WORLD_BANK')
        self.authenticate()
        response = self.client.get('/api/paises/CO/indicadores/?search=WORLD_BANK')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['tipo'], 'INFLACION')
        self.assertEqual(self.client.get('/api/paises/CO/indicadores/?search=PIB').data['count'], 1)

    def test_exchange_search_filters_by_currency_or_source(self):
        pais = country()
        for days, source in [(1, 'DEMO_SINTETICO'), (0, 'EXCHANGE_RATE_API')]:
            TipoCambio.objects.create(moneda_origen=pais.moneda, tasa='0.00025',
                fecha=timezone.now().date()-timedelta(days=days), fuente=source)
        self.authenticate()
        response = self.client.get('/api/paises/CO/tipo-cambio/?search=DEMO_SINTETICO')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fuente'], 'DEMO_SINTETICO')

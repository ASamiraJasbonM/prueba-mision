from django.utils import timezone
from core.models import IndiceRiesgo, IndicadorEconomico, Portafolio, Alerta
from .helpers import APICase, country


class DashboardTests(APICase):
    def setUp(self):
        super().setUp()
        self.pais = country()
        self.authenticate()

    def test_kpis_are_scoped_and_decimal(self):
        Portafolio.objects.create(usuario=self.user, nombre='Propio')
        Portafolio.objects.create(usuario=self.admin, nombre='Ajeno', es_publico=True)
        Alerta.objects.create(pais=self.pais, tipo_alerta='RIESGO', severidad='INFO', titulo='Demo', mensaje='Demo')
        IndiceRiesgo.objects.create(pais=self.pais, score_economico=70, score_cambiario=70,
            score_estabilidad=70, indice_compuesto='70.25', nivel_riesgo='MODERADO')
        response = self.client.get('/api/dashboard/resumen/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['portafolios_usuario'], 1)
        self.assertEqual(response.data['alertas_activas'], 1)
        self.assertEqual(response.data['promedio_irpc_region'], '70.25')
        mapa = self.client.get('/api/dashboard/mapa/')
        self.assertEqual(mapa.data['results'][0]['color'], '#eab308')

    def test_five_year_series_keeps_missing_points(self):
        year = timezone.now().year-1
        IndicadorEconomico.objects.create(pais=self.pais, tipo='INFLACION', anio=year, valor='5.123456', unidad='PORCENTAJE')
        response = self.client.get('/api/dashboard/tendencias/?tipo=INFLACION&paises=CO')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(response.data['results'][-1]['valor'], '5.123456')
        self.assertIsNone(response.data['results'][0]['valor'])
        self.assertEqual(self.client.get('/api/dashboard/tendencias/?tipo=INVALIDO').status_code, 400)
        self.assertEqual(self.client.get('/api/dashboard/tendencias/?paises=CO,BR,MX,AR').status_code, 400)

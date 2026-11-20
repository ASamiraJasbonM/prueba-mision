from datetime import timedelta
from django.utils import timezone
from core.models import IndiceRiesgo
from .helpers import APICase, country


class RiskQualityTests(APICase):
    def test_complete_inputs_do_not_hide_demo_manual_or_stale_data(self):
        pais = country()
        now = timezone.now()
        sources = {key: {'fuente': 'WORLD_BANK', 'anio': now.year-1} for key in
            ['PIB', 'PIB_PERCAPITA', 'INFLACION', 'DESEMPLEO', 'DEUDA_PIB', 'BALANZA_COMERCIAL']}
        sources['DEUDA_PIB'] = {'fuente': 'MANUAL', 'anio': now.year-5}
        sources['INFLACION'] = {'fuente': 'DEMO_SINTETICO', 'anio': now.year-1}
        IndiceRiesgo.objects.create(pais=pais, score_economico=80, score_cambiario=80,
            score_estabilidad=80, indice_compuesto=80, nivel_riesgo='BAJO',
            fecha_calculo=now-timedelta(days=3), detalle_calculo={'parcial': False, 'fuentes': sources,
                'tasas': [{'fecha': str(now.date()-timedelta(days=4)), 'fuente': 'DEMO_SINTETICO'}]})
        self.authenticate()
        response = self.client.get('/api/riesgo/CO/')
        self.assertIn('calidad_datos', response.data)
        quality = response.data['calidad_datos']
        self.assertEqual(quality['indicadores_externos'], 4)
        self.assertEqual(quality['indicadores_manuales'], 1)
        self.assertEqual(quality['indicadores_sinteticos'], 1)
        self.assertEqual(quality['tasas_sinteticas'], 1)
        self.assertEqual(quality['indicadores_rezagados'], ['DEUDA_PIB'])
        self.assertEqual(quality['dias_desde_calculo'], 3)
        self.assertEqual(quality['dias_desde_tasa'], 4)
        self.assertFalse(quality['solo_fuentes_externas'])
        self.assertTrue(quality['requiere_revision'])
        summary = self.client.get('/api/dashboard/resumen/').data
        self.assertEqual(summary['paises_con_datos_no_verificados'], 1)
        self.assertEqual(summary['paises_con_datos_rezagados'], 1)

    def test_legacy_risk_without_metadata_is_unknown_instead_of_verified(self):
        pais = country()
        IndiceRiesgo.objects.create(pais=pais, score_economico=80, score_cambiario=80,
            score_estabilidad=80, indice_compuesto=80, nivel_riesgo='BAJO')
        self.authenticate()
        response = self.client.get('/api/riesgo/CO/')
        self.assertIn('calidad_datos', response.data)
        self.assertFalse(response.data['calidad_datos']['solo_fuentes_externas'])
        self.assertEqual(response.data['calidad_datos']['indicadores_sin_origen'], 6)

    def test_external_source_without_year_cannot_be_described_as_recent(self):
        pais = country()
        sources = {key: {'fuente': 'WORLD_BANK'} for key in
            ['PIB', 'PIB_PERCAPITA', 'INFLACION', 'DESEMPLEO', 'DEUDA_PIB', 'BALANZA_COMERCIAL']}
        IndiceRiesgo.objects.create(pais=pais, score_economico=80, score_cambiario=80,
            score_estabilidad=80, indice_compuesto=80, nivel_riesgo='BAJO',
            detalle_calculo={'parcial': False, 'fuentes': sources,
                'tasas': [{'fecha': str(timezone.now().date()), 'fuente': 'EXCHANGE_RATE_API'}]})
        self.authenticate()
        quality = self.client.get('/api/riesgo/CO/').data['calidad_datos']
        self.assertTrue(quality['requiere_revision'])

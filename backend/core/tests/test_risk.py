from decimal import Decimal
from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone
from core.models import Alerta, IndiceRiesgo, IndicadorEconomico
from .helpers import APICase, country


class ScoreTests(SimpleTestCase):
    def test_economic_threshold_uses_raw_value(self):
        from core.services.risk import score_economico
        self.assertEqual(score_economico({'INFLACION': Decimal('10')}), Decimal('90'))
        self.assertEqual(score_economico({'INFLACION': Decimal('10.0001')}), Decimal('75'))

    def test_pdf_formula_and_explicit_negative_indicators(self):
        from core.services.risk import calculate_scores
        data = {key: Decimal(val) for key, val in {'PIB_PERCAPITA': '6800', 'INFLACION': '9.2',
            'DESEMPLEO': '11.3', 'DEUDA_PIB': '55', 'BALANZA_COMERCIAL': '-4.2', 'CRECIMIENTO_PIB': '1.5'}.items()}
        result = calculate_scores(data, [Decimal('.8'), Decimal('-.8')], Decimal('1.5'))
        self.assertEqual(result['score_economico'], Decimal('60.00'))
        self.assertEqual(result['score_cambiario'], Decimal('90.00'))
        self.assertEqual(result['score_estabilidad'], Decimal('70.00'))
        self.assertEqual(result['indice_compuesto'], Decimal('72.00'))

    def test_classifies_after_half_up_quantization(self):
        from core.services.risk import classify
        self.assertEqual(classify(Decimal('74.995')), 'BAJO')
        self.assertEqual(classify(Decimal('74.994')), 'MODERADO')
        self.assertEqual(classify(Decimal('24.995')), 'ALTO')


class RiskApiTests(APICase):
    def setUp(self):
        super().setUp()
        self.pais = country()
        self.authenticate()

    def test_partial_calculation_and_idempotence(self):
        from core.services.risk import recalculate
        recalculate()
        recalculate()
        self.assertEqual(IndiceRiesgo.objects.count(), 1)
        risk = IndiceRiesgo.objects.get()
        self.assertTrue(risk.detalle_calculo['parcial'])
        self.assertIn('INFLACION', risk.detalle_calculo['faltantes'])
        self.assertEqual(self.client.get('/api/riesgo/').status_code, 200)
        self.assertEqual(self.client.post('/api/riesgo/calcular/').status_code, 403)

    def test_alert_deduplication_and_global_read_is_per_user(self):
        from core.services.risk import recalculate
        IndicadorEconomico.objects.create(pais=self.pais, tipo='INFLACION', valor='60', unidad='PORCENTAJE', anio=2025)
        recalculate()
        recalculate()
        self.assertEqual(Alerta.objects.filter(severidad='CRITICAL').count(), 1)
        alert = Alerta.objects.get()
        self.assertEqual(self.client.put(f'/api/alertas/{alert.pk}/leer/').status_code, 200)
        self.assertEqual(self.client.get('/api/alertas/?leida=false').data['count'], 0)
        self.authenticate(self.viewer)
        self.assertEqual(self.client.get('/api/alertas/?leida=false').data['count'], 1)
        self.assertEqual(self.client.put('/api/alertas/leer-todas/').status_code, 200)
        self.assertEqual(self.client.get('/api/alertas/resumen/').data['no_leidas'], 0)

    def test_risk_drop_creates_warning_and_critical(self):
        from core.services.risk import recalculate
        recalculate()
        from core.models import TipoCambio
        for tipo, value in {'INFLACION': '80', 'PIB_PERCAPITA': '1000', 'DESEMPLEO': '20',
                            'DEUDA_PIB': '90', 'BALANZA_COMERCIAL': '-15', 'PIB': '50'}.items():
            IndicadorEconomico.objects.create(pais=self.pais, tipo=tipo, anio=2025, valor=value,
                unidad='USD' if tipo in ['PIB', 'PIB_PERCAPITA'] else 'PORCENTAJE')
        IndicadorEconomico.objects.create(pais=self.pais, tipo='PIB', anio=2024, valor='100', unidad='USD')
        for day in range(31):
            TipoCambio.objects.create(moneda_origen=self.pais.moneda,
                fecha=timezone.now().date()-timedelta(days=30-day),
                tasa=Decimal('1')-Decimal(day)/100,
                variacion_porcentual=Decimal('4') if day % 2 else Decimal('-4'))
        recalculate()
        self.assertTrue(Alerta.objects.filter(tipo_alerta='RIESGO', severidad='CRITICAL').exists())
        self.assertTrue(Alerta.objects.filter(tipo_alerta='RIESGO', severidad='WARNING').exists())

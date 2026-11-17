from decimal import Decimal
from django.test import SimpleTestCase
from core.services.risk import calculate_scores
from core.models import IndicadorEconomico
from .helpers import APICase, country
from .test_irpc import EXAMPLE


class RiskFactorTests(SimpleTestCase):
    def test_count_and_weighted_effect(self):
        from core.services.risk import contar_indicadores_en_riesgo, risk_factors
        healthy = {key: Decimal(value) for key, value in {'PIB_PERCAPITA': '13000', 'INFLACION': '3',
            'DESEMPLEO': '5', 'DEUDA_PIB': '30', 'BALANZA_COMERCIAL': '1', 'CRECIMIENTO_PIB': '3'}.items()}
        cases = [('ejemplo', EXAMPLE, 5, '70.00', '72.00'),
                 ('recesion', {**EXAMPLE, 'CRECIMIENTO_PIB': Decimal('-3')}, 6, '35.00', '61.50'),
                 ('sanos', healthy, 0, '100.00', '97.00')]
        for label, data, count, stability, composite in cases:
            with self.subTest(scenario=label):
                self.assertEqual(contar_indicadores_en_riesgo(data), count)
                self.assertEqual(len(risk_factors(data)), count)
                result = calculate_scores(data, [Decimal('.8'), Decimal('-.8')], Decimal('1.5'))
                self.assertEqual(result['score_estabilidad'], Decimal(stability))
                self.assertEqual(result['indice_compuesto'], Decimal(composite))


class RiskFactorDetailTests(APICase):
    def test_stored_detail_identifies_penalized_factors(self):
        from core.services.risk import calculate_country
        pais = country()
        for kind, value in EXAMPLE.items():
            if kind == 'CRECIMIENTO_PIB':
                continue
            IndicadorEconomico.objects.create(pais=pais, tipo=kind, anio=2025, valor=value,
                unidad='USD' if kind == 'PIB_PERCAPITA' else 'PORCENTAJE')
        for year, value in [(2024, '100'), (2025, '101.5')]:
            IndicadorEconomico.objects.create(pais=pais, tipo='PIB', anio=year, valor=value, unidad='USD')
        risk, _ = calculate_country(pais)
        risk.refresh_from_db()
        detail = risk.detalle_calculo
        self.assertEqual(detail['cantidad_indicadores_en_riesgo'], 5)
        self.assertEqual(detail['penalizacion_concentracion'], '25.00')
        self.assertEqual({factor['factor'] for factor in detail['factores_en_riesgo']},
            {'PIB_PERCAPITA', 'INFLACION', 'DESEMPLEO', 'DEUDA_PIB', 'BALANZA_COMERCIAL'})
        inflation = next(factor for factor in detail['factores_en_riesgo'] if factor['factor'] == 'INFLACION')
        self.assertEqual(Decimal(inflation['penalizacion']), Decimal('10'))
        self.assertEqual(Decimal(inflation['valor']), Decimal('9.2'))

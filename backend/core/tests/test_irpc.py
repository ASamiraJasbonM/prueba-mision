from decimal import Decimal
from django.test import SimpleTestCase
from core.services.risk import classify, calculate_scores

EXAMPLE = {key: Decimal(value) for key, value in {
    'PIB_PERCAPITA': '6800', 'INFLACION': '9.2', 'DESEMPLEO': '11.3',
    'DEUDA_PIB': '55', 'BALANZA_COMERCIAL': '-4.2', 'CRECIMIENTO_PIB': '1.5',
}.items()}


class IrpcTraceabilityTests(SimpleTestCase):
    def test_three_documented_scenarios(self):
        from core.services.risk import compose_irpc
        cases = [
            ('PDF', '25', 3, '45', '80', '69.00', 'MODERADO'),
            ('Pseudocódigo + 3 negativos', '10', 3, '60', '80', '75.00', 'BAJO'),
            ('Pseudocódigo + regla propia', '10', 5, '60', '70', '72.00', 'MODERADO'),
        ]
        for scenario, inflation_penalty, negatives, economic, stability, composite, level in cases:
            with self.subTest(scenario=scenario):
                self.assertEqual(Decimal('100')-5-Decimal(inflation_penalty)-15-10, Decimal(economic))
                self.assertEqual(Decimal('100')-5-negatives*5, Decimal(stability))
                result = compose_irpc(Decimal(economic), Decimal('90'), Decimal(stability))
                self.assertEqual(result, Decimal(composite))
                self.assertEqual(classify(result), level)

    def test_production_uses_third_row(self):
        result = calculate_scores(EXAMPLE, [Decimal('.8'), Decimal('-.8')], Decimal('1.5'))
        self.assertEqual(result['score_economico'], Decimal('60.00'))
        self.assertEqual(result['score_estabilidad'], Decimal('70.00'))
        self.assertEqual(result['indice_compuesto'], Decimal('72.00'))
        self.assertEqual(result['nivel_riesgo'], 'MODERADO')

    def test_pdf_example_contradiction_documented(self):
        from core.services.risk import compose_irpc
        economic = Decimal('100') - 5 - Decimal('25') - 15 - 10
        stability = Decimal('100') - 5 - 3 * 5
        self.assertEqual(compose_irpc(economic, Decimal('90'), stability), Decimal('69.00'))
        result = calculate_scores(EXAMPLE, [Decimal('.8'), Decimal('-.8')], Decimal('1.5'))
        self.assertEqual(result['indice_compuesto'], Decimal('72.00'))

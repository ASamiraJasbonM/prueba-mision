from decimal import Decimal
from django.test import SimpleTestCase
from core.services.numbers import quantize
from core.services.risk import classify


class IrpcBoundaryTests(SimpleTestCase):
    def test_classification_matches_presented_two_decimal_value(self):
        cases = [('74.994', '74.99', 'MODERADO'), ('74.995', '75.00', 'BAJO'), ('74.999', '75.00', 'BAJO')]
        for raw, presented, level in cases:
            with self.subTest(raw=raw):
                self.assertEqual(quantize(Decimal(raw)), Decimal(presented))
                self.assertEqual(classify(Decimal(raw)), level)

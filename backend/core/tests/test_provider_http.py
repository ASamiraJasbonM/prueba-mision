from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase, override_settings
from core.services.http import get_json


class ProviderHttpTests(SimpleTestCase):
    @override_settings(EXTERNAL_API_TIMEOUT=60)
    def test_separate_connect_read_budget_is_bounded_and_keeps_decimal_precision(self):
        session = MagicMock()
        session.get.return_value.text = '{"value": 123.456789}'
        with patch('core.services.http.requests.Session') as factory:
            factory.return_value.__enter__.return_value = session
            result = get_json('https://api.worldbank.org/v2/')
        self.assertEqual(session.get.call_args.kwargs['timeout'], (5, 20))
        self.assertEqual(result['value'], Decimal('123.456789'))

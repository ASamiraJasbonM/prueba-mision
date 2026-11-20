from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase, override_settings
from core.services.http import get_json


class ProviderHttpTests(SimpleTestCase):
    @override_settings(EXTERNAL_API_TIMEOUT=60)
    def test_separate_connect_read_budget_is_bounded_and_keeps_decimal_precision(self):
        session = MagicMock()
        session.get.return_value.text = '{"value": 123.456789}'
        with patch("core.services.http.requests.Session") as factory:
            factory.return_value.__enter__.return_value = session
            result = get_json("https://api.worldbank.org/v2/")
        self.assertEqual(session.get.call_args.kwargs["timeout"], (5, 20))
        self.assertEqual(result["value"], Decimal("123.456789"))

    def test_retry_config_retries_connection_and_read_failures(self):
        session = MagicMock()
        session.get.return_value.text = "{}"
        with (
            patch("core.services.http.requests.Session") as factory,
            patch("core.services.http.Retry") as retry_cls,
            patch("core.services.http.HTTPAdapter") as adapter_cls,
        ):
            factory.return_value.__enter__.return_value = session
            get_json("https://api.worldbank.org/v2/")
        kwargs = retry_cls.call_args.kwargs
        self.assertLessEqual(kwargs["total"], 2)
        self.assertLessEqual(kwargs["connect"], 2)
        self.assertLessEqual(kwargs["read"], 2)
        self.assertIs(kwargs["respect_retry_after_header"], True)
        self.assertIn(429, kwargs["status_forcelist"])

    def test_provider_retry_after_cannot_outlive_the_worker_lease(self):
        from types import SimpleNamespace
        from urllib3.exceptions import ReadTimeoutError
        session = MagicMock()
        session.get.return_value.text = '{}'
        with patch('core.services.http.requests.Session') as factory:
            factory.return_value.__enter__.return_value = session
            get_json('https://api.worldbank.org/v2/')
        retry = session.mount.call_args.args[1].max_retries
        self.assertLessEqual(retry.get_retry_after(SimpleNamespace(headers={'Retry-After': '3600'})), 2)
        retry = retry.increment(method='GET', error=ReadTimeoutError(None, '/v2/', 'timed out'))
        self.assertLessEqual(retry.get_retry_after(SimpleNamespace(headers={'Retry-After': '3600'})), 2)

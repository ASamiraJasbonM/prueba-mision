from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError


class ApiBaseTests(SimpleTestCase):
    def tearDown(self):
        cache.clear()

    def test_unified_validation_error(self):
        from core.api import exception_handler
        result = exception_handler(ValidationError({'monto': ['Monto inválido.']}), {})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data['error']['code'], 'invalid')
        self.assertIn('monto', result.data['error']['details'])

    def test_anonymous_rate_limit(self):
        cache.clear()
        for _ in range(20):
            self.assertEqual(self.client.get('/api/health/').status_code, 200)
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('error', response.json())

    def test_schema_and_docs(self):
        cache.clear()
        self.assertEqual(self.client.get('/api/schema/').status_code, 200)
        self.assertEqual(self.client.get('/api/docs/').status_code, 200)

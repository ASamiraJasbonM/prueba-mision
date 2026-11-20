from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase


class ReadinessTests(TestCase):
    def test_ready_requires_database_and_cache_without_exposing_details(self):
        healthy = self.client.get('/api/ready/')
        self.assertEqual(healthy.status_code, 200)
        self.assertEqual(healthy.json(), {'status': 'ready'})
        with patch('django.db.backends.utils.CursorWrapper.execute',
                   side_effect=OperationalError('private-database-host password=secret')):
            response = self.client.get('/api/ready/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'not_ready')
        self.assertNotIn('private', str(response.content))
        self.assertNotIn('secret', str(response.content))

    def test_liveness_is_not_throttled_or_dependent_on_database(self):
        with patch('django.db.backends.utils.CursorWrapper.execute', side_effect=OperationalError('down')):
            for _ in range(25):
                response = self.client.get('/api/health/')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {})

    def test_missing_cache_table_is_not_ready(self):
        with patch('core.health.cache.get', side_effect=OperationalError('missing cache table')):
            response = self.client.get('/api/ready/')
        self.assertEqual(response.status_code, 503)

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from core.cache import SharedDatabaseCache
from django.db import connections
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils.module_loading import import_string


DATABASE_CACHE = {'default': {
    'BACKEND': 'core.cache.SharedDatabaseCache', 'LOCATION': 'datapulse_cache',
}}


@override_settings(CACHE_SHARED=True, CACHES=DATABASE_CACHE)
class SharedCacheTests(TestCase):
    def test_independent_cache_instances_share_the_same_state(self):
        first = SharedDatabaseCache('datapulse_cache', {})
        second = SharedDatabaseCache('datapulse_cache', {})
        self.assertTrue(first.set('worker-budget', [1, 2, 3], timeout=60))
        self.assertEqual(second.get('worker-budget'), [1, 2, 3])
        second.delete('worker-budget')
        self.assertIsNone(first.get('worker-budget'))

    def test_failed_budget_write_is_not_silently_accepted(self):
        from unittest.mock import patch
        cache.clear()
        with patch('core.cache.SharedDatabaseCache._base_set', return_value=False):
            response = self.client.get('/api/auth/captcha/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'throttle_unavailable')


@override_settings(CACHE_SHARED=True, CACHES=DATABASE_CACHE)
@skipUnlessDBFeature('has_select_for_update')
class ConcurrentThrottleTests(TransactionTestCase):
    def test_parallel_workers_cannot_exceed_one_remaining_slot(self):
        anon = import_string('core.throttling.SharedAnonRateThrottle')
        user = import_string('core.throttling.SharedUserRateThrottle')
        scoped = import_string('core.security_auth.ActionThrottle')
        for base in [anon, user, scoped]:
            with self.subTest(throttle=base.__name__):
                class OnePerMinute(base):
                    rate = '1/min'
                    THROTTLE_RATES = {'limited': '1/min'}

                cache.clear()
                barrier = Barrier(4)

                def request_slot(number):
                    connections.close_all()
                    try:
                        actor = (SimpleNamespace(pk=19, is_authenticated=True) if base is user else AnonymousUser())
                        request = SimpleNamespace(user=actor, headers={}, META={'REMOTE_ADDR': '203.0.113.19'})
                        barrier.wait(timeout=10)
                        return OnePerMinute().allow_request(request, SimpleNamespace(throttle_scope='limited'))
                    finally:
                        connections.close_all()

                with ThreadPoolExecutor(max_workers=4) as workers:
                    results = list(workers.map(request_slot, range(4)))
                self.assertEqual(results.count(True), 1)
                self.assertEqual(results.count(False), 3)

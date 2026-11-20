from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone
from .helpers import APICase, country


class AsyncSyncTests(APICase):
    def setUp(self):
        super().setUp()
        country()
        self.authenticate(self.admin)

    def submit(self):
        return self.client.post('/api/paises/sync-indicadores/')

    def test_submission_returns_202_without_contacting_provider_and_deduplicates(self):
        with patch('core.services.sync.get_json', side_effect=AssertionError('HTTP must not call providers')):
            first, second = self.submit(), self.submit()
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.data['estado'], 'PENDIENTE')
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(self.client.get(first.data['estado_url']).status_code, 200)
        self.authenticate(self.viewer)
        self.assertEqual(self.submit().status_code, 403)
        self.assertEqual(self.client.get(first.data['estado_url']).status_code, 403)

    def test_worker_persists_partial_result_and_safe_failure(self):
        response = self.submit()
        self.assertEqual(response.status_code, 202)
        def provider(url, **kwargs):
            if 'NY.GDP.MKTP.CD' in url:
                return [{'pages': 1}, [{'date': '2025', 'value': '100', 'country': {'id': 'CO'}}]]
            raise ValueError('external secret must not be exposed')
        with patch('core.services.sync.get_json', side_effect=provider):
            call_command('procesar_sincronizaciones', once=True)
        result = self.client.get(response.data['estado_url']).data
        self.assertEqual(result['estado'], 'PARCIAL')
        self.assertEqual(result['resultado']['actualizados'], 1)
        self.assertEqual(len(result['resultado']['errores']), 5)
        self.assertNotIn('external secret', str(result))
        next_job = self.submit()
        with patch('core.services.sync.get_json', side_effect=ValueError('private detail')):
            call_command('procesar_sincronizaciones', once=True)
        result = self.client.get(next_job.data['estado_url']).data
        self.assertEqual(result['estado'], 'FALLIDA')
        self.assertNotIn('private detail', str(result))

    def test_expired_lease_can_be_recovered_and_previous_owner_cannot_finish(self):
        response = self.submit()
        self.assertEqual(response.status_code, 202)
        from core.models import SyncJob
        from core.services.sync_jobs import claim_job, finish_job
        job = claim_job()
        self.assertIsNone(claim_job())
        SyncJob.objects.filter(pk=job.pk).update(lease_until=timezone.now()-timedelta(seconds=1))
        replacement = claim_job()
        self.assertEqual(replacement.pk, job.pk)
        self.assertNotEqual(replacement.lease_token, job.lease_token)
        self.assertFalse(finish_job(job, 'COMPLETADA', {}))
        self.assertTrue(finish_job(replacement, 'COMPLETADA', {}))

    def test_idempotency_key_reuses_accepted_job(self):
        first = self.client.post('/api/paises/sync-indicadores/', HTTP_IDEMPOTENCY_KEY='audit-one')
        self.assertEqual(first.status_code, 202)
        with patch('core.services.sync.get_json', side_effect=ValueError('offline')):
            call_command('procesar_sincronizaciones', once=True)
        repeat = self.client.post('/api/paises/sync-indicadores/', HTTP_IDEMPOTENCY_KEY='audit-one')
        self.assertEqual(repeat.status_code, 202)
        self.assertEqual(repeat.data['id'], first.data['id'])


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from core.models import Usuario, SyncJob


@skipUnlessDBFeature('has_select_for_update')
class QueueConcurrencyTests(TransactionTestCase):
    def test_concurrent_submissions_and_claims_do_not_duplicate_work(self):
        from core.services.sync_jobs import enqueue, claim_job
        user = Usuario.objects.create_user('queue@test.com', rol='ADMIN')
        barrier = Barrier(4)
        def submit(_):
            connections.close_all()
            try:
                actor = Usuario.objects.get(pk=user.pk)
                barrier.wait(timeout=10)
                return enqueue(actor).pk
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(submit, range(4)))
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(SyncJob.objects.count(), 1)
        barrier = Barrier(4)
        def claim(_):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return claim_job() is not None
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(claim, range(4)))
        self.assertEqual(claims.count(True), 1)

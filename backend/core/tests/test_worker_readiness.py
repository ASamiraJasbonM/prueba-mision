from datetime import timedelta
from django.test import override_settings
from django.utils import timezone
from .helpers import APICase


@override_settings(SYNC_WORKER_REQUIRED=True)
class WorkerReadinessTests(APICase):
    def test_required_worker_must_have_a_recent_heartbeat(self):
        from core.models import SyncWorkerPulse
        self.assertEqual(self.client.get('/api/ready/').status_code, 503)
        SyncWorkerPulse.objects.create(pk=1)
        self.assertEqual(self.client.get('/api/ready/').status_code, 200)
        SyncWorkerPulse.objects.filter(pk=1).update(actualizado=timezone.now()-timedelta(seconds=91))
        self.assertEqual(self.client.get('/api/ready/').status_code, 503)

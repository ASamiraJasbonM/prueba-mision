import json
import logging
from core.observability import JsonFormatter
from .helpers import APICase


class SiemContractTests(APICase):
    def test_failed_login_emits_safe_json(self):
        with self.assertLogs('datapulse', level='INFO') as captured:
            self.client.post('/api/auth/login/', {'email': self.user.email, 'password': 'never-log-this'})
        rows = [json.loads(JsonFormatter().format(record)) for record in captured.records]
        request = next(row for row in rows if row['event'] == 'request')
        self.assertEqual(request['status'], 401)
        self.assertEqual(request['path'], '/api/auth/login/')
        self.assertIn('duracion_ms', request)
        self.assertNotIn('never-log-this', json.dumps(rows))

    def test_audit_verification_json_retains_evidence_fields(self):
        record = logging.makeLogRecord({'msg': 'audit_verification', 'ok': False, 'broken_id': 42, 'checked': 41})
        row = json.loads(JsonFormatter().format(record))
        self.assertFalse(row['ok'])
        self.assertEqual(row['broken_id'], 42)

    def test_sync_error_contains_country_and_error_code_without_exception_text(self):
        from core.services.sync import report_error
        with self.assertLogs('datapulse', level='ERROR') as captured:
            report_error({'errores': []}, 'CO', 'WORLD_BANK', ValueError('provider-key-secret'))
        row = json.loads(JsonFormatter().format(captured.records[0]))
        self.assertEqual(row['event'], 'sync_error')
        self.assertEqual(row['pais'], 'CO')
        self.assertEqual(row['error_code'], 'ValueError')
        self.assertNotIn('provider-key-secret', json.dumps(row))

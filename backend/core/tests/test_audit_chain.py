import json
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction, DatabaseError
from django.test import override_settings
from core.audit import audit
from core.models import LogActividad
from core.services.audit_chain import verify
from .helpers import APICase


class AuditChainTests(APICase):
    def test_hash_chain_valid_after_100_inserts(self):
        for n in range(100):
            audit(self.user, 'CONSULTAR', self.user, {'n': n})
        output = StringIO()
        call_command('verificar_auditoria', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['checked'], 100)

    def test_tampering_detected_or_blocked(self):
        audit(self.user, 'CONSULTAR', self.user)
        if connection.vendor == 'postgresql':
            with self.assertRaises(DatabaseError), transaction.atomic():
                LogActividad.objects.update(detalle={'changed': True})
            with self.assertRaises(DatabaseError), transaction.atomic():
                LogActividad.objects.all().delete()
            self.assertTrue(verify()['ok'])
        else:
            LogActividad.objects.update(detalle={'changed': True})
            output = StringIO()
            with self.assertRaises(CommandError):
                call_command('verificar_auditoria', stdout=output)
            self.assertEqual(json.loads(output.getvalue())['cause'], 'hash')

    def test_wrong_hmac_key_detected(self):
        audit(self.user, 'CONSULTAR', self.user)
        with override_settings(AUDIT_HMAC_KEY='different-test-key'):
            self.assertEqual(verify()['cause'], 'hmac')

    def test_transaction_rollback_preserves_head(self):
        audit(self.user, 'CONSULTAR', self.user)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                audit(self.user, 'EDITAR', self.user)
                raise RuntimeError('rollback')
        self.assertEqual(verify()['checked'], 1)
        self.assertTrue(verify()['ok'])

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AuditMigrationTests(TransactionTestCase):
    def test_backfill_preserves_and_seals_legacy_row(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        old = [('core', '0002_dominio_economico')]
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            legacy = apps.get_model('core', 'LogActividad').objects.create(
                accion='CONSULTAR', entidad_afectada='Usuario', entidad_id='legacy', detalle={'legacy': True})
            executor = MigrationExecutor(connection)
            executor.migrate(leaves)
            from core.models import LogActividad
            from core.services.audit_chain import verify
            row = LogActividad.objects.get(pk=legacy.pk)
            self.assertEqual(row.detalle, {'legacy': True})
            self.assertEqual(len(row.hash_actual), 64)
            self.assertEqual(len(row.firma_hmac), 64)
            self.assertTrue(verify()['ok'])
        finally:
            MigrationExecutor(connection).migrate(leaves)

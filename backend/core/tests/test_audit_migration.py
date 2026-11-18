from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor
from django.db import connections


class AuditMigrationTests(TransactionTestCase):
    def test_concurrent_appends_do_not_fork(self):
        from core.audit import audit
        from core.models import Usuario, AuditHead
        from core.services.audit_chain import verify
        AuditHead.objects.get_or_create(pk=1)
        def write(number):
            connections.close_all()
            try:
                audit(None, 'CONSULTAR', Usuario(pk='concurrent'), {'n': number})
            finally:
                connections.close_all()
        if connection.vendor == 'postgresql':
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(write, range(20)))
        else:
            # SQLite's coarse locking is not a multi-writer production target.
            from core.models import Usuario
            for number in range(20):
                audit(None, 'CONSULTAR', Usuario(pk='serial'), {'n': number})
        self.assertTrue(verify()['ok'])
        self.assertEqual(verify()['checked'], 20)

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

import json
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from core.models import Posicion, LogActividad
from core.services.crypto import decrypt
from . import test_portfolios as fixtures
from .helpers import APICase, country


class CorrectionPolicyTests(APICase):
    create_portfolio = fixtures.PortfolioTests.create_portfolio
    position = fixtures.PortfolioTests.position

    def setUp(self):
        super().setUp()
        self.pais = country()
        self.authenticate()
    def setup_position(self):
        portfolio = self.create_portfolio()
        base = f"/api/portafolios/{portfolio['id']}/"
        position = self.client.post(base+'posiciones/', self.position(1, notas='Nota privada')).data
        return base, position, base+f"posiciones/{position['id']}/eliminar/?motivo=ERROR_CREACION"

    def test_correction_preserves_encrypted_snapshot_and_updated_version(self):
        base, position, url = self.setup_position()
        self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"2"').status_code, 204)
        record = LogActividad.objects.filter(entidad_afectada='Posicion', accion='ELIMINAR').first()
        self.assertEqual(record.detalle['motivo'], 'ERROR_CREACION')
        self.assertEqual(record.detalle['version'], 3)
        self.assertNotIn('Nota privada', str(record.detalle))
        snapshot = json.loads(decrypt(record.detalle['snapshot_cifrado']))
        self.assertEqual(snapshot['monto_inversion_usd'], '1000.00')
        self.assertEqual(snapshot['notas'], 'Nota privada')
        self.assertEqual(snapshot['id'], position['id'])
        self.assertEqual(self.client.get(base).data['version'], 3)

    def test_expired_closed_unknown_and_missing_reason_are_rejected(self):
        base, position, url = self.setup_position()
        self.assertEqual(self.client.delete(url.split('?')[0], HTTP_IF_MATCH='"2"').status_code, 400)
        for values in [
            {'fecha_creacion': timezone.now()-timedelta(hours=24)},
            {'fecha_creacion': None},
            {'fecha_creacion': timezone.now(), 'fecha_salida': timezone.now().date()},
        ]:
            Posicion.objects.filter(pk=position['id']).update(**values)
            self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"2"').status_code, 400)
            self.assertEqual(self.client.get(base).data['version'], 2)
        self.assertTrue(Posicion.objects.filter(pk=position['id']).exists())

    def test_viewer_foreign_owner_and_wrong_parent_cannot_delete(self):
        base, position, url = self.setup_position()
        self.authenticate(self.viewer)
        self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"2"').status_code, 403)
        from core.models import Usuario
        other = Usuario.objects.create_user('another@test.com', rol='ANALISTA')
        self.authenticate(other)
        self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"2"').status_code, 403)
        own = self.create_portfolio('Otro portafolio')
        wrong = f"/api/portafolios/{own['id']}/posiciones/{position['id']}/eliminar/?motivo=DUPLICADO"
        self.assertEqual(self.client.delete(wrong, HTTP_IF_MATCH='"1"').status_code, 404)
        self.assertTrue(Posicion.objects.filter(pk=position['id']).exists())

    def test_archive_does_not_erase_positions_even_after_the_correction_window(self):
        base, position, _ = self.setup_position()
        response = self.client.delete(base+'?motivo=DESISTIMIENTO', HTTP_IF_MATCH='"2"')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Posicion.objects.filter(pk=position['id']).exists())
        log = LogActividad.objects.filter(entidad_afectada='Portafolio', accion='ELIMINAR').first()
        self.assertEqual(log.detalle['motivo'], 'DESISTIMIENTO')

    def test_encryption_failure_rolls_back_and_admin_has_the_same_time_limit(self):
        base, position, url = self.setup_position()
        with patch('core.services.portfolios.encrypt', side_effect=ValueError('encryption unavailable')):
            self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"2"').status_code, 500)
        self.assertTrue(Posicion.objects.filter(pk=position['id']).exists())
        self.assertEqual(self.client.get(base).data['version'], 2)
        self.authenticate(self.admin)
        Posicion.objects.filter(pk=position['id']).update(fecha_creacion=timezone.now()-timedelta(days=2))
        self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"2"').status_code, 400)

    def test_editing_or_supplying_creation_metadata_does_not_restart_the_window(self):
        base, position, url = self.setup_position()
        original = timezone.now()-timedelta(days=2)
        Posicion.objects.filter(pk=position['id']).update(fecha_creacion=original)
        payload = self.position(2, fecha_creacion=timezone.now().isoformat(), puede_eliminar=True)
        self.assertEqual(self.client.put(base+f"posiciones/{position['id']}/", payload).status_code, 200)
        self.assertEqual(Posicion.objects.get(pk=position['id']).fecha_creacion, original)
        self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"3"').status_code, 400)

    def test_failure_after_removing_the_row_restores_position_and_audit_chain(self):
        from core.services.audit_chain import verify
        base, position, url = self.setup_position()
        count = LogActividad.objects.count()
        with patch('core.services.portfolios.touch', side_effect=ValueError('write failed')):
            self.assertEqual(self.client.delete(url, HTTP_IF_MATCH='"2"').status_code, 500)
        self.assertTrue(Posicion.objects.filter(pk=position['id']).exists())
        self.assertEqual(LogActividad.objects.count(), count)
        self.assertTrue(verify()['ok'])
        self.assertEqual(self.client.get(base).data['version'], 2)


from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class CorrectionMigrationTests(TransactionTestCase):
    def test_existing_positions_do_not_receive_a_new_correction_window(self):
        from core.models import Usuario, Portafolio
        owner = Usuario.objects.create_user('migration-clock@test.com')
        portfolio = Portafolio.objects.create(usuario=owner, nombre='Reloj')
        position = Posicion.objects.create(portafolio=portfolio, pais=country(), tipo_activo='RENTA_FIJA',
            monto_inversion_usd='1000', fecha_entrada=timezone.now().date())
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([('core', '0009_maintenance_runs')])
        finally:
            MigrationExecutor(connection).migrate(leaves)
        self.assertIsNone(Posicion.objects.get(pk=position.pk).fecha_creacion)

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError

from core.models import Usuario, LogActividad
from .helpers import APICase


class MaintenanceTests(APICase):
    def test_daily_sync_runs_exchange_even_when_indicators_fail(self):
        with patch('core.services.tasks.sync_and_recalculate', side_effect=ValueError('provider failed')), \
             patch('core.services.tasks.exchange_and_recalculate', return_value={
                 'actualizados': 1, 'errores': [], 'riesgo': {'errores': []}}) as exchange:
            with self.assertRaises(CommandError):
                call_command('sync_diaria', stdout=StringIO(), stderr=StringIO())
        exchange.assert_called_once()

    def test_daily_sync_rejects_partial_errors_and_failed_recalculations(self):
        for report in [
            {'actualizados': 2, 'errores': [{'pais': 'CO'}], 'riesgo': {'errores': []}},
            {'actualizados': 0, 'errores': [], 'riesgo': {'errores': [{'pais': 'CO'}]}},
        ]:
            with self.subTest(report=report), \
                 patch('core.services.tasks.sync_and_recalculate', return_value=report), \
                 patch('core.services.tasks.exchange_and_recalculate', return_value={
                     'actualizados': 0, 'errores': [], 'riesgo': {'errores': []}}):
                with self.assertRaises(CommandError):
                    call_command('sync_diaria', stdout=StringIO(), stderr=StringIO())

    def test_unchanged_success_is_success_and_writes_report(self):
        report = {'actualizados': 0, 'errores': [], 'riesgo': {'errores': []}}
        output = StringIO()
        with patch('core.services.tasks.sync_and_recalculate', return_value=report), \
             patch('core.services.tasks.exchange_and_recalculate', return_value=report):
            call_command('sync_diaria', stdout=output)
        import json
        result = json.loads(output.getvalue())
        self.assertTrue(result['ok'])
        self.assertEqual(set(result['tareas']), {'indicadores', 'tipos_cambio'})

    def test_evaluation_setup_requires_explicit_demo_confirmation(self):
        with self.assertRaises(CommandError):
            call_command('prepare_evaluation_accounts', stdout=StringIO())
        self.assertFalse(Usuario.objects.filter(email='admin@datapulse.com').exists())

    def test_evaluation_accounts_have_required_access_without_django_superuser(self):
        demo = Usuario.objects.create_superuser('admin@datapulse.com', 'old-password', nombre_completo='Demo')
        operator_password = self.admin.password
        call_command('prepare_evaluation_accounts', confirm_demo=True, stdout=StringIO())
        for prefix, role in [('admin', 'ADMIN'), ('analista', 'ANALISTA'), ('viewer', 'VIEWER')]:
            user = Usuario.objects.get(email=f'{prefix}@datapulse.com')
            self.assertEqual(user.rol, role)
            self.assertTrue(user.check_password('DataPulse2026!'))
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            self.assertTrue(user.activo and user.is_active)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, operator_password)
        demo.refresh_from_db()
        password = demo.password
        audit_count = LogActividad.objects.count()
        call_command('prepare_evaluation_accounts', confirm_demo=True, stdout=StringIO())
        demo.refresh_from_db()
        self.assertEqual(demo.password, password)
        self.assertEqual(LogActividad.objects.count(), audit_count)

    def test_evaluation_setup_preserves_enrolled_mfa_and_rolls_back_every_account(self):
        demo = Usuario.objects.create_user('viewer@datapulse.com', 'existing-password', mfa_enabled=True)
        with self.assertRaises(CommandError):
            call_command('prepare_evaluation_accounts', confirm_demo=True, stdout=StringIO())
        demo.refresh_from_db()
        self.assertTrue(demo.check_password('existing-password'))
        self.assertFalse(Usuario.objects.filter(email='admin@datapulse.com').exists())

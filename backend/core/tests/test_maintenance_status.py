from io import StringIO
from unittest.mock import patch
from django.core.management import call_command, CommandError
from .helpers import APICase


class MaintenanceStatusTests(APICase):
    def test_coverage_does_not_count_manual_indicators_as_external(self):
        from django.utils import timezone
        from core.models import IndicadorEconomico
        from .helpers import country
        pais = country()
        year = timezone.now().year-1
        IndicadorEconomico.objects.create(pais=pais, tipo='PIB', anio=year, valor='100', unidad='USD', fuente='WORLD_BANK')
        IndicadorEconomico.objects.create(pais=pais, tipo='INFLACION', anio=year, valor='5', unidad='PORCENTAJE', fuente='MANUAL')
        with patch('core.services.tasks.sync_and_recalculate', return_value={'actualizados': 0, 'errores': []}):
            call_command('sync_diaria', task='indicadores', stdout=StringIO())
        self.authenticate(self.admin)
        row = self.client.get('/api/dashboard/mantenimiento/').data[0]['ultima_ejecucion']
        self.assertEqual(row['cobertura'][0]['externos'], 1)
        self.assertEqual(row['cobertura'][0]['no_verificados'], 1)
        self.assertEqual(row['cobertura'][0]['faltantes'], 28)

    def test_reports_last_attempt_and_preserves_last_success_without_exposing_errors(self):
        self.authenticate(self.admin)
        with patch('core.services.tasks.sync_and_recalculate', return_value={'actualizados': 3, 'errores': []}):
            call_command('sync_diaria', task='indicadores', stdout=StringIO())
        with patch('core.services.tasks.sync_and_recalculate', side_effect=RuntimeError('private credential')):
            with self.assertRaises(CommandError):
                call_command('sync_diaria', task='indicadores', stdout=StringIO(), stderr=StringIO())
        from core.models import MaintenanceRun
        from django.utils import timezone
        # Equal clock ticks must still resolve to the most recently inserted run.
        MaintenanceRun.objects.update(iniciado=timezone.now())
        response = self.client.get('/api/dashboard/mantenimiento/')
        self.assertEqual(response.status_code, 200)
        row = next(row for row in response.data if row['tarea'] == 'indicadores')
        self.assertEqual(row['ultima_ejecucion']['estado'], 'FALLIDA')
        self.assertEqual(row['ultimo_exito']['actualizados'], 3)
        self.assertNotIn('private credential', str(response.data))
        self.authenticate(self.viewer)
        self.assertEqual(self.client.get('/api/dashboard/mantenimiento/').status_code, 403)

    def test_partial_and_interrupted_runs_are_not_successes_and_metadata_is_validated(self):
        from datetime import timedelta
        from django.utils import timezone
        from core.models import MaintenanceRun
        self.authenticate(self.admin)
        with patch.dict('os.environ', {'GITHUB_SHA': 'invalid', 'GITHUB_RUN_ID': 'https://private.example'}), \
             patch('core.services.tasks.exchange_and_recalculate', return_value={'actualizados': 1, 'errores': [{'pais': 'CO', 'code': 'ConnectionError'}]}):
            with self.assertRaises(CommandError):
                call_command('sync_diaria', task='tipos_cambio', stdout=StringIO())
        run = MaintenanceRun.objects.get(tarea='tipos_cambio')
        self.assertEqual(run.estado, 'PARCIAL')
        self.assertEqual(run.commit, '')
        self.assertEqual(run.run_id, '')
        run.estado, run.iniciado = 'EJECUTANDO', timezone.now()-timedelta(minutes=36)
        run.save()
        row = self.client.get('/api/dashboard/mantenimiento/').data[1]
        self.assertIsNone(row['ultimo_exito'])
        self.assertEqual(row['ultima_ejecucion']['estado'], 'INTERRUMPIDA')
        self.assertIsNone(row['ultima_ejecucion']['ejecucion_url'])

    def test_countries_are_opt_in_and_failure_is_recorded(self):
        self.authenticate(self.admin)
        with patch('core.services.tasks.sync_countries', return_value={'actualizados': 0, 'errores': [
            {'pais': 'CO', 'operacion': 'PAIS', 'code': 'ValueError', 'mensaje': 'private credential'}]}):
            with self.assertRaises(CommandError):
                call_command('sync_diaria', task='paises', stdout=StringIO())
        response = self.client.get('/api/dashboard/mantenimiento/')
        self.assertEqual(response.status_code, 200)
        row = next(row for row in response.data if row['tarea'] == 'paises')
        self.assertIsNone(row['ultimo_exito'])
        self.assertEqual(row['ultima_ejecucion']['estado'], 'FALLIDA')
        self.assertEqual(row['ultima_ejecucion']['errores'][0]['code'], 'ValueError')
        self.assertNotIn('private credential', str(response.data))

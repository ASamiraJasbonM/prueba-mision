import importlib.util
from pathlib import Path
from subprocess import CompletedProcess
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet, InvalidToken


class BackupVerificationTests(unittest.TestCase):
    def module(self):
        path = Path(__file__).resolve().parents[1] / 'backup_verify.py'
        self.assertTrue(path.exists(), 'Debe existir una verificación reproducible del backup cifrado.')
        spec = importlib.util.spec_from_file_location('backup_verification', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_ciphertext_requires_the_correct_key_and_contains_restore_expectations(self):
        module = self.module()
        key = Fernet.generate_key()
        encrypted = module.seal_bundle(b'PGDMP-private-records', {'major': 16, 'tables': {'core_pais': 10}}, key)
        self.assertNotIn(b'private-records', encrypted)
        dump, manifest = module.open_bundle(encrypted, key)
        self.assertEqual(dump, b'PGDMP-private-records')
        self.assertEqual(manifest['tables'], {'core_pais': 10})
        with self.assertRaises(InvalidToken):
            module.open_bundle(encrypted, Fernet.generate_key())

    def test_production_connections_require_tls_and_local_exception_is_explicit(self):
        module = self.module()
        for value in ['sqlite:///db.sqlite3', 'postgresql://u:p@remote/db', 'postgresql://u:p@remote/db?sslmode=disable']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.database_env(value)
        self.assertEqual(module.database_env('postgresql://u:p@remote/db?sslmode=require')['PGSSLMODE'], 'require')
        self.assertEqual(module.database_env('postgresql://u:p@127.0.0.1/db', development=True)['PGSSLMODE'], 'disable')
        with self.assertRaises(ValueError):
            module.database_env('postgresql://u:p@remote/db', development=True)

    def test_restore_waits_for_the_final_tcp_listener(self):
        module = self.module()
        with (
            patch.object(module.secrets, 'token_hex', return_value='test'),
            patch.object(module, 'run', side_effect=[b'', b'true', b'127.0.0.1:54321', b'true', b'']),
            patch.object(module.time, 'sleep') as sleep,
            patch.object(module.subprocess, 'run', side_effect=[CompletedProcess([], 2), CompletedProcess([], 0)]) as probe,
        ):
            with module.isolated_database(16) as (name, url):
                self.assertEqual(name, 'datapulse-restore-test')
                self.assertTrue(url.endswith('@127.0.0.1:54321/restored'))

        self.assertEqual(probe.call_count, 2)
        probe.assert_called_with(
            ['docker', 'exec', 'datapulse-restore-test', 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'restored'],
            capture_output=True,
        )
        sleep.assert_called_once_with(1)

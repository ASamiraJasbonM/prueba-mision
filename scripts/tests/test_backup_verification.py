import importlib.util
from pathlib import Path
import unittest
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

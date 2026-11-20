import base64
import importlib.util
from pathlib import Path
import tempfile
import unittest


class LocalSetupTests(unittest.TestCase):
    def test_creates_independent_valid_keys_and_never_overwrites_existing_configuration(self):
        path = Path(__file__).resolve().parents[1] / 'setup_local.py'
        spec = importlib.util.spec_from_file_location('setup_local', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / '.env'
            self.assertTrue(module.initialize(target))
            original = target.read_bytes()
            values = dict(line.split('=', 1) for line in original.decode().splitlines()
                          if '=' in line and not line.startswith('#'))
            self.assertEqual(len(base64.urlsafe_b64decode(values['FIELD_ENCRYPTION_KEY'])), 32)
            self.assertEqual(len({values[key] for key in ['SECRET_KEY', 'AUDIT_HMAC_KEY', 'MFA_KEY']}), 3)
            self.assertNotIn(b'replace-with-generated', original)
            self.assertFalse(module.initialize(target))
            self.assertEqual(target.read_bytes(), original)

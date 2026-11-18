import os
import subprocess
import sys
from django.conf import settings
from django.test import SimpleTestCase


class SecurityStartupTests(SimpleTestCase):
    def test_production_requires_audit_hmac_key(self):
        environment = {**os.environ, 'DEBUG': 'False', 'AUDIT_HMAC_KEY': '',
                       'SECRET_KEY': 'test-only-dummy-secret-with-more-than-fifty-characters-for-checks'}
        result = subprocess.run([sys.executable, str(settings.BASE_DIR / 'manage.py'), 'check'],
            env=environment, capture_output=True, text=True, timeout=30, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('AUDIT_HMAC_KEY is required in production', result.stderr)

    def test_production_requires_field_encryption_key(self):
        environment = {**os.environ, 'DEBUG': 'False', 'AUDIT_HMAC_KEY': 'dummy-audit-key',
                       'FIELD_ENCRYPTION_KEY': '', 'MFA_KEY': 'dummy-mfa-key',
                       'SECRET_KEY': 'test-only-dummy-secret-with-more-than-fifty-characters-for-checks'}
        result = subprocess.run([sys.executable, str(settings.BASE_DIR / 'manage.py'), 'check'],
            env=environment, capture_output=True, text=True, timeout=30, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FIELD_ENCRYPTION_KEY and MFA_KEY are required in production', result.stderr)

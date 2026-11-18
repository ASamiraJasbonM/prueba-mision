import base64
import json
import os
from io import StringIO
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django_otp.oath import TOTP
from core.models import MFALoginChallenge
from core.services.crypto import encrypt, decrypt
from .helpers import APICase


@override_settings(CAPTCHA_ENFORCED=False)
class MFATests(APICase):
    def enroll(self):
        self.authenticate(self.admin)
        result = self.client.post('/api/auth/mfa/enroll/')
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data['qr'].startswith('data:image/png;base64,'))
        self.admin.refresh_from_db()
        secret = decrypt(self.admin.mfa_secret_enc)
        self.assertNotEqual(secret, self.admin.mfa_secret_enc)
        totp = TOTP(base64.b32decode(secret))
        totp.time = 1800000000
        with patch('core.services.mfa.time', return_value=1800000000):
            verified = self.client.post('/api/auth/mfa/verify/', {'code': f'{totp.token():06d}'})
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(len(verified.data['recovery_codes']), 10)
        return secret, verified.data['recovery_codes']

    def begin_login(self):
        self.client.force_authenticate(None)
        response = self.client.post('/api/auth/login/', {'email': self.admin.email, 'password': 'Strong-test-2026!'})
        self.assertTrue(response.data['mfa_required'])
        self.assertNotIn('access', response.data)
        return response.data['mfa_token']

    def test_admin_login_requires_mfa_and_returns_tokens_once(self):
        secret, _ = self.enroll()
        token = self.begin_login()
        totp = TOTP(base64.b32decode(secret))
        totp.time = 1800000030
        with patch('core.services.mfa.time', return_value=1800000030):
            result = self.client.post('/api/auth/mfa/verify-login/', {'mfa_token': token, 'code': f'{totp.token():06d}'})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(self.client.post('/api/auth/mfa/verify-login/', {'mfa_token': token, 'code': f'{totp.token():06d}'}).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {result.data['access']}")
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        self.assertTrue(MFALoginChallenge.objects.get().used)

    def test_recovery_code_single_use_and_no_totp_replay(self):
        secret, codes = self.enroll()
        token = self.begin_login()
        result = self.client.post('/api/auth/mfa/verify-login/', {'mfa_token': token, 'code': codes[0]})
        self.assertEqual(result.status_code, 200)
        second = self.begin_login()
        self.assertEqual(self.client.post('/api/auth/mfa/verify-login/', {'mfa_token': second, 'code': codes[0]}).status_code, 401)
        self.admin.refresh_from_db()
        self.assertEqual(len(json.loads(decrypt(self.admin.recovery_codes_enc))), 9)

    def test_disable_requires_current_totp_not_recovery_code(self):
        secret, codes = self.enroll()
        self.assertEqual(self.client.post('/api/auth/mfa/disable/', {'code': codes[0]}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/mfa/disable/', {'code': '000000'}).status_code, 401)
        totp = TOTP(base64.b32decode(secret))
        totp.time = 1800000030
        with patch('core.services.mfa.time', return_value=1800000030):
            self.assertEqual(self.client.post('/api/auth/mfa/disable/', {'code': f'{totp.token():06d}'}).status_code, 204)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.mfa_enabled)

    def test_mfa_throttles_sixth_attempt(self):
        for _ in range(5):
            self.assertEqual(self.client.post('/api/auth/mfa/verify-login/', {'mfa_token': 'invalid', 'code': '000000'}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/mfa/verify-login/', {'mfa_token': 'invalid', 'code': '000000'}).status_code, 429)

    def test_non_admin_cannot_enroll(self):
        self.authenticate(self.user)
        self.assertEqual(self.client.post('/api/auth/mfa/enroll/').status_code, 403)

    def test_enrollment_revokes_preexisting_access(self):
        self.client.force_authenticate(None)
        old = self.client.post('/api/auth/login/', {'email': self.admin.email, 'password': 'Strong-test-2026!'}).data
        self.enroll()
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {old['access']}")
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/auth/refresh/', {'refresh': old['refresh']}).status_code, 401)

    def test_field_encryption_roundtrip_and_rotation(self):
        original, replacement = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        value = encrypt('sensitive', original)
        self.assertEqual(decrypt(value, original), 'sensitive')
        self.admin.mfa_secret_enc = value
        self.admin.recovery_codes_enc = encrypt('["hash"]', original)
        self.admin.save()
        with patch.dict(os.environ, {'FIELD_ENCRYPTION_KEY_OLD': original, 'FIELD_ENCRYPTION_KEY_NEW': replacement}):
            call_command('rotar_field_key', stdout=StringIO())
        self.admin.refresh_from_db()
        self.assertEqual(decrypt(self.admin.mfa_secret_enc, replacement), 'sensitive')
        self.assertEqual(decrypt(self.admin.recovery_codes_enc, replacement), '["hash"]')

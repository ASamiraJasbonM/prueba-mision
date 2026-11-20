from unittest.mock import patch
from django.test import override_settings
from django.core.cache import cache
from captcha.models import CaptchaStore
from axes.models import AccessAttempt
from core.models import LogActividad, Usuario
from .helpers import APICase


@override_settings(CAPTCHA_ENFORCED=False)
class SecurityAuthTests(APICase):
    def login(self, password='bad', **headers):
        return self.client.post('/api/auth/login/', {'email': self.user.email, 'password': password}, **headers)

    def test_five_failures_then_lockout_audited(self):
        for _ in range(5):
            self.assertEqual(self.login().status_code, 401)
        result = self.login()
        self.assertEqual(result.status_code, 429)
        self.assertEqual(result.data['error']['code'], 'account_locked')
        self.assertEqual(result['Retry-After'], '900')
        self.assertEqual(LogActividad.objects.filter(accion='LOGIN_FALLIDO').count(), 5)
        self.assertEqual(LogActividad.objects.filter(accion='LOGIN_BLOQUEADO').count(), 1)
        self.assertNotIn('password', str(list(LogActividad.objects.values('detalle'))))

    def test_lockout_cannot_be_bypassed_by_forwarded_for(self):
        for _ in range(5):
            self.login()
        self.assertEqual(self.login(HTTP_X_FORWARDED_FOR='10.20.30.40').status_code, 429)
        self.assertEqual(self.login(REMOTE_ADDR='127.0.0.2').status_code, 401)

    def test_success_resets_axes_failures(self):
        self.login()
        self.assertEqual(self.login('Strong-test-2026!').status_code, 200)
        self.assertFalse(AccessAttempt.objects.filter(username=self.user.email).exists())

    def test_six_successful_logins_are_throttled(self):
        for _ in range(5):
            self.assertEqual(self.login('Strong-test-2026!').status_code, 200)
        self.assertEqual(self.login('Strong-test-2026!').status_code, 429)

    @override_settings(CAPTCHA_ENFORCED=True)
    def test_register_requires_captcha_and_challenge_is_single_use(self):
        payload = {'email': 'fresh@test.com', 'nombre_completo': 'Fresh', 'password': 'Strong-test-2026!'}
        denied = self.client.post('/api/auth/register/', payload)
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(denied.data['error']['code'], 'captcha_required')
        challenge = self.client.get('/api/auth/captcha/').data
        image = self.client.get(challenge['image_url'])
        self.assertEqual(image.status_code, 200)
        store = CaptchaStore.objects.get(hashkey=challenge['captcha_key'])
        payload.update(captcha_key=store.hashkey, captcha_answer=store.response)
        self.assertEqual(self.client.post('/api/auth/register/', payload).status_code, 201)
        payload['email'] = 'replay@test.com'
        self.assertEqual(self.client.post('/api/auth/register/', payload).status_code, 400)

    @override_settings(CAPTCHA_ENFORCED=True)
    def test_login_demands_captcha_after_three_failures(self):
        for _ in range(3):
            self.assertEqual(self.login().status_code, 401)
        result = self.login('Strong-test-2026!')
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data['error']['code'], 'captcha_required')

    def test_password_change_revokes_refresh_and_access(self):
        tokens = self.login('Strong-test-2026!').data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        changed = self.client.post('/api/auth/password-change/', {
            'current_password': 'Strong-test-2026!', 'new_password': 'Even-stronger-test-2026!'})
        self.assertEqual(changed.status_code, 204)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/auth/refresh/', {'refresh': tokens['refresh']}).status_code, 401)

    def test_password_minimum_twelve(self):
        result = self.client.post('/api/auth/register/', {
            'email': 'short@test.com', 'nombre_completo': 'Short', 'password': 'sH0rt-X!42'})
        self.assertEqual(result.status_code, 400)
        self.assertFalse(Usuario.objects.filter(email='short@test.com').exists())

    def test_sync_third_call_throttled(self):
        self.authenticate(self.admin)
        from core.models import SyncJob
        for _ in range(2):
            self.assertEqual(self.client.post('/api/paises/sync-indicadores/').status_code, 202)
        self.assertEqual(self.client.post('/api/paises/sync-indicadores/').status_code, 429)
        self.assertEqual(SyncJob.objects.count(), 1)

    def test_idempotency_isolated_by_user_endpoint_and_body(self):
        self.authenticate(self.admin)
        from core.models import SyncJob, IdempotentRequest
        ids = []
        for _ in range(2):
            result = self.client.post('/api/paises/sync-indicadores/', {'a': 1}, HTTP_IDEMPOTENCY_KEY='example')
            self.assertEqual(result.status_code, 202)
            ids.append(result.data['id'])
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(SyncJob.objects.count(), 1)
        self.assertEqual(IdempotentRequest.objects.count(), 1)
        self.assertEqual(LogActividad.objects.filter(accion='CREAR', entidad_afectada='SyncJob').count(), 1)
        cache.clear()
        conflict = self.client.post('/api/paises/sync-indicadores/', {'a': 2}, HTTP_IDEMPOTENCY_KEY='example')
        self.assertEqual(conflict.status_code, 409)

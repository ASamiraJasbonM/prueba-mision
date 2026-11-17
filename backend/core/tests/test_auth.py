from core.models import Usuario
from .helpers import APICase


class AuthTests(APICase):
    def test_register_and_reject_role_escalation(self):
        payload = {'email': 'NEW@test.com', 'password': 'Strong-test-2026!', 'nombre_completo': 'Nuevo'}
        response = self.client.post('/api/auth/register/', payload)
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        self.assertEqual(Usuario.objects.get(email='new@test.com').rol, 'ANALISTA')
        response = self.client.post('/api/auth/register/', {**payload, 'email': 'admin2@test.com', 'rol': 'ADMIN'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Usuario.objects.filter(email='admin2@test.com').exists())

    def test_login_refresh_me(self):
        response = self.client.post('/api/auth/login/', {'email': 'ANALISTA@test.com', 'password': 'Strong-test-2026!'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertEqual(self.client.post('/api/auth/refresh/', {'refresh': response.data['refresh']}).status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        self.assertEqual(self.client.get('/api/auth/me/').data['email'], self.user.email)

    def test_profile_cannot_change_role(self):
        self.authenticate()
        response = self.client.put('/api/auth/me/', {'email': self.user.email, 'nombre_completo': 'Cambio', 'rol': 'ADMIN'})
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.rol, 'ANALISTA')

    def test_inactive_user_token_is_rejected(self):
        login = self.client.post('/api/auth/login/', {'email': self.user.email, 'password': 'Strong-test-2026!'})
        self.assertEqual(login.status_code, 200)
        self.user.activo = False
        self.user.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login/', {'email': self.user.email, 'password': 'Strong-test-2026!'}).status_code, 401)

    def test_me_requires_auth_and_bad_password_is_uniform(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        response = self.client.post('/api/auth/login/', {'email': self.user.email, 'password': 'bad'})
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)

from django.contrib.auth import get_user_model
from django.test import TestCase


class UserTests(TestCase):
    def test_email_login_and_safe_defaults(self):
        user = get_user_model().objects.create_user(email='Test@Example.com', password='Strong-test-2026!')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.USERNAME_FIELD, 'email')
        self.assertEqual(user.rol, 'ANALISTA')
        self.assertTrue(user.check_password('Strong-test-2026!'))

    def test_superuser_flags(self):
        user = get_user_model().objects.create_superuser(email='admin@example.com', password='Strong-test-2026!')
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.rol, 'ADMIN')

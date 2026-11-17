from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase
from core.models import Usuario, Moneda, Pais


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class APICase(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = Usuario.objects.create_user('analista@test.com', 'Strong-test-2026!', nombre_completo='Analista')
        self.admin = Usuario.objects.create_user('admin@test.com', 'Strong-test-2026!', rol='ADMIN')
        self.viewer = Usuario.objects.create_user('viewer@test.com', 'Strong-test-2026!', rol='VIEWER')

    def authenticate(self, user=None):
        self.client.force_authenticate(user or self.user)


def country(code='CO', currency='COP'):
    moneda, _ = Moneda.objects.get_or_create(codigo=currency, defaults={'nombre': currency})
    return Pais.objects.create(codigo_iso=code, nombre=code, moneda=moneda, region='ANDINA', latitud='0', longitud='0', poblacion=1)

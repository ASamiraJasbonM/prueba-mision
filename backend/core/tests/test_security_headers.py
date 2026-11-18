from django.test import override_settings
from django.conf import settings
from .helpers import APICase


class SecurityHeadersTests(APICase):
    @override_settings(DEBUG=False, SECURE_HSTS_SECONDS=31536000)
    def test_headers_over_https(self):
        response = self.client.get('/api/health/', secure=True)
        self.assertIn('max-age=31536000', response['Strict-Transport-Security'])
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Permissions-Policy'], 'geolocation=(), camera=(), microphone=()')
        self.assertEqual(response['Cross-Origin-Opener-Policy'], 'same-origin')

    def test_no_store_even_for_auth_errors(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['Cache-Control'], 'no-store')

    @override_settings(API_DOCS_ENABLED=True)
    def test_docs_csp_has_local_scripts_without_unsafe_inline(self):
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("script-src 'self'", response['Content-Security-Policy'])
        self.assertNotIn('<script>', response.content.decode())

    @override_settings(API_DOCS_ENABLED=False)
    def test_docs_disabled_but_schema_available(self):
        self.assertEqual(self.client.get('/api/docs/').status_code, 404)
        self.assertEqual(self.client.get('/api/schema/').status_code, 200)

    def test_proxy_header_untrusted_by_default(self):
        self.assertIsNone(settings.SECURE_PROXY_SSL_HEADER)

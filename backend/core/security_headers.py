from django.conf import settings
from django.http import HttpResponseNotFound


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Disable interactive docs in production; JSON schema stays available.
        if not settings.API_DOCS_ENABLED and request.path.startswith('/api/docs/'):
            response = HttpResponseNotFound()
        else:
            response = self.get_response(request)
        response['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'
        if request.path.startswith('/api/auth/'):
            response['Cache-Control'] = 'no-store'
            response['Pragma'] = 'no-cache'
        return response

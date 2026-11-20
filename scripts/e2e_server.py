"""Local-only E2E fixture: production SPA + real Django + temporary demo DB."""
import base64
from io import StringIO
import json
import mimetypes
import os
from pathlib import Path
import secrets
import signal
import sys
from threading import Event, Thread
from tempfile import TemporaryDirectory
from socketserver import ThreadingMixIn
from urllib.parse import unquote
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server
from wsgiref.util import FileWrapper


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend/dist/datapulse/browser'


def main():
    if not (FRONTEND / 'index.html').is_file():
        raise SystemExit('Build the SPA first: cd frontend && npm run build:e2e')
    with TemporaryDirectory(prefix='datapulse-e2e-') as directory:
        os.environ.update({
            'DJANGO_SETTINGS_MODULE': 'config.settings',
            'SECRET_KEY': secrets.token_urlsafe(64),
            'AUDIT_HMAC_KEY': secrets.token_urlsafe(64),
            'MFA_KEY': secrets.token_urlsafe(64),
            'FIELD_ENCRYPTION_KEY': base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            'DATABASE_URL': 'sqlite:///' + (Path(directory) / 'e2e.sqlite3').as_posix(),
            'DEBUG': 'False', 'SECURE_SSL_REDIRECT': 'False', 'TRUST_PROXY_SSL_HEADER': 'False',
            'CACHE_SHARED': 'False',
            'CAPTCHA_ENFORCED': 'False', 'API_DOCS_ENABLED': 'False',
            'ALLOWED_HOSTS': '127.0.0.1,localhost', 'CORS_ALLOWED_ORIGINS': '', 'JWT_SIGNING_KEY': '',
            'WORLD_BANK_URL': 'http://127.0.0.1:18120/provider/world-bank',
        })
        sys.path.insert(0, str(ROOT / 'backend'))
        import django
        django.setup()
        from django.conf import settings
        settings.DATABASES['default'].setdefault('OPTIONS', {})['transaction_mode'] = 'IMMEDIATE'
        # High limits only in this disposable fixture; production limits and
        # CAPTCHA/MFA behavior have their own unit/integration regression tests.
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
            key: '10000/min' for key in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']}
        from django.core.management import call_command
        from django.core.wsgi import get_wsgi_application
        from django.db import connections
        call_command('migrate', interactive=False, stdout=StringIO())
        call_command('seed_data', stdout=StringIO())
        connections.close_all()
        django_app = get_wsgi_application()
        csp = json.loads((ROOT / 'frontend/docker/csp-policy.json').read_text())
        provider_unavailable = Event()

        def application(environ, start_response):
            path = environ.get('PATH_INFO', '/')
            if path == '/fixture/provider-mode' and environ.get('REQUEST_METHOD') == 'POST':
                if environ.get('QUERY_STRING') == 'unavailable':
                    provider_unavailable.set()
                else:
                    provider_unavailable.clear()
                start_response('204 No Content', [])
                return [b'']
            if path == '/fixture/expired-session':
                from datetime import timedelta
                from rest_framework_simplejwt.tokens import RefreshToken
                from core.models import Usuario
                refresh = RefreshToken.for_user(Usuario.objects.get(email='analista@datapulse.com'))
                access = refresh.access_token
                access.set_exp(lifetime=timedelta(seconds=-1))
                refresh.set_exp(lifetime=timedelta(seconds=-1))
                body = json.dumps({'access': str(access), 'refresh': str(refresh)}).encode()
                start_response('200 OK', [('Content-Type', 'application/json'), ('Cache-Control', 'no-store')])
                return [body]
            if path.startswith('/provider/world-bank/country/'):
                # Only the upstream provider is controlled; SPA/API/queue/worker are real.
                parts = path.split('/')
                code, indicator = parts[-3], parts[-1]
                if provider_unavailable.is_set() or indicator == 'GC.DOD.TOTL.GD.ZS':
                    payload = {'error': 'Controlled provider failure'}
                else:
                    from datetime import datetime, timezone
                    year = datetime.now(timezone.utc).year-1
                    payload = [{'pages': 1}, [{'country': {'id': country}, 'date': str(annual), 'value': 4}
                        for country in code.split(';') for annual in range(year-4, year+1)]]
                body = json.dumps(payload).encode()
                start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
                return [body]
            if path.startswith(('/api/', '/admin/')):
                return django_app(environ, start_response)
            target = (FRONTEND / unquote(path).lstrip('/')).resolve()
            if not target.is_relative_to(FRONTEND.resolve()):
                start_response('404 Not Found', [('Content-Type', 'text/plain')])
                return [b'Not found']
            if not target.is_file():
                if target.suffix or path.startswith('/assets/'):
                    start_response('404 Not Found', [('Content-Type', 'text/plain')])
                    return [b'Not found']
                target = FRONTEND / 'index.html'
            content_type = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
            start_response('200 OK', [('Content-Type', content_type),
                                      ('Content-Length', str(target.stat().st_size)),
                                      ('Content-Security-Policy', csp),
                                      ('Cache-Control', 'no-store')])
            return FileWrapper(target.open('rb'))

        class Server(ThreadingMixIn, WSGIServer):
            daemon_threads = True
            request_queue_size = 128

        class QuietHandler(WSGIRequestHandler):
            def log_message(self, format, *args):
                return  # No URLs, headers or tokens in browser test artifacts.

        def stop(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, stop)
        worker_stop = Event()
        def work():
            from core.services.sync_jobs import process_next_job
            from core.models import SyncJob
            from django.db import close_old_connections, DatabaseError
            while not worker_stop.wait(.2):
                close_old_connections()
                try:
                    if SyncJob.objects.filter(estado__in=['PENDIENTE', 'EJECUTANDO']).exists():
                        process_next_job()
                except DatabaseError:
                    close_old_connections()
            connections.close_all()
        worker = Thread(target=work, daemon=True)
        worker.start()
        try:
            with make_server('127.0.0.1', 18120, application, Server, QuietHandler) as server:
                server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            worker_stop.set()
            worker.join(timeout=10)
            connections.close_all()


if __name__ == '__main__':
    main()

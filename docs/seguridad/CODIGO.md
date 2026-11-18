# Código completo de archivos clave de seguridad

Snapshot 2026-11-18 UTC. La fuente editable está en el árbol del repositorio.

## pyproject.toml

```toml
[project]
name = "datapulse-backend"
version = "1.0.0"
description = "Backend Django y DRF de DataPulse Latam"
requires-python = ">=3.12,<3.13"
dependencies = [
    "Django==5.2.19",
    "djangorestframework==3.18.2",
    "djangorestframework-simplejwt==5.5.1",
    "django-cors-headers==4.9.0",
    "django-environ==0.14.0",
    "django-filter==26.2",
    "drf-spectacular==0.30.0",
    "psycopg[binary]==3.3.9",
    "reportlab==5.1.0",
    "requests==2.34.2",
    "PyYAML==6.0.3",
    "pillow==13.0.0",
    "gunicorn==27.0.1",
    "django-axes>=9.0.0",
    "django-simple-captcha>=0.8.0",
    "django-csp>=4.0",
    "drf-spectacular-sidecar>=2026.10.1",
    "django-otp>=1.7.5",
    "qrcode>=8.2",
    "cryptography>=50.0.2",
]

[dependency-groups]
# Test runner remains Django/unittest; scanners are development/CI only.
dev = [
    "bandit>=1.9.4",
    "pip-audit>=2.10.1",
]

[tool.uv]
package = false
default-groups = ["dev"]
compile-bytecode = true
# Preserve the previously verified transitive versions without making them direct.
constraint-dependencies = [
    "asgiref==3.13.0",
    "attrs==26.1.0",
    "certifi==2026.10.23",
    "charset-normalizer==3.5.2",
    "idna==3.20",
    "inflection==0.5.1",
    "jsonschema==4.26.0",
    "jsonschema-specifications==2025.9.1",
    "psycopg-binary==3.3.9",
    "PyJWT==2.15.1",
    "referencing==0.37.0",
    "rpds-py==2026.9.1",
    "sqlparse==0.6.1",
    "typing-extensions==4.16.0",
    "tzdata==2026.6",
    "uritemplate==4.2.0",
    "urllib3==2.8.0",
]
```

## Dockerfile

```
FROM ghcr.io/astral-sh/uv:0.13.9 AS uv

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/backend" \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy
WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --create-home appuser \
    && mkdir -p /app/docs /app/data \
    && chown -R appuser:appuser /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=uv /uv /usr/local/bin/uv
COPY --chown=appuser:appuser pyproject.toml uv.lock .python-version ./
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser scripts/check_numeric_policy.py ./scripts/check_numeric_policy.py

USER appuser
EXPOSE 8000

# Gunicorn trusts secure-scheme headers from loopback; do not broaden that trust.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; h=os.environ.get('ALLOWED_HOSTS','localhost').split(',')[0].strip().lstrip('.'); h='localhost' if h=='*' else h; r=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/health/', headers={'Host':h,'X-Forwarded-Proto':'https'}), timeout=3); assert r.status == 200"

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
```

## .env.example

```
SECRET_KEY=replace-with-a-random-secret-at-least-50-characters
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
DATABASE_URL=sqlite:///db.sqlite3
# PostgreSQL: postgresql://datapulse:YOUR_PASSWORD@localhost:5432/datapulse
POSTGRES_PASSWORD=replace-local-demo-password
CORS_ALLOWED_ORIGINS=http://localhost:4200
JWT_ACCESS_MINUTES=15
JWT_REFRESH_DAYS=1
JWT_SIGNING_KEY=
SECURE_SSL_REDIRECT=False
WORLD_BANK_URL=https://api.worldbank.org/v2
EXCHANGE_RATE_URL=https://open.er-api.com/v6/latest/USD
REST_COUNTRIES_URL=https://api.restcountries.com/countries/v5
REST_COUNTRIES_API_KEY=
EXTERNAL_API_TIMEOUT=10

# Independiente de SECRET_KEY; generar aleatoriamente para producción, nunca registrar.
AUDIT_HMAC_KEY=
# Fernet de 32 bytes codificados base64; MFA_KEY aleatoria independiente.
FIELD_ENCRYPTION_KEY=
MFA_KEY=
BACKUP_GPG_KEY=
# Activado por defecto si DEBUG=False. El cliente debe soportar el reto.
CAPTCHA_ENFORCED=False
API_DOCS_ENABLED=True
# Solo un proxy confiable que limpie y reescriba X-Forwarded-Proto.
TRUST_PROXY_SSL_HEADER=False
```

## .bandit

```
[bandit]
# Existing tests intentionally exercise weak hashes and error paths. Migrations
# contain historical schema SQL and are reviewed with migration/PG tests.
exclude = backend/core/tests,backend/core/migrations
# No global skips: B101 remains active in production code.
```

## .gitattributes

```
*.sh text eol=lf
```

## .github/dependabot.yml

```yaml
version: 2
updates:
  # Native uv ecosystem updates pyproject.toml and uv.lock together.
  - package-ecosystem: uv
    directory: /
    schedule:
      interval: weekly
    groups:
      python-dependencies:
        patterns: ['*']
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: docker
    directories: [/, /frontend]
    schedule:
      interval: weekly
```

## .github/workflows/backend-ci.yml

```yaml
name: Backend CI

on:
  push:
    branches: [main, feat/backend-datapulse]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: backend-ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

# Dummy values only. No .env, personal API keys, or deployment credentials in CI.
# DEBUG stays false; redirect is explicitly off for HTTP test-client requests.
env:
  SECRET_KEY: ci-only-dummy-key-not-for-deployment-security-checks-2026-at-least-fifty
  AUDIT_HMAC_KEY: ci-only-audit-key-never-for-production
  FIELD_ENCRYPTION_KEY: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
  MFA_KEY: ci-only-mfa-key-never-for-production
  CAPTCHA_ENFORCED: "False"
  API_DOCS_ENABLED: "True"
  DEBUG: "False"
  SECURE_SSL_REDIRECT: "False"
  ALLOWED_HOSTS: "*"
  CORS_ALLOWED_ORIGINS: http://localhost:4200
  JWT_ACCESS_MINUTES: "15"
  JWT_REFRESH_DAYS: "1"
  JWT_SIGNING_KEY: ""
  REST_COUNTRIES_API_KEY: ""

defaults:
  run:
    shell: bash

jobs:
  lint-and-check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      DATABASE_URL: sqlite:////tmp/datapulse-checks.sqlite3
    steps:
      - uses: actions/checkout@v4
      # Keep 3.12: pyproject.toml and the production image use this interpreter.
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v7
        with:
          version: "0.13.9"
          enable-cache: true
          cache-dependency-glob: uv.lock
      - run: uv lock --check
      - run: uv sync --frozen
      - run: uv run --frozen python backend/manage.py check
      - name: Production deployment checks
        env:
          SECURE_SSL_REDIRECT: "True"
          API_DOCS_ENABLED: "False"
          CAPTCHA_ENFORCED: "True"
        run: uv run --frozen python backend/manage.py check --deploy --fail-level WARNING
      - name: Audit the locked production dependency graph
        run: |
          uv export --frozen --no-dev --no-hashes --output-file /tmp/req.audit.txt
          uv run --frozen pip-audit -r /tmp/req.audit.txt --strict --no-deps --disable-pip
      - run: uv run --frozen bandit -r backend -ll -x backend/core/migrations,backend/core/tests
      - run: uv run --frozen python backend/manage.py makemigrations --check --dry-run
      - run: uv run --frozen python scripts/check_numeric_policy.py
      - run: uv run --frozen python backend/manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml

  test-sqlite:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    env:
      DATABASE_URL: sqlite:////tmp/datapulse-tests.sqlite3
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v7
        with:
          version: "0.13.9"
          enable-cache: true
          cache-dependency-glob: uv.lock
      - run: uv lock --check
      - run: uv sync --frozen
      # Seed is exercised only by isolated tests, never as a CI setup command.
      - run: uv run --frozen python backend/manage.py test -v 2

  test-postgresql:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: datapulse
          POSTGRES_USER: datapulse
          POSTGRES_PASSWORD: datapulse
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U datapulse -d datapulse"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      DATABASE_URL: postgresql://datapulse:datapulse@127.0.0.1:5432/datapulse
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v7
        with:
          version: "0.13.9"
          enable-cache: true
          cache-dependency-glob: uv.lock
      - run: uv lock --check
      - run: uv sync --frozen
      - run: uv run --frozen python backend/manage.py migrate --noinput
      - run: uv run --frozen python backend/manage.py verificar_auditoria
      - name: Run the complete suite and reject skips
        run: |
          uv run --frozen python backend/manage.py test -v 2 2>&1 | tee /tmp/postgresql-tests.log
          if grep -Eq '(\.\.\. skipped |^OK \(skipped=)' /tmp/postgresql-tests.log; then
            echo '::error::PostgreSQL must execute the entire suite without skips.'
            exit 1
          fi
          grep -Eq 'test_two_writers_same_version_only_one_succeeds .*\.\.\. ok' /tmp/postgresql-tests.log
          grep -Eq 'test_large_decimal_is_preserved .*\.\.\. ok' /tmp/postgresql-tests.log

  docker-build:
    needs: [lint-and-check]
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          load: true
          tags: datapulse-backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Verify non-root user and Django import
        env:
          IMAGE: datapulse-backend:${{ github.sha }}
        run: |
          test "$(docker run --rm "$IMAGE" whoami)" = appuser
          docker run --rm -e SECRET_KEY -e AUDIT_HMAC_KEY -e FIELD_ENCRYPTION_KEY -e MFA_KEY -e DEBUG -e SECURE_SSL_REDIRECT -e ALLOWED_HOSTS \
            -e DATABASE_URL=sqlite:////tmp/datapulse-image.sqlite3 \
            "$IMAGE" uv run --frozen --no-sync --no-dev python backend/manage.py check
      - name: Export the exact image for security scanning
        run: docker save datapulse-backend:${{ github.sha }} -o /tmp/backend-image.tar
      - uses: actions/upload-artifact@v4
        with:
          name: backend-image
          path: /tmp/backend-image.tar
          retention-days: 1

  security-scan:
    needs: docker-build
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: backend-image
          path: /tmp/backend-image
      - name: Scan the built image without publishing it
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25
        with:
          version: v0.76.2
          input: /tmp/backend-image/backend-image.tar
          scanners: vuln
          timeout: 15m
          severity: HIGH,CRITICAL
          exit-code: '1'
          ignore-unfixed: true
          format: json
          output: trivy-backend.json
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: backend-security-report
          path: trivy-backend.json
          if-no-files-found: ignore
          retention-days: 7
```

## backend/config/settings.py

```python
from datetime import timedelta
from pathlib import Path
import base64
import hashlib

import environ
from django.core.exceptions import ImproperlyConfigured
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR.parent / '.env')
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'django_filters', 'drf_spectacular', 'corsheaders', 'core',
    'axes', 'captcha', 'rest_framework_simplejwt.token_blacklist', 'drf_spectacular_sidecar',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.observability.RequestLogMiddleware',
    'csp.middleware.CSPMiddleware', 'core.security_headers.SecurityHeadersMiddleware',
    'axes.middleware.AxesMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')}
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    database_path = Path(DATABASES['default']['NAME'])
    if not database_path.is_absolute() and str(database_path) != ':memory:':
        DATABASES['default']['NAME'] = BASE_DIR / database_path
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': f'django.contrib.auth.password_validation.{name}',
     **({'OPTIONS': {'min_length': 12}} if name == 'MinimumLengthValidator' else {})}
    for name in ['UserAttributeSimilarityValidator', 'MinimumLengthValidator',
                 'CommonPasswordValidator', 'NumericPasswordValidator']
]
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.Usuario'
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_HEADERS = [*default_headers, 'if-match', 'idempotency-key']
CORS_EXPOSE_HEADERS = ['ETag']
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'
SECURE_HSTS_SECONDS = 0 if DEBUG else 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'
# Enable only behind a proxy that strips incoming X-Forwarded-Proto and sets it
# from its TLS connection. Never trust this header on a public backend port.
if env.bool('TRUST_PROXY_SSL_HEADER', default=False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
AUDIT_HMAC_KEY = env('AUDIT_HMAC_KEY', default='')
if not AUDIT_HMAC_KEY and not DEBUG:
    raise ImproperlyConfigured('AUDIT_HMAC_KEY is required in production.')
if not AUDIT_HMAC_KEY:
    # Local development only: no new persistent secret and no hard-coded key.
    AUDIT_HMAC_KEY = SECRET_KEY
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='')
MFA_KEY = env('MFA_KEY', default='')
if not DEBUG and (not FIELD_ENCRYPTION_KEY or not MFA_KEY):
    raise ImproperlyConfigured('FIELD_ENCRYPTION_KEY and MFA_KEY are required in production.')
if not FIELD_ENCRYPTION_KEY:
    FIELD_ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()).decode()
if not MFA_KEY:
    MFA_KEY = SECRET_KEY
try:
    from cryptography.fernet import Fernet
    Fernet(FIELD_ENCRYPTION_KEY.encode())
except (ValueError, TypeError) as exc:
    raise ImproperlyConfigured('FIELD_ENCRYPTION_KEY must be a valid Fernet key.') from exc
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend', 'django.contrib.auth.backends.ModelBackend']
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_FORM_FIELD = 'email'
AXES_CLIENT_IP_CALLABLE = 'core.security_auth.client_ip'
AXES_VERBOSE = False
AXES_LOCKOUT_CALLABLE = 'core.security_auth.lockout_response'
# DEBUG demo keeps the current Angular registration usable. Production requires
# the challenge; the API client must support it before enabling production.
CAPTCHA_ENFORCED = env.bool('CAPTCHA_ENFORCED', default=not DEBUG)
API_DOCS_ENABLED = env.bool('API_DOCS_ENABLED', default=DEBUG)
CONTENT_SECURITY_POLICY = {'DIRECTIVES': {
    'default-src': ["'self'"], 'img-src': ["'self'", 'data:'],
    'connect-src': ["'self'"], 'script-src': ["'self'"],
    'style-src': ["'self'", "'unsafe-inline'"], 'object-src': ["'none'"],
    'base-uri': ["'self'"], 'frame-ancestors': ["'none'"],
}}
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': ['core.authentication.ActiveJWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'core.api.Pagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend',
                               'rest_framework.filters.SearchFilter', 'rest_framework.filters.OrderingFilter'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle', 'core.security_auth.ActionThrottle'],
    'DEFAULT_THROTTLE_RATES': {'user': '100/min', 'anon': '20/min', 'login': '5/min',
        'register': '3/min', 'sync': '2/hour', 'recalcular': '2/hour', 'export_pdf': '10/min', 'mfa_verify': '5/min'},
    'NUM_PROXIES': 0,
    'EXCEPTION_HANDLER': 'core.api.exception_handler',
    'COERCE_DECIMAL_TO_STRING': True,
    'DATETIME_FORMAT': 'iso-8601',
}
SPECTACULAR_SETTINGS = {'TITLE': 'DataPulse Latam API', 'VERSION': '1.0.0',
    'SWAGGER_UI_DIST': 'SIDECAR', 'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'POSTPROCESSING_HOOKS': ['drf_spectacular.hooks.postprocess_schema_enums', 'core.security_schema.security_responses']}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_MINUTES', default=15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_DAYS', default=1)),
    'SIGNING_KEY': env('JWT_SIGNING_KEY', default='') or SECRET_KEY,
    'USER_AUTHENTICATION_RULE': 'core.authentication.active_user',
    'CHECK_REVOKE_TOKEN': True,
}
WORLD_BANK_URL = env('WORLD_BANK_URL', default='https://api.worldbank.org/v2')
EXCHANGE_RATE_URL = env('EXCHANGE_RATE_URL', default='https://open.er-api.com/v6/latest/USD')
REST_COUNTRIES_URL = env('REST_COUNTRIES_URL', default='https://api.restcountries.com/countries/v5')
REST_COUNTRIES_API_KEY = env('REST_COUNTRIES_API_KEY', default='')
EXTERNAL_API_TIMEOUT = env.int('EXTERNAL_API_TIMEOUT', default=10)
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'json': {'()': 'core.observability.JsonFormatter'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'json'}},
    'loggers': {'datapulse': {'handlers': ['console'], 'level': 'INFO', 'propagate': False}},
}
```

## backend/config/urls.py

```python
from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView
from core.health import health
from core.auth_api import RegisterView, LoginView, MeView, PasswordChangeView
from core.captcha_api import CaptchaView
from core.mfa_api import MFAEnrollView, MFAVerifyView, MFADisableView, MFALoginView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from django.urls import include
from core.data_api import PaisViewSet
from core.risk_api import RiesgoViewSet, AlertaViewSet
from core.portfolio_api import PortafolioViewSet
from core.dashboard_api import DashboardViewSet
from core.audit_api import AuditListView

router = DefaultRouter()
router.register('paises', PaisViewSet)
router.register('riesgo', RiesgoViewSet, basename='riesgo')
router.register('alertas', AlertaViewSet, basename='alerta')
router.register('portafolios', PortafolioViewSet, basename='portafolio')
router.register('dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('api/auditoria/', AuditListView.as_view()),
    path('api/', include(router.urls)),
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/auth/me/', MeView.as_view()),
    path('api/auth/password-change/', PasswordChangeView.as_view()),
    path('api/auth/captcha/', CaptchaView.as_view()),
    path('api/auth/mfa/enroll/', MFAEnrollView.as_view()),
    path('api/auth/mfa/verify/', MFAVerifyView.as_view()),
    path('api/auth/mfa/disable/', MFADisableView.as_view()),
    path('api/auth/mfa/verify-login/', MFALoginView.as_view()),
    path('api/auth/captcha-image/', include('captcha.urls')),
    path('api/health/', health),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerSplitView.as_view(url_name='schema')),
]
```

## backend/core/admin.py

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario
from .models import (Moneda, Pais, IndicadorEconomico, TipoCambio, Portafolio,
                     Posicion, IndiceRiesgo, Alerta, LecturaAlerta, LogActividad)

for model in [Moneda, Pais, IndicadorEconomico, TipoCambio, Portafolio,
              Posicion, IndiceRiesgo, Alerta, LecturaAlerta]:
    admin.site.register(model)


@admin.register(LogActividad)
class AuditAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in LogActividad._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ['email']
    list_display = ['email', 'nombre_completo', 'rol', 'activo', 'is_staff']
    search_fields = ['email', 'nombre_completo']
    fieldsets = (
        (None, {'fields': ('email', 'password', 'nombre_completo', 'rol', 'activo')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = ((None, {'fields': ('email', 'nombre_completo', 'password1', 'password2', 'rol')}),)
```

## backend/core/models.py

```python
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from decimal import Decimal


class ActivoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class ActivoModel(models.Model):
    activo = models.BooleanField(default=True)
    objects = ActivoManager()
    todos = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = 'todos'


class Moneda(models.Model):
    codigo = models.CharField(max_length=3, primary_key=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.codigo


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('El email es obligatorio.')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('rol', 'ADMIN')
        if not extra['is_staff'] or not extra['is_superuser'] or extra['rol'] != 'ADMIN':
            raise ValueError('Un superusuario requiere permisos ADMIN.')
        return self.create_user(email, password, **extra)


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        ANALISTA = 'ANALISTA', 'Analista'
        VIEWER = 'VIEWER', 'Consulta'

    username = None
    email = models.EmailField(unique=True)
    nombre_completo = models.CharField(max_length=200)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.ANALISTA)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre_completo']
    objects = UsuarioManager()
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret_enc = models.TextField(blank=True)
    recovery_codes_enc = models.TextField(blank=True)
    mfa_last_t = models.BigIntegerField(default=-1)
    mfa_epoch = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='usuario_email_ci_unique')]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Pais(ActivoModel):
    class Region(models.TextChoices):
        ANDINA = 'ANDINA', 'Andina'
        CONO_SUR = 'CONO_SUR', 'Cono sur'
        CENTROAMERICA = 'CENTROAMERICA', 'Centroamérica'
        CARIBE = 'CARIBE', 'Caribe'

    codigo_iso = models.CharField(max_length=2, primary_key=True)
    nombre = models.CharField(max_length=150, db_index=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='paises')
    region = models.CharField(max_length=15, choices=Region.choices, db_index=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    poblacion = models.PositiveBigIntegerField(default=0)
    bandera_url = models.URLField(blank=True)

    @property
    def moneda_codigo(self):
        return self.moneda_id

    @property
    def moneda_nombre(self):
        return self.moneda.nombre

    def __str__(self):
        return self.nombre


class IndicadorEconomico(models.Model):
    class Tipo(models.TextChoices):
        PIB = 'PIB', 'PIB'
        INFLACION = 'INFLACION', 'Inflación'
        DESEMPLEO = 'DESEMPLEO', 'Desempleo'
        BALANZA_COMERCIAL = 'BALANZA_COMERCIAL', 'Balanza comercial'
        DEUDA_PIB = 'DEUDA_PIB', 'Deuda/PIB'
        PIB_PERCAPITA = 'PIB_PERCAPITA', 'PIB per cápita'

    class Unidad(models.TextChoices):
        PORCENTAJE = 'PORCENTAJE', 'Porcentaje'
        USD = 'USD', 'USD'
        USD_MILES_MILLONES = 'USD_MILES_MILLONES', 'Miles de millones USD'

    class Fuente(models.TextChoices):
        WORLD_BANK = 'WORLD_BANK', 'World Bank'
        MANUAL = 'MANUAL', 'Manual'

    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='indicadores')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=28, decimal_places=6)
    unidad = models.CharField(max_length=20, choices=Unidad.choices)
    anio = models.PositiveSmallIntegerField()
    fuente = models.CharField(max_length=12, choices=Fuente.choices, default=Fuente.MANUAL)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['pais', 'tipo', 'anio'], name='indicador_natural_unique')]
        indexes = [models.Index(fields=['pais', 'tipo', 'anio'], name='indicador_pais_tipo_anio')]
        ordering = ['pais_id', 'tipo', '-anio']


class TipoCambio(models.Model):
    moneda_origen = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='tasas')
    moneda_destino = models.CharField(max_length=3, default='USD')
    tasa = models.DecimalField(max_digits=24, decimal_places=12, validators=[MinValueValidator(Decimal('0.000000000001'))])
    fecha = models.DateField()
    variacion_porcentual = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fuente = models.CharField(max_length=100, default='EXCHANGE_RATE_API')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['moneda_origen', 'moneda_destino', 'fecha'], name='cambio_natural_unique'),
            models.CheckConstraint(condition=models.Q(tasa__gt=0), name='cambio_tasa_positiva'),
        ]
        indexes = [models.Index(fields=['moneda_origen', 'moneda_destino', 'fecha'], name='cambio_moneda_fecha')]
        ordering = ['-fecha', 'pk']


class Portafolio(ActivoModel):
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(3)])
    descripcion = models.CharField(max_length=500, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='portafolios')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_modificacion = models.DateTimeField(default=timezone.now)
    es_publico = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'nombre'], name='portafolio_usuario_nombre_unique')]
        indexes = [models.Index(fields=['usuario', 'activo'], name='portafolio_usuario_activo')]
        ordering = ['-fecha_creacion', 'pk']


class Posicion(models.Model):
    class TipoActivo(models.TextChoices):
        RENTA_FIJA = 'RENTA_FIJA', 'Renta fija'
        RENTA_VARIABLE = 'RENTA_VARIABLE', 'Renta variable'
        COMMODITIES = 'COMMODITIES', 'Commodities'
        MONEDA = 'MONEDA', 'Moneda'

    portafolio = models.ForeignKey(Portafolio, on_delete=models.PROTECT, related_name='posiciones')
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='posiciones')
    tipo_activo = models.CharField(max_length=15, choices=TipoActivo.choices)
    monto_inversion_usd = models.DecimalField(max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('1000')), MaxValueValidator(Decimal('10000000'))])
    fecha_entrada = models.DateField()
    fecha_salida = models.DateField(null=True, blank=True)
    notas = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(fecha_salida__isnull=True) | models.Q(fecha_salida__gt=models.F('fecha_entrada')), name='posicion_salida_posterior'),
            models.CheckConstraint(condition=models.Q(monto_inversion_usd__gte=1000, monto_inversion_usd__lte=10000000), name='posicion_monto_limites'),
        ]
        indexes = [models.Index(fields=['portafolio', 'fecha_salida'], name='posicion_portafolio_salida')]
        ordering = ['-fecha_entrada', 'pk']

    def clean(self):
        super().clean()
        if self.fecha_salida and self.fecha_entrada and self.fecha_salida <= self.fecha_entrada:
            raise ValidationError({'fecha_salida': 'La salida debe ser posterior a la entrada.'})
        if self.fecha_entrada and self.fecha_entrada > timezone.now().date():
            raise ValidationError({'fecha_entrada': 'La entrada no puede ser futura.'})


class IndiceRiesgo(models.Model):
    class Nivel(models.TextChoices):
        BAJO = 'BAJO', 'Bajo'
        MODERADO = 'MODERADO', 'Moderado'
        ALTO = 'ALTO', 'Alto'
        CRITICO = 'CRITICO', 'Crítico'

    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='riesgos')
    fecha_calculo = models.DateTimeField(default=timezone.now)
    score_economico = models.DecimalField(max_digits=5, decimal_places=2)
    score_cambiario = models.DecimalField(max_digits=5, decimal_places=2)
    score_estabilidad = models.DecimalField(max_digits=5, decimal_places=2)
    indice_compuesto = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_riesgo = models.CharField(max_length=10, choices=Nivel.choices)
    detalle_calculo = models.JSONField(default=dict)
    clave_calculo = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(**{f'{f}__gte': 0, f'{f}__lte': 100}), name=f'{f}_rango')
                       for f in ['indice_compuesto', 'score_economico', 'score_cambiario', 'score_estabilidad']]
        indexes = [models.Index(fields=['pais', '-fecha_calculo'], name='riesgo_pais_fecha')]
        ordering = ['-fecha_calculo', '-pk']

    def clean(self):
        super().clean()
        for field in ['indice_compuesto', 'score_economico', 'score_cambiario', 'score_estabilidad']:
            value = getattr(self, field)
            if value is not None and not Decimal('0') <= Decimal(str(value)) <= Decimal('100'):
                raise ValidationError({field: 'El score debe estar entre 0 y 100.'})


class Alerta(models.Model):
    class Tipo(models.TextChoices):
        RIESGO = 'RIESGO', 'Riesgo'
        TIPO_CAMBIO = 'TIPO_CAMBIO', 'Tipo de cambio'
        INDICADOR = 'INDICADOR', 'Indicador'

    class Severidad(models.TextChoices):
        INFO = 'INFO', 'Información'
        WARNING = 'WARNING', 'Advertencia'
        CRITICAL = 'CRITICAL', 'Crítica'

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='alertas', null=True, blank=True)
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='alertas')
    tipo_alerta = models.CharField(max_length=12, choices=Tipo.choices)
    severidad = models.CharField(max_length=8, choices=Severidad.choices)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    clave_evento = models.CharField(max_length=200, unique=True, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['usuario', 'leida'], name='alerta_usuario_leida')]
        ordering = ['-fecha_creacion', '-pk']


class LecturaAlerta(models.Model):
    alerta = models.ForeignKey(Alerta, on_delete=models.CASCADE, related_name='lecturas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='lecturas_alertas')
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['alerta', 'usuario'], name='lectura_alerta_usuario_unique')]


class LogActividad(models.Model):
    class Accion(models.TextChoices):
        CREAR = 'CREAR', 'Crear'
        EDITAR = 'EDITAR', 'Editar'
        ELIMINAR = 'ELIMINAR', 'Eliminar'
        CONSULTAR = 'CONSULTAR', 'Consultar'
        LOGIN = 'LOGIN', 'Login'
        EXPORT = 'EXPORT', 'Exportar'
        LOGIN_FALLIDO = 'LOGIN_FALLIDO', 'Login fallido'
        LOGIN_BLOQUEADO = 'LOGIN_BLOQUEADO', 'Login bloqueado'
        PASSWORD_CHANGE = 'PASSWORD_CHANGE', 'Cambio de contraseña'
        MFA_ENROLL = 'MFA_ENROLL', 'Enrolar MFA'
        MFA_VERIFY_OK = 'MFA_VERIFY_OK', 'Verificación MFA correcta'
        MFA_VERIFY_FAIL = 'MFA_VERIFY_FAIL', 'Verificación MFA fallida'
        MFA_DISABLE = 'MFA_DISABLE', 'Deshabilitar MFA'
        CORRECCION = 'CORRECCION', 'Corrección de auditoría'

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='actividades', null=True, blank=True)
    accion = models.CharField(max_length=32, choices=Accion.choices)
    entidad_afectada = models.CharField(max_length=100)
    entidad_id = models.CharField(max_length=100)
    detalle = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    hash_anterior = models.CharField(max_length=64, null=True, blank=True)
    hash_actual = models.CharField(max_length=64, unique=True)
    firma_hmac = models.CharField(max_length=64)

    class Meta:
        ordering = ['-fecha', '-pk']


class AuditHead(models.Model):
    """Singleton used to serialize appends, including an initially empty chain."""
    hash_actual = models.CharField(max_length=64, default='', blank=True)


class IdempotentRequest(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    path = models.CharField(max_length=100)
    key = models.CharField(max_length=128)
    body_hash = models.CharField(max_length=64)
    response = models.JSONField()
    expires = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'path', 'key'], name='idempotency_user_path_key')]


class MFALoginChallenge(models.Model):
    digest = models.CharField(max_length=64, primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)
```

## backend/core/audit.py

```python
from .services.audit_chain import registrar
from .observability import request_ip


def audit(user, action, obj, details=None, ip=None):
    return registrar(usuario=user if user and user.is_authenticated else None,
        accion=action, entidad_afectada=obj.__class__.__name__, entidad_id=str(obj.pk),
        detalle=details or {}, ip_address=ip or request_ip.get())


log_actividad = audit
```

## backend/core/auth_api.py

```python
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from rest_framework import generics, serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenObtainSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from core.audit import audit
from core.models import Usuario
from core.security_auth import check_captcha
from core.services.mfa import challenge


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'nombre_completo', 'rol', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'rol', 'activo', 'fecha_creacion']

    def validate(self, attrs):
        blocked = {'rol', 'activo', 'is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions'} & set(self.initial_data)
        if blocked:
            import logging
            from core.observability import request_ip
            logging.getLogger('datapulse').warning('privilege_escalation_attempt', extra={
                'usuario_id': self.instance.pk if self.instance else None, 'ip': request_ip.get(),
                'path': '/api/auth/me/' if self.instance else '/api/auth/register/'})
            raise serializers.ValidationError({key: 'Este campo no puede modificarse.' for key in blocked})
        return attrs

    def validate_email(self, value):
        value = value.strip().lower()
        query = Usuario.objects.filter(email__iexact=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError('Ya existe un usuario con este email.')
        return value


class RegisterSerializer(ProfileSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    captcha_key = serializers.CharField(write_only=True, required=False)
    captcha_answer = serializers.CharField(write_only=True, required=False)

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + ['password', 'captcha_key', 'captcha_answer']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        check_captcha(attrs)
        attrs.pop('captcha_key', None)
        attrs.pop('captcha_answer', None)
        validate_password(attrs['password'], Usuario(email=attrs.get('email', ''), nombre_completo=attrs.get('nombre_completo', '')))
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = Usuario.objects.create_user(**validated_data)
        audit(user, 'CREAR', user)
        return user


class RegisterView(generics.CreateAPIView):
    throttle_scope = 'register'
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    http_method_names = ['get', 'put', 'head', 'options']

    def get_object(self):
        return self.request.user

    @transaction.atomic
    def perform_update(self, serializer):
        user = serializer.save()
        audit(user, 'EDITAR', user)


class LoginSerializer(TokenObtainPairSerializer):
    captcha_key = serializers.CharField(write_only=True, required=False)
    captcha_answer = serializers.CharField(write_only=True, required=False)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['mfa_epoch'] = user.mfa_epoch
        return token

    def validate(self, attrs):
        attrs['email'] = attrs['email'].strip().lower()
        try:
            TokenObtainSerializer.validate(self, attrs)
        except AuthenticationFailed:
            self.context['request']._request._login_failed_this_request = True
            audit(None, 'LOGIN_FALLIDO', Usuario(pk=''), {'email': attrs['email']})
            raise
        user_logged_in.send(sender=Usuario, request=self.context['request'], user=self.user)
        audit(self.user, 'LOGIN', self.user)
        if self.user.rol == 'ADMIN' and self.user.mfa_enabled:
            return challenge(self.user)
        refresh = self.get_token(self.user)
        return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class LoginTokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class MFAPendingSerializer(serializers.Serializer):
    mfa_required = serializers.BooleanField()
    mfa_token = serializers.CharField()


@extend_schema(responses=PolymorphicProxySerializer(component_name='LoginResponse',
    serializers=[LoginTokensSerializer, MFAPendingSerializer], resource_type_field_name=None))
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_scope = 'login'


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer

    @extend_schema(responses={204: None})
    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = Usuario.objects.select_for_update().get(pk=request.user.pk)
        if not user.check_password(serializer.validated_data['current_password']):
            raise AuthenticationFailed()
        validate_password(serializer.validated_data['new_password'], user)
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        audit(user, 'PASSWORD_CHANGE', user)
        return Response(status=204)
```

## backend/core/authentication.py

```python
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ActiveJWTScheme(OpenApiAuthenticationExtension):
    target_class = 'core.authentication.ActiveJWTAuthentication'
    name = 'jwtAuth'

    def get_security_definition(self, auto_schema):
        return {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}


def active_user(user):
    return user is not None and user.is_active and user.activo


class ActiveJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not active_user(user):
            raise AuthenticationFailed('El usuario está inactivo.')
        if validated_token.get('mfa_epoch', 0) != user.mfa_epoch or (user.mfa_enabled and validated_token.get('mfa') is not True):
            raise AuthenticationFailed('La sesión requiere autenticación actualizada.')
        return user
```

## backend/core/captcha_api.py

```python
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema


class CaptchaSerializer(serializers.Serializer):
    captcha_key = serializers.CharField()
    image_url = serializers.CharField()


class CaptchaView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CaptchaSerializer

    @extend_schema(responses=CaptchaSerializer)
    def get(self, request):
        CaptchaStore.remove_expired()
        key = CaptchaStore.generate_key()
        return Response({'captcha_key': key, 'image_url': captcha_image_url(key)})
```

## backend/core/idempotency.py

```python
import hashlib
import json
from datetime import timedelta
from functools import wraps
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from core.api import Conflict
from core.models import Usuario, IdempotentRequest


def idempotent(function):
    @wraps(function)
    def wrapped(view, request, *args, **kwargs):
        key = request.headers.get('Idempotency-Key')
        if key is None:
            return function(view, request, *args, **kwargs)
        if not key or len(key) > 128 or not key.isascii() or not key.isprintable():
            raise ValidationError({'Idempotency-Key': 'Debe contener entre 1 y 128 caracteres ASCII visibles.'})
        digest = hashlib.sha256(json.dumps(request.data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with transaction.atomic():
            # Shared database, safe across Gunicorn processes. No process-local cache.
            Usuario.objects.select_for_update().get(pk=request.user.pk)
            lookup = {'usuario': request.user, 'path': request.path, 'key': key}
            existing = IdempotentRequest.objects.filter(**lookup, expires__gt=timezone.now()).first()
            if existing:
                if existing.body_hash != digest:
                    raise Conflict('Idempotency-Key ya fue usada con otro cuerpo.')
                return Response(existing.response)
            result = function(view, request, *args, **kwargs)
            if result.status_code == 200:
                IdempotentRequest.objects.update_or_create(**lookup, defaults={
                    'body_hash': digest, 'response': result.data, 'expires': timezone.now() + timedelta(minutes=5)})
            return result
    return wrapped
```

## backend/core/mfa_api.py

```python
import base64
import io
import json
import secrets
import hashlib
from urllib.parse import quote, urlencode
import qrcode
from django.db import transaction
from rest_framework import generics, serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from drf_spectacular.utils import extend_schema
from core.permissions import EsAdmin
from core.models import Usuario
from core.audit import audit
from core.services.crypto import encrypt
from core.services.mfa import verify_totp, verify_login


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=128, trim_whitespace=False)


class LoginCodeSerializer(CodeSerializer):
    mfa_token = serializers.CharField(max_length=2048, trim_whitespace=False)


class EnrollmentSerializer(serializers.Serializer):
    otpauth_url = serializers.CharField()
    qr = serializers.CharField()


class RecoverySerializer(serializers.Serializer):
    recovery_codes = serializers.ListField(child=serializers.CharField())


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class MFAEnrollView(generics.GenericAPIView):
    permission_classes = [EsAdmin]
    throttle_scope = 'mfa_verify'
    serializer_class = EnrollmentSerializer

    @extend_schema(request=None, responses=EnrollmentSerializer)
    @transaction.atomic
    def post(self, request):
        user = Usuario.objects.select_for_update().get(pk=request.user.pk)
        if user.mfa_enabled:
            raise ValidationError('MFA ya está habilitado. Desactívalo con el factor actual antes de reenrolar.')
        secret = base64.b32encode(secrets.token_bytes(20)).decode()
        user.mfa_secret_enc, user.mfa_last_t = encrypt(secret), -1
        user.save(update_fields=['mfa_secret_enc', 'mfa_last_t'])
        uri = f"otpauth://totp/{quote('DataPulse:' + user.email, safe='')}?{urlencode({'secret': secret, 'issuer': 'DataPulse', 'digits': 6, 'period': 30})}"
        buffer = io.BytesIO()
        qrcode.make(uri).save(buffer, format='PNG')
        audit(user, 'MFA_ENROLL', user)
        return Response({'otpauth_url': uri, 'qr': 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()})


class MFAVerifyView(generics.GenericAPIView):
    permission_classes = [EsAdmin]
    throttle_scope = 'mfa_verify'
    serializer_class = CodeSerializer

    @extend_schema(responses=RecoverySerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failed = False
        with transaction.atomic():
            user = Usuario.objects.select_for_update().get(pk=request.user.pk)
            if user.mfa_enabled:
                raise ValidationError('MFA ya está habilitado.')
            if not verify_totp(user, serializer.validated_data['code']):
                audit(user, 'MFA_VERIFY_FAIL', user)
                failed = True
            else:
                codes = [secrets.token_hex(16) for _ in range(10)]
                user.recovery_codes_enc = encrypt(json.dumps([hashlib.sha256(code.encode()).hexdigest() for code in codes]))
                user.mfa_enabled = True
                user.mfa_epoch += 1
                user.save(update_fields=['mfa_enabled', 'recovery_codes_enc', 'mfa_epoch'])
                # Sessions issued before enrollment must not bypass the new factor.
                for token in OutstandingToken.objects.filter(user=user):
                    BlacklistedToken.objects.get_or_create(token=token)
                audit(user, 'MFA_VERIFY_OK', user)
        if failed:
            raise AuthenticationFailed()
        return Response({'recovery_codes': codes})


class MFADisableView(generics.GenericAPIView):
    permission_classes = [EsAdmin]
    throttle_scope = 'mfa_verify'
    serializer_class = CodeSerializer

    @extend_schema(responses={204: None})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failed = False
        with transaction.atomic():
            user = Usuario.objects.select_for_update().get(pk=request.user.pk)
            if not user.mfa_enabled or not verify_totp(user, serializer.validated_data['code']):
                audit(user, 'MFA_VERIFY_FAIL', user)
                failed = True
            else:
                user.mfa_enabled, user.mfa_secret_enc, user.recovery_codes_enc = False, '', ''
                user.mfa_epoch += 1
                user.save(update_fields=['mfa_enabled', 'mfa_secret_enc', 'recovery_codes_enc', 'mfa_epoch'])
                audit(user, 'MFA_DISABLE', user)
        if failed:
            raise AuthenticationFailed()
        return Response(status=204)


class MFALoginView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'mfa_verify'
    serializer_class = LoginCodeSerializer

    def get_authenticate_header(self, request):
        return 'Bearer'

    @extend_schema(responses=TokenResponseSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(verify_login(**{'token': serializer.validated_data['mfa_token'], 'code': serializer.validated_data['code']}))
```

## backend/core/observability.py

```python
import ipaddress
import json
import logging
from contextvars import ContextVar
from time import perf_counter_ns
from django.utils import timezone
from django.http import JsonResponse

request_ip = ContextVar('request_ip', default=None)
logger = logging.getLogger('datapulse')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        result = {'timestamp': timezone.now().isoformat(), 'level': record.levelname, 'event': record.getMessage()}
        for key in ['metodo', 'path', 'usuario_id', 'ip', 'duracion_ms', 'status', 'pais', 'operacion', 'error_code', 'actualizados', 'errores', 'ok', 'broken_id', 'checked', 'cause']:
            if hasattr(record, key):
                result[key] = getattr(record, key)
        return json.dumps(result, ensure_ascii=False)


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = perf_counter_ns()
        try:
            ip = str(ipaddress.ip_address(request.META.get('REMOTE_ADDR', '')))
        except ValueError:
            ip = None
        token = request_ip.set(ip)
        response = None
        try:
            response = self.get_response(request)
            if request.path.startswith('/api/') and response.status_code == 404 and 'application/json' not in response.get('Content-Type', ''):
                original = response
                response = JsonResponse({'error': {'code': 'not_found', 'message': 'No se encontró el recurso.', 'details': {}}}, status=404)
                for name, value in original.items():
                    if name.lower() not in {'content-type', 'content-length'}:
                        response[name] = value
            return response
        finally:
            user = getattr(request, 'user', None)
            logger.info('request', extra={'metodo': request.method, 'path': request.path,
                'usuario_id': user.pk if user and user.is_authenticated else None,
                'ip': ip, 'duracion_ms': (perf_counter_ns()-started)//1000000,
                'status': response.status_code if response else 500})
            request_ip.reset(token)
```

## backend/core/security_auth.py

```python
import ipaddress
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.utils import timezone
from axes.handlers.proxy import AxesProxyHandler
from axes.models import AccessAttempt
from captcha.fields import CaptchaField
from rest_framework.exceptions import APIException, Throttled
from rest_framework.throttling import ScopedRateThrottle
from core.audit import audit


def client_ip(request):
    # X-Forwarded-For is untrusted; all throttles and Axes share this boundary.
    try:
        return str(ipaddress.ip_address(request.META.get('REMOTE_ADDR', '')))
    except ValueError:
        return None


class AccountLocked(Throttled):
    default_code = 'account_locked'


class CaptchaRequired(APIException):
    status_code = 400
    default_code = 'captcha_required'
    default_detail = 'Completa un CAPTCHA válido.'


def check_captcha(data):
    if not settings.CAPTCHA_ENFORCED:
        return
    key, answer = data.get('captcha_key'), data.get('captcha_answer')
    if not isinstance(key, str) or not isinstance(answer, str):
        raise CaptchaRequired()
    try:
        CaptchaField().clean([key, answer])
    except DjangoValidationError as exc:
        raise CaptchaRequired() from exc


def login_preflight(request, email):
    if not AxesProxyHandler.is_allowed(request, {'email': email}):
        audit(None, 'LOGIN_BLOQUEADO', type('Login', (), {'pk': ''})(), {'email': email}, ip=client_ip(request))
        raise AccountLocked(wait=15 * 60)
    recent = AccessAttempt.objects.filter(ip_address=client_ip(request),
        attempt_time__gte=timezone.now() - timedelta(minutes=10)).aggregate(n=Sum('failures_since_start'))['n'] or 0
    if recent >= 3:
        check_captcha(request.data)


class ActionThrottle(ScopedRateThrottle):
    def allow_request(self, request, view):
        scopes = {'sync_indicadores': 'sync', 'calcular': 'recalcular', 'export_pdf': 'export_pdf'}
        # Viewsets choose their action before throttles execute.
        action_scope = scopes.get(getattr(view, 'action', None))
        if action_scope:
            view.throttle_scope = action_scope
        if getattr(view, 'throttle_scope', None) == 'login':
            # Lockout has precedence over rate throttling so the sixth failed
            # login is audited and returns account_locked even in the same minute.
            email = request.data.get('email')
            if isinstance(email, str):
                login_preflight(request, email.strip().lower()[:254])
        return super().allow_request(request, view)


def lockout_response(request, credentials=None, *args, **kwargs):
    from django.http import JsonResponse
    failed = getattr(request, '_login_failed_this_request', False)
    response = JsonResponse({'error': {'code': 'authentication_failed' if failed else 'account_locked',
        'message': 'Autenticación requerida o token inválido.' if failed else 'Demasiadas solicitudes. Intenta más tarde.',
        'details': {}}}, status=401 if failed else 429)
    if not failed:
        response['Retry-After'] = '900'
    return response
```

## backend/core/security_headers.py

```python
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
```

## backend/core/security_schema.py

```python
def security_responses(result, generator, request, public):
    error = {'description': 'Error uniforme. 429: throttled o account_locked; 400: captcha_required o validation_error.',
             'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorResponse'}}}}
    result.setdefault('components', {}).setdefault('schemas', {})['ErrorResponse'] = {
        'type': 'object', 'properties': {'error': {'type': 'object', 'properties': {
            'code': {'type': 'string'}, 'message': {'type': 'string'}, 'details': {}}}}}
    for path, methods in result.get('paths', {}).items():
        for method, operation in methods.items():
            if method not in {'get', 'post', 'put', 'delete', 'patch'}:
                continue
            operation.setdefault('responses', {}).setdefault('429', {**error, 'headers': {
                'Retry-After': {'schema': {'type': 'integer'}, 'description': 'Segundos de espera.'}}})
            if path.startswith('/api/auth/') and method == 'post':
                operation['responses'].setdefault('400', error)
                operation['responses'].setdefault('401', error)
            if path in {'/api/paises/sync-indicadores/', '/api/riesgo/calcular/'}:
                operation.setdefault('parameters', []).append({'in': 'header', 'name': 'Idempotency-Key',
                    'required': False, 'schema': {'type': 'string', 'maxLength': 128},
                    'description': 'Por usuario y endpoint; mismo cuerpo durante 5 minutos. Otro cuerpo: 409.'})
    return result
```

## backend/core/services/audit_chain.py

```python
import hashlib
import hmac
import json
from datetime import timezone as datetime_timezone
from django.conf import settings
from django.db import transaction
from django.db.models import F
from core.models import AuditHead, LogActividad


def seal(row, previous):
    # Versioned canonical representation; preserve this format across upgrades.
    fields = {'v': 1, 'id': row.pk, 'usuario_id': row.usuario_id, 'accion': row.accion,
              'entidad_afectada': row.entidad_afectada, 'entidad_id': row.entidad_id,
              'detalle': row.detalle, 'ip_address': row.ip_address,
              'fecha': row.fecha.astimezone(datetime_timezone.utc).isoformat()}
    payload = json.dumps(fields, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    digest = hashlib.sha256(((previous or '') + payload).encode()).hexdigest()
    signature = hmac.new(settings.AUDIT_HMAC_KEY.encode(), digest.encode(), hashlib.sha256).hexdigest()
    return digest, signature


@transaction.atomic
def registrar(**fields):
    # SQLite obtains a write lock before reading the tail. PostgreSQL locks the
    # singleton row until the caller's outermost transaction commits.
    _, created = AuditHead.objects.get_or_create(pk=1)
    if created and LogActividad.objects.exists():
        raise RuntimeError('Missing audit head for an existing chain.')
    AuditHead.objects.filter(pk=1).update(hash_actual=F('hash_actual'))
    head = AuditHead.objects.select_for_update().get(pk=1)
    row = LogActividad(**fields)
    # Allocate a monotonically increasing ID while holding the chain lock.
    last = LogActividad.objects.order_by('-pk').first()
    row.pk = last.pk + 1 if last else 1
    row.hash_anterior = head.hash_actual or None
    row.hash_actual, row.firma_hmac = seal(row, row.hash_anterior)
    row.save(force_insert=True)
    head.hash_actual = row.hash_actual
    head.save(update_fields=['hash_actual'])
    return row


@transaction.atomic
def verify():
    # Hold the same lock as appenders so an ordinary concurrent append cannot
    # produce a false tail-mismatch incident during periodic verification.
    head = AuditHead.objects.select_for_update().filter(pk=1).first()
    if head is None:
        return {'event': 'audit_verification', 'ok': False, 'broken_id': None, 'checked': 0, 'cause': 'missing_head'}
    previous, checked = None, 0
    for row in LogActividad.objects.order_by('pk').iterator():
        digest, signature = seal(row, previous)
        cause = ('previous_hash' if row.hash_anterior != previous else
                 'hash' if not hmac.compare_digest(row.hash_actual, digest) else
                 'hmac' if not hmac.compare_digest(row.firma_hmac, signature) else None)
        if cause:
            return {'event': 'audit_verification', 'ok': False, 'broken_id': row.pk, 'checked': checked, 'cause': cause}
        previous, checked = row.hash_actual, checked + 1
    ok = hmac.compare_digest(head.hash_actual, previous or '')
    return {'event': 'audit_verification', 'ok': ok, 'broken_id': None, 'checked': checked,
            'cause': None if ok else 'tail'}
```

## backend/core/services/crypto.py

```python
from cryptography.fernet import Fernet
from django.conf import settings


def encrypt(value, key=None):
    return Fernet((key or settings.FIELD_ENCRYPTION_KEY).encode()).encrypt(value.encode()).decode()


def decrypt(value, key=None):
    return Fernet((key or settings.FIELD_ENCRYPTION_KEY).encode()).decrypt(value.encode()).decode()
```

## backend/core/services/mfa.py

```python
import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from time import time
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django_otp.oath import TOTP
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import MFALoginChallenge, Usuario
from core.services.crypto import encrypt, decrypt
from core.audit import audit


def challenge(user):
    nonce = secrets.token_urlsafe(32)
    token = signing.dumps({'uid': user.pk, 'nonce': nonce, 'epoch': user.mfa_epoch, 'pwd': hashlib.sha256(user.password.encode()).hexdigest()},
                          key=settings.MFA_KEY, salt='datapulse-mfa')
    MFALoginChallenge.objects.create(digest=hashlib.sha256(token.encode()).hexdigest(), usuario=user,
        expires=timezone.now() + timedelta(minutes=5))
    return {'mfa_required': True, 'mfa_token': token}


def verify_totp(user, code):
    if not user.mfa_secret_enc or not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return False
    raw = base64.b32decode(decrypt(user.mfa_secret_enc))
    totp = TOTP(raw, step=30, digits=6)
    totp.time = time()
    if not totp.verify(int(code), tolerance=1, min_t=user.mfa_last_t + 1):
        return False
    user.mfa_last_t = totp.t()
    user.save(update_fields=['mfa_last_t'])
    return True


def verify_factor(user, code):
    if verify_totp(user, code):
        return True
    if not user.recovery_codes_enc or not isinstance(code, str):
        return False
    hashes = json.loads(decrypt(user.recovery_codes_enc))
    candidate = hashlib.sha256(code.encode()).hexdigest()
    for index, stored in enumerate(hashes):
        if hmac.compare_digest(candidate, stored):
            hashes.pop(index)
            user.recovery_codes_enc = encrypt(json.dumps(hashes))
            user.save(update_fields=['recovery_codes_enc'])
            return True
    return False


def verify_login(token, code):
    try:
        payload = signing.loads(token, key=settings.MFA_KEY, salt='datapulse-mfa', max_age=300)
    except (signing.BadSignature, TypeError, ValueError) as exc:
        raise AuthenticationFailed() from exc
    failed = False
    with transaction.atomic():
        user = Usuario.objects.select_for_update().filter(pk=payload['uid'], rol='ADMIN', activo=True, is_active=True, mfa_enabled=True).first()
        record = MFALoginChallenge.objects.select_for_update().filter(digest=hashlib.sha256(token.encode()).hexdigest(),
            usuario=user, used=False, expires__gt=timezone.now()).first()
        if not user or not record or payload['epoch'] != user.mfa_epoch or not hmac.compare_digest(payload['pwd'], hashlib.sha256(user.password.encode()).hexdigest()):
            raise AuthenticationFailed()
        if not verify_factor(user, code):
            audit(user, 'MFA_VERIFY_FAIL', user)
            failed = True
        else:
            record.used = True
            record.save(update_fields=['used'])
            refresh = RefreshToken.for_user(user)
            refresh['mfa'] = True
            refresh['mfa_epoch'] = user.mfa_epoch
            audit(user, 'MFA_VERIFY_OK', user)
            result = {'access': str(refresh.access_token), 'refresh': str(refresh)}
    # Keep the failure audit committed; never return tokens on failure.
    if failed:
        raise AuthenticationFailed()
    return result
```

## backend/core/management/commands/verificar_auditoria.py

```python
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from core.services.audit_chain import verify


class Command(BaseCommand):
    help = 'Valida hashes, HMAC y cabecera de la cadena de auditoría.'

    def handle(self, **options):
        result = verify()
        self.stdout.write(json.dumps(result))
        logging.getLogger('datapulse').info('audit_verification', extra=result)
        if not result['ok']:
            raise CommandError(f"Cadena inválida: id={result['broken_id']}, causa={result['cause']}")
```

## backend/core/management/commands/rotar_field_key.py

```python
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Usuario
from core.services.crypto import encrypt, decrypt


class Command(BaseCommand):
    help = 'Recifra MFA usando FIELD_ENCRYPTION_KEY_OLD y FIELD_ENCRYPTION_KEY_NEW (entorno).'

    @transaction.atomic
    def handle(self, **options):
        old = os.environ.get('FIELD_ENCRYPTION_KEY_OLD')
        new = os.environ.get('FIELD_ENCRYPTION_KEY_NEW')
        if not old or not new:
            raise CommandError('Se requieren las claves OLD y NEW en el entorno.')
        count = 0
        for user in Usuario.objects.select_for_update().order_by('pk'):
            changed = []
            for field in ['mfa_secret_enc', 'recovery_codes_enc']:
                value = getattr(user, field)
                if value:
                    setattr(user, field, encrypt(decrypt(value, old), new))
                    changed.append(field)
            if changed:
                user.save(update_fields=changed)
                count += 1
        self.stdout.write(f'Usuarios recifrados: {count}. Actualizar FIELD_ENCRYPTION_KEY antes de reiniciar.')
```

## docker-compose.siem.yaml

```yaml
# Local observability only. Alloy replaces EOL Promtail; no Docker socket mount.
services:
  loki:
    image: grafana/loki:3.6.20
    profiles: [siem]
    command: [-config.file=/etc/loki/local-config.yaml]
    volumes:
      - ./ops/loki.yaml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    ports: ['127.0.0.1:13100:3100']
    security_opt: [no-new-privileges:true]
  alloy:
    image: grafana/alloy:v1.21.3
    profiles: [siem]
    command: [run, --storage.path=/var/lib/alloy, /etc/alloy/config.alloy]
    volumes:
      - ./ops/alloy/config.alloy:/etc/alloy/config.alloy:ro
      - ./tmp/siem:/var/log/datapulse:ro
      - alloy_data:/var/lib/alloy
    depends_on: [loki]
    security_opt: [no-new-privileges:true]
  grafana:
    image: grafana/grafana:13.3.1
    profiles: [siem]
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:?Define GRAFANA_ADMIN_PASSWORD locally}
      GF_USERS_ALLOW_SIGN_UP: 'false'
      GF_ANALYTICS_REPORTING_ENABLED: 'false'
      GF_ANALYTICS_CHECK_FOR_UPDATES: 'false'
    ports: ['127.0.0.1:13000:3000']
    volumes:
      - grafana_data:/var/lib/grafana
      - ./ops/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro
      - ./ops/grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./ops/grafana/rules.yaml:/etc/grafana/provisioning/alerting/rules.yaml:ro
      - ./ops/grafana/dashboards:/var/lib/grafana/dashboards:ro
    depends_on: [loki]
    security_opt: [no-new-privileges:true]
volumes:
  loki_data:
  alloy_data:
  grafana_data:
```

## scripts/backup.sh

```sh
#!/bin/sh
set -eu
umask 077
: "${PGDATABASE:?Set PGDATABASE, PGHOST, PGUSER and PGPASSWORD securely}"
: "${BACKUP_GPG_KEY:?Set BACKUP_GPG_KEY outside source control}"
server_major=$(psql --no-psqlrc --tuples-only --no-align -c 'SHOW server_version_num' | awk '{print int($1/10000)}')
client_major=$(pg_dump --version | sed -n 's/.* \([0-9][0-9]*\)\..*/\1/p')
[ "$server_major" = "$client_major" ] || { echo 'Use pg_dump with the same major version as the server' >&2; exit 1; }
destination=${BACKUP_DIR:-backups}
mkdir -p "$destination"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
stamp=$(date -u +%Y%m%dT%H%M%SZ)
name="datapulse-$stamp.dump.gpg"
test ! -e "$destination/$name"
pg_dump --format=custom --no-owner --no-privileges --file="$work/database.dump"
printf '%s\n' "$BACKUP_GPG_KEY" | gpg --batch --yes --pinentry-mode loopback \
  --passphrase-fd 0 --symmetric --cipher-algo AES256 --output "$work/$name" "$work/database.dump"
(cd "$work" && sha256sum "$name" > "$name.sha256")
mv "$work/$name" "$destination/$name"
mv "$work/$name.sha256" "$destination/$name.sha256"
if [ -n "${BACKUP_BUCKET:-}" ]; then
  case "$BACKUP_BUCKET" in s3://*) ;; *) echo 'BACKUP_BUCKET must start with s3://' >&2; exit 1;; esac
  command -v aws >/dev/null
  aws s3 cp "$destination/$name" "${BACKUP_BUCKET%/}/$name" --only-show-errors
  aws s3 cp "$destination/$name.sha256" "${BACKUP_BUCKET%/}/$name.sha256" --only-show-errors
fi
printf 'Backup cifrado: %s/%s\n' "$destination" "$name"
```

## scripts/restore.sh

```sh
#!/bin/sh
set -eu
umask 077
: "${PGDATABASE:?Set the isolated target PGDATABASE}"
: "${RESTORE_CONFIRM_DATABASE:?Explicitly confirm the target database name}"
: "${BACKUP_GPG_KEY:?Set BACKUP_GPG_KEY outside source control}"
: "${HEALTH_URL:?Set the restored backend health URL}"
[ "$PGDATABASE" = "$RESTORE_CONFIRM_DATABASE" ] || { echo 'Target confirmation mismatch' >&2; exit 1; }
started=$(date +%s)
# Refuse to migrate/verify a different database from the restore destination.
uv run --frozen python backend/manage.py shell -c "import os; from django.conf import settings; d=settings.DATABASES['default']; assert d['ENGINE']=='django.db.backends.postgresql' and d['NAME']==os.environ['PGDATABASE'] and d['HOST']==os.environ.get('PGHOST','') and str(d.get('PORT') or 5432)==os.environ.get('PGPORT','5432'), 'Django and PG restore destinations differ'"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
archive=${1:-}
if [ -z "$archive" ]; then
  : "${BACKUP_BUCKET:?Provide an archive path or BACKUP_BUCKET}"
  case "$BACKUP_BUCKET" in s3://*) ;; *) exit 1;; esac
  name=$(aws s3 ls "${BACKUP_BUCKET%/}/" | awk '/datapulse-[0-9]+T[0-9]+Z.dump.gpg$/ {print $4}' | sort | tail -n 1)
  [ -n "$name" ] || { echo 'No backup found' >&2; exit 1; }
  printf '%s\n' "$name" | grep -Eq '^datapulse-[0-9]{8}T[0-9]{6}Z\.dump\.gpg$' || { echo 'Invalid backup object name' >&2; exit 1; }
  aws s3 cp "${BACKUP_BUCKET%/}/$name" "$work/$name" --only-show-errors
  aws s3 cp "${BACKUP_BUCKET%/}/$name.sha256" "$work/$name.sha256" --only-show-errors
else
  name=$(basename "$archive")
  cp "$archive" "$work/$name"
  cp "$archive.sha256" "$work/$name.sha256"
fi
# Validate exactly this archive, never paths embedded in an untrusted manifest.
expected=$(awk 'NR==1 {print $1}' "$work/$name.sha256")
actual=$(sha256sum "$work/$name" | awk '{print $1}')
[ "${#expected}" -eq 64 ] && [ "$expected" = "$actual" ] || { echo 'SHA256 mismatch' >&2; exit 1; }
printf '%s\n' "$BACKUP_GPG_KEY" | gpg --batch --yes --pinentry-mode loopback \
  --passphrase-fd 0 --decrypt --output "$work/database.dump" "$work/$name"
pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges --dbname="$PGDATABASE" "$work/database.dump"
# Run from the repo root in an environment with uv and PostgreSQL client tools.
uv run --frozen python backend/manage.py migrate --noinput
if [ "${RESTORE_SEED_DEMO:-false}" = true ]; then
  uv run --frozen python backend/manage.py seed_data
fi
uv run --frozen python backend/manage.py check
uv run --frozen python backend/manage.py verificar_auditoria
curl --fail --silent --show-error "$HEALTH_URL" >/dev/null
elapsed=$(( $(date +%s) - started ))
printf '{"event":"restore_verification","ok":true,"duration_seconds":%s}\n' "$elapsed"
```

## scripts/siem_logs.ps1

```powershell
# Run from repository root. Separate terminal; Ctrl+C stops only log capture.
New-Item -ItemType Directory -Force -Path tmp/siem | Out-Null
docker compose logs --follow --no-color --no-log-prefix backend db | Out-File -FilePath tmp/siem/services.log -Encoding utf8
```

## scripts/build_siem_config.py

```python
"""Regenerate provisioned dashboard and rules; no network or secrets."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUESTS = '{job="datapulse"} | json | event="request" | __error__=""'
PANELS = [
    ('Top IPs: login 401 (15 min)', f'topk(10, sum by (ip) (count_over_time({REQUESTS} | path="/api/auth/login/" | status=401 [15m])))'),
    ('5xx por endpoint (60 min)', f'sum by (path) (count_over_time({REQUESTS} | status>=500 [1h]))'),
    ('p95 duración ms por endpoint', f'quantile_over_time(0.95, {REQUESTS} | unwrap duracion_ms | __error__="" [1h]) by (path)'),
    ('Errores sync por país y operación', 'sum by (pais, operacion) (count_over_time({job="datapulse"} | json | event="sync_error" | __error__="" [1h]))'),
]
RULES = [
    ('brute_force_login', f'sum by (ip) (count_over_time({REQUESTS} | path="/api/auth/login/" | status=401 [1m]))', 4),
    ('privilege_escalation_attempt', 'sum(count_over_time({job="datapulse"} | json | event="privilege_escalation_attempt" | __error__="" [5m]))', 0),
    ('mass_conflict', f'sum by (usuario_id) (count_over_time({REQUESTS} | status=409 [5m]))', 9),
    ('error_5xx_burst', f'sum(count_over_time({REQUESTS} | status>=500 [5m])) / sum(count_over_time({REQUESTS} [5m]))', 0.05),
    ('audit_chain_broken', 'sum(count_over_time({job="datapulse"} | json | event="audit_verification" | ok="false" | __error__="" [5m]))', 0),
]


def main():
    panels = [{'id': i + 1, 'type': 'timeseries', 'title': title,
        'datasource': {'type': 'loki', 'uid': 'loki'},
        'gridPos': {'x': (i % 2) * 12, 'y': (i // 2) * 9, 'w': 12, 'h': 9},
        'targets': [{'refId': 'A', 'expr': expression, 'queryType': 'range'}]} for i, (title, expression) in enumerate(PANELS)]
    dashboard = {'uid': 'datapulse-security', 'title': 'DataPulse Security', 'schemaVersion': 41,
        'version': 1, 'refresh': '10s', 'time': {'from': 'now-1h', 'to': 'now'}, 'panels': panels}
    (ROOT / 'ops/grafana/dashboards/datapulse.json').write_text(json.dumps(dashboard, indent=2) + '\n', encoding='utf-8')
    rules = []
    for title, expression, threshold in RULES:
        rules.append({'uid': title, 'title': title, 'condition': 'B', 'for': '0s',
            'noDataState': 'OK', 'execErrState': 'Error',
            'labels': {'service': 'datapulse', 'severity': 'warning'},
            'annotations': {'summary': title + ': revisar docs/IR.md; confirmar antes de contener.'},
            'data': [
                {'refId': 'A', 'relativeTimeRange': {'from': 600, 'to': 0}, 'datasourceUid': 'loki',
                 'model': {'refId': 'A', 'expr': expression, 'queryType': 'instant', 'instant': True, 'intervalMs': 1000, 'maxDataPoints': 43200}},
                {'refId': 'B', 'relativeTimeRange': {'from': 0, 'to': 0}, 'datasourceUid': '__expr__',
                 'model': {'refId': 'B', 'type': 'classic_conditions', 'conditions': [{
                     'evaluator': {'type': 'gt', 'params': [threshold]}, 'operator': {'type': 'and'},
                     'query': {'params': ['A']}, 'reducer': {'type': 'last', 'params': []}, 'type': 'query'}]}}
            ]})
    output = {'apiVersion': 1, 'groups': [{'orgId': 1, 'name': 'datapulse', 'folder': 'DataPulse', 'interval': '1m', 'rules': rules}]}
    (ROOT / 'ops/grafana/rules.yaml').write_text(yaml.safe_dump(output, sort_keys=False), encoding='utf-8')


if __name__ == '__main__':
    main()
```

## scripts/verify_siem.py

```python
"""Validate provisioned Grafana resources and every dashboard/rule LogQL query."""
import json
import os
from pathlib import Path
from time import sleep
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    grafana = os.environ.get('GRAFANA_URL', 'http://127.0.0.1:13000')
    loki = os.environ.get('LOKI_URL', 'http://127.0.0.1:13100')
    auth = (os.environ.get('GRAFANA_ADMIN_USER', 'admin'), os.environ['GRAFANA_ADMIN_PASSWORD'])
    for _ in range(30):
        try:
            response = requests.get(grafana + '/api/health', timeout=3)
            if response.ok:
                break
        except requests.RequestException:
            pass
        sleep(1)
    response = requests.get(grafana + '/api/dashboards/uid/datapulse-security', auth=auth, timeout=10)
    response.raise_for_status()
    assert len(response.json()['dashboard']['panels']) == 4
    rules = requests.get(grafana + '/api/v1/provisioning/alert-rules', auth=auth, timeout=10)
    rules.raise_for_status()
    assert len(rules.json()) == 5
    dashboard = json.loads((ROOT / 'ops/grafana/dashboards/datapulse.json').read_text())
    provisioning = yaml.safe_load((ROOT / 'ops/grafana/rules.yaml').read_text())
    expressions = [p['targets'][0]['expr'] for p in dashboard['panels']]
    expressions += [r['data'][0]['model']['expr'] for r in provisioning['groups'][0]['rules']]
    for expression in expressions:
        response = requests.get(loki + '/loki/api/v1/query', params={'query': expression}, timeout=30)
        response.raise_for_status()
        assert response.json()['status'] == 'success', response.text
    count = 0
    for _ in range(30):
        rows = requests.get(loki + '/loki/api/v1/query_range', params={'query': '{job="datapulse"}', 'limit': 100}, timeout=30)
        rows.raise_for_status()
        count = sum(len(stream['values']) for stream in rows.json()['data']['result'])
        if count:
            break
        sleep(1)
    assert count > 0, 'No ingested data; capture real backend/DB logs first.'
    print(json.dumps({'dashboard_panels': 4, 'rules': 5, 'queries_validated': len(expressions), 'ingested_rows_sample': count}))


if __name__ == '__main__':
    main()
```

## backend/core/migrations/0003_logactividad_hash_chain.py

```python
import hashlib
import hmac
import json
from datetime import timezone
from django.conf import settings
from django.db import migrations, models


def backfill(apps, schema_editor):
    Log = apps.get_model('core', 'LogActividad')
    Head = apps.get_model('core', 'AuditHead')
    alias = schema_editor.connection.alias
    previous = None
    for row in Log.objects.using(alias).order_by('pk').iterator():
        fields = {'v': 1, 'id': row.pk, 'usuario_id': row.usuario_id, 'accion': row.accion,
                  'entidad_afectada': row.entidad_afectada, 'entidad_id': row.entidad_id,
                  'detalle': row.detalle, 'ip_address': row.ip_address,
                  'fecha': row.fecha.astimezone(timezone.utc).isoformat()}
        payload = json.dumps(fields, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        digest = hashlib.sha256(((previous or '') + payload).encode()).hexdigest()
        signature = hmac.new(settings.AUDIT_HMAC_KEY.encode(), digest.encode(), hashlib.sha256).hexdigest()
        Log.objects.using(alias).filter(pk=row.pk).update(hash_anterior=previous, hash_actual=digest, firma_hmac=signature)
        previous = digest
    Head.objects.using(alias).create(pk=1, hash_actual=previous or '')


def append_only(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    # REVOKE alone does not restrict a table owner (the default local role).
    # A trigger also blocks owners' UPDATE/DELETE; a separate non-owner role is
    # still required in production. Superusers can always bypass this control.
    schema_editor.execute('''
        CREATE FUNCTION datapulse_audit_append_only() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit log is append-only' USING ERRCODE = '42501'; END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER datapulse_audit_append_only BEFORE UPDATE OR DELETE
        ON core_logactividad FOR EACH ROW EXECUTE FUNCTION datapulse_audit_append_only();
        REVOKE UPDATE, DELETE ON core_logactividad FROM CURRENT_USER;
    ''')


def remove_guard(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('''DROP TRIGGER IF EXISTS datapulse_audit_append_only ON core_logactividad;
            DROP FUNCTION IF EXISTS datapulse_audit_append_only();
            GRANT UPDATE, DELETE ON core_logactividad TO CURRENT_USER;''')


class Migration(migrations.Migration):
    dependencies = [('core', '0002_dominio_economico')]
    operations = [
        migrations.CreateModel(name='AuditHead', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('hash_actual', models.CharField(blank=True, default='', max_length=64)),
        ]),
        migrations.AlterField(model_name='logactividad', name='accion', field=models.CharField(
            choices=[('CREAR', 'Crear'), ('EDITAR', 'Editar'), ('ELIMINAR', 'Eliminar'),
                     ('CONSULTAR', 'Consultar'), ('LOGIN', 'Login'), ('EXPORT', 'Exportar')], max_length=32)),
        migrations.AddField(model_name='logactividad', name='hash_anterior', field=models.CharField(blank=True, max_length=64, null=True)),
        migrations.AddField(model_name='logactividad', name='hash_actual', field=models.CharField(max_length=64, null=True)),
        migrations.AddField(model_name='logactividad', name='firma_hmac', field=models.CharField(max_length=64, default=''), preserve_default=False),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AlterField(model_name='logactividad', name='hash_actual', field=models.CharField(max_length=64, unique=True)),
        migrations.RunPython(append_only, remove_guard),
    ]
```

## backend/core/migrations/0004_idempotentrequest.py

```python
# Generated by Django 5.2.19 on 2026-11-18 18:13

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_logactividad_hash_chain'),
    ]

    operations = [
        migrations.CreateModel(
            name='IdempotentRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=100)),
                ('key', models.CharField(max_length=128)),
                ('body_hash', models.CharField(max_length=64)),
                ('response', models.JSONField()),
                ('expires', models.DateTimeField()),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('usuario', 'path', 'key'), name='idempotency_user_path_key')],
            },
        ),
    ]
```

## backend/core/migrations/0005_usuario_mfa_enabled_usuario_mfa_epoch_and_more.py

```python
# Generated by Django 5.2.19 on 2026-11-18 18:22

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_idempotentrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='mfa_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usuario',
            name='mfa_epoch',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='usuario',
            name='mfa_last_t',
            field=models.BigIntegerField(default=-1),
        ),
        migrations.AddField(
            model_name='usuario',
            name='mfa_secret_enc',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='recovery_codes_enc',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='MFALoginChallenge',
            fields=[
                ('digest', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('expires', models.DateTimeField()),
                ('used', models.BooleanField(default=False)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
```

## backend/core/migrations/0006_alter_logactividad_accion.py

```python
# Generated by Django 5.2.19 on 2026-11-18 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_usuario_mfa_enabled_usuario_mfa_epoch_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='logactividad',
            name='accion',
            field=models.CharField(choices=[('CREAR', 'Crear'), ('EDITAR', 'Editar'), ('ELIMINAR', 'Eliminar'), ('CONSULTAR', 'Consultar'), ('LOGIN', 'Login'), ('EXPORT', 'Exportar'), ('LOGIN_FALLIDO', 'Login fallido'), ('LOGIN_BLOQUEADO', 'Login bloqueado'), ('PASSWORD_CHANGE', 'Cambio de contraseña'), ('MFA_ENROLL', 'Enrolar MFA'), ('MFA_VERIFY_OK', 'Verificación MFA correcta'), ('MFA_VERIFY_FAIL', 'Verificación MFA fallida'), ('MFA_DISABLE', 'Deshabilitar MFA'), ('CORRECCION', 'Corrección de auditoría')], max_length=32),
        ),
    ]
```

## backend/core/tests/test_security_auth.py

```python
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
        with patch('core.data_api.sync_and_recalculate', return_value={'ok': True}) as execute:
            for _ in range(2):
                self.assertEqual(self.client.post('/api/paises/sync-indicadores/').status_code, 200)
            self.assertEqual(self.client.post('/api/paises/sync-indicadores/').status_code, 429)
            self.assertEqual(execute.call_count, 2)

    def test_idempotency_isolated_by_user_endpoint_and_body(self):
        self.authenticate(self.admin)
        def run():
            from core.audit import audit
            audit(self.admin, 'CONSULTAR', self.admin)
            return {'ok': True}
        with patch('core.data_api.sync_and_recalculate', side_effect=run) as execute:
            for _ in range(2):
                result = self.client.post('/api/paises/sync-indicadores/', {'a': 1}, HTTP_IDEMPOTENCY_KEY='example')
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.data, {'ok': True})
            self.assertEqual(execute.call_count, 1)
            self.assertEqual(LogActividad.objects.filter(accion='CONSULTAR').count(), 1)
            cache.clear()
            conflict = self.client.post('/api/paises/sync-indicadores/', {'a': 2}, HTTP_IDEMPOTENCY_KEY='example')
            self.assertEqual(conflict.status_code, 409)
```

## backend/core/tests/test_security_headers.py

```python
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
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Content-Security-Policy', response)
        self.assertIn('Permissions-Policy', response)
        self.assertEqual(self.client.get('/api/schema/').status_code, 200)

    def test_proxy_header_untrusted_by_default(self):
        self.assertIsNone(settings.SECURE_PROXY_SSL_HEADER)
```

## backend/core/tests/test_security_startup.py

```python
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
```

## backend/core/tests/test_audit_chain.py

```python
import json
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction, DatabaseError
from django.test import override_settings
from core.audit import audit
from core.models import LogActividad
from core.services.audit_chain import verify
from .helpers import APICase


class AuditChainTests(APICase):
    def test_hash_chain_valid_after_100_inserts(self):
        for n in range(100):
            audit(self.user, 'CONSULTAR', self.user, {'n': n})
        output = StringIO()
        call_command('verificar_auditoria', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['checked'], 100)

    def test_tampering_detected_or_blocked(self):
        audit(self.user, 'CONSULTAR', self.user)
        if connection.vendor == 'postgresql':
            with self.assertRaises(DatabaseError), transaction.atomic():
                LogActividad.objects.update(detalle={'changed': True})
            with self.assertRaises(DatabaseError), transaction.atomic():
                LogActividad.objects.all().delete()
            self.assertTrue(verify()['ok'])
        else:
            LogActividad.objects.update(detalle={'changed': True})
            output = StringIO()
            with self.assertRaises(CommandError):
                call_command('verificar_auditoria', stdout=output)
            self.assertEqual(json.loads(output.getvalue())['cause'], 'hash')

    def test_wrong_hmac_key_detected(self):
        audit(self.user, 'CONSULTAR', self.user)
        with override_settings(AUDIT_HMAC_KEY='different-test-key'):
            self.assertEqual(verify()['cause'], 'hmac')

    def test_transaction_rollback_preserves_head(self):
        audit(self.user, 'CONSULTAR', self.user)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                audit(self.user, 'EDITAR', self.user)
                raise RuntimeError('rollback')
        self.assertEqual(verify()['checked'], 1)
        self.assertTrue(verify()['ok'])
```

## backend/core/tests/test_audit_migration.py

```python
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor
from django.db import connections


class AuditMigrationTests(TransactionTestCase):
    def test_concurrent_appends_do_not_fork(self):
        from core.audit import audit
        from core.models import Usuario, AuditHead
        from core.services.audit_chain import verify
        AuditHead.objects.get_or_create(pk=1)
        def write(number):
            connections.close_all()
            try:
                audit(None, 'CONSULTAR', Usuario(pk='concurrent'), {'n': number})
            finally:
                connections.close_all()
        if connection.vendor == 'postgresql':
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(write, range(20)))
        else:
            # SQLite's coarse locking is not a multi-writer production target.
            from core.models import Usuario
            for number in range(20):
                audit(None, 'CONSULTAR', Usuario(pk='serial'), {'n': number})
        self.assertTrue(verify()['ok'])
        self.assertEqual(verify()['checked'], 20)

    def test_backfill_preserves_and_seals_legacy_row(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        old = [('core', '0002_dominio_economico')]
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            legacy = apps.get_model('core', 'LogActividad').objects.create(
                accion='CONSULTAR', entidad_afectada='Usuario', entidad_id='legacy', detalle={'legacy': True})
            executor = MigrationExecutor(connection)
            executor.migrate(leaves)
            from core.models import LogActividad
            from core.services.audit_chain import verify
            row = LogActividad.objects.get(pk=legacy.pk)
            self.assertEqual(row.detalle, {'legacy': True})
            self.assertEqual(len(row.hash_actual), 64)
            self.assertEqual(len(row.firma_hmac), 64)
            self.assertTrue(verify()['ok'])
        finally:
            MigrationExecutor(connection).migrate(leaves)
```

## backend/core/tests/test_mfa.py

```python
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
```

## backend/core/tests/test_siem_contract.py

```python
import json
import logging
from core.observability import JsonFormatter
from .helpers import APICase


class SiemContractTests(APICase):
    def test_failed_login_emits_safe_json(self):
        with self.assertLogs('datapulse', level='INFO') as captured:
            self.client.post('/api/auth/login/', {'email': self.user.email, 'password': 'never-log-this'})
        rows = [json.loads(JsonFormatter().format(record)) for record in captured.records]
        request = next(row for row in rows if row['event'] == 'request')
        self.assertEqual(request['status'], 401)
        self.assertEqual(request['path'], '/api/auth/login/')
        self.assertIn('duracion_ms', request)
        self.assertNotIn('never-log-this', json.dumps(rows))

    def test_audit_verification_json_retains_evidence_fields(self):
        record = logging.makeLogRecord({'msg': 'audit_verification', 'ok': False, 'broken_id': 42, 'checked': 41})
        row = json.loads(JsonFormatter().format(record))
        self.assertFalse(row['ok'])
        self.assertEqual(row['broken_id'], 42)

    def test_sync_error_contains_country_and_error_code_without_exception_text(self):
        from core.services.sync import report_error
        with self.assertLogs('datapulse', level='ERROR') as captured:
            report_error({'errores': []}, 'CO', 'WORLD_BANK', ValueError('provider-key-secret'))
        row = json.loads(JsonFormatter().format(captured.records[0]))
        self.assertEqual(row['event'], 'sync_error')
        self.assertEqual(row['pais'], 'CO')
        self.assertEqual(row['error_code'], 'ValueError')
        self.assertNotIn('provider-key-secret', json.dumps(row))
```

## ops/backup.Dockerfile

```
# Verification/toolbox image only, never the application runtime.
FROM postgres:16-alpine
RUN apk add --no-cache gnupg curl
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_NO_DEV=1 UV_NO_SYNC=1
COPY pyproject.toml uv.lock .python-version /build/
RUN cd /build && uv sync --frozen --no-dev --python 3.12
WORKDIR /workspace
ENTRYPOINT []
```

## ops/loki.yaml

```yaml
auth_enabled: false
server:
  http_listen_port: 3100
common:
  path_prefix: /loki
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
schema_config:
  configs:
    - from: 2024-04-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
limits_config:
  retention_period: 168h
compactor:
  working_directory: /loki/compactor
  retention_enabled: true
  delete_request_store: filesystem
```

## ops/alloy/config.alloy

```
local.file_match "datapulse" {
  path_targets = [{"__path__" = "/var/log/datapulse/*.log", "job" = "datapulse"}]
  sync_period = "5s"
}

loki.source.file "datapulse" {
  targets = local.file_match.datapulse.targets
  forward_to = [loki.process.datapulse.receiver]
}

loki.process "datapulse" {
  stage.json {
    expressions = {"event" = "event", "timestamp" = "timestamp"}
  }
  stage.timestamp {
    source = "timestamp"
    format = "RFC3339Nano"
    action_on_failure = "skip"
  }
  stage.labels {
    values = {"event" = ""}
  }
  forward_to = [loki.write.local.receiver]
}

loki.write "local" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

## ops/grafana/rules.yaml

```yaml
apiVersion: 1
groups:
- orgId: 1
  name: datapulse
  folder: DataPulse
  interval: 1m
  rules:
  - uid: brute_force_login
    title: brute_force_login
    condition: B
    for: 0s
    noDataState: OK
    execErrState: Error
    labels:
      service: datapulse
      severity: warning
    annotations:
      summary: 'brute_force_login: revisar docs/IR.md; confirmar antes de contener.'
    data:
    - refId: A
      relativeTimeRange:
        from: 600
        to: 0
      datasourceUid: loki
      model:
        refId: A
        expr: sum by (ip) (count_over_time({job="datapulse"} | json | event="request"
          | __error__="" | path="/api/auth/login/" | status=401 [1m]))
        queryType: instant
        instant: true
        intervalMs: 1000
        maxDataPoints: 43200
    - refId: B
      relativeTimeRange:
        from: 0
        to: 0
      datasourceUid: __expr__
      model:
        refId: B
        type: classic_conditions
        conditions:
        - evaluator:
            type: gt
            params:
            - 4
          operator:
            type: and
          query:
            params:
            - A
          reducer:
            type: last
            params: []
          type: query
  - uid: privilege_escalation_attempt
    title: privilege_escalation_attempt
    condition: B
    for: 0s
    noDataState: OK
    execErrState: Error
    labels:
      service: datapulse
      severity: warning
    annotations:
      summary: 'privilege_escalation_attempt: revisar docs/IR.md; confirmar antes
        de contener.'
    data:
    - refId: A
      relativeTimeRange:
        from: 600
        to: 0
      datasourceUid: loki
      model:
        refId: A
        expr: sum(count_over_time({job="datapulse"} | json | event="privilege_escalation_attempt"
          | __error__="" [5m]))
        queryType: instant
        instant: true
        intervalMs: 1000
        maxDataPoints: 43200
    - refId: B
      relativeTimeRange:
        from: 0
        to: 0
      datasourceUid: __expr__
      model:
        refId: B
        type: classic_conditions
        conditions:
        - evaluator:
            type: gt
            params:
            - 0
          operator:
            type: and
          query:
            params:
            - A
          reducer:
            type: last
            params: []
          type: query
  - uid: mass_conflict
    title: mass_conflict
    condition: B
    for: 0s
    noDataState: OK
    execErrState: Error
    labels:
      service: datapulse
      severity: warning
    annotations:
      summary: 'mass_conflict: revisar docs/IR.md; confirmar antes de contener.'
    data:
    - refId: A
      relativeTimeRange:
        from: 600
        to: 0
      datasourceUid: loki
      model:
        refId: A
        expr: sum by (usuario_id) (count_over_time({job="datapulse"} | json | event="request"
          | __error__="" | status=409 [5m]))
        queryType: instant
        instant: true
        intervalMs: 1000
        maxDataPoints: 43200
    - refId: B
      relativeTimeRange:
        from: 0
        to: 0
      datasourceUid: __expr__
      model:
        refId: B
        type: classic_conditions
        conditions:
        - evaluator:
            type: gt
            params:
            - 9
          operator:
            type: and
          query:
            params:
            - A
          reducer:
            type: last
            params: []
          type: query
  - uid: error_5xx_burst
    title: error_5xx_burst
    condition: B
    for: 0s
    noDataState: OK
    execErrState: Error
    labels:
      service: datapulse
      severity: warning
    annotations:
      summary: 'error_5xx_burst: revisar docs/IR.md; confirmar antes de contener.'
    data:
    - refId: A
      relativeTimeRange:
        from: 600
        to: 0
      datasourceUid: loki
      model:
        refId: A
        expr: sum(count_over_time({job="datapulse"} | json | event="request" | __error__=""
          | status>=500 [5m])) / sum(count_over_time({job="datapulse"} | json | event="request"
          | __error__="" [5m]))
        queryType: instant
        instant: true
        intervalMs: 1000
        maxDataPoints: 43200
    - refId: B
      relativeTimeRange:
        from: 0
        to: 0
      datasourceUid: __expr__
      model:
        refId: B
        type: classic_conditions
        conditions:
        - evaluator:
            type: gt
            params:
            - 0.05
          operator:
            type: and
          query:
            params:
            - A
          reducer:
            type: last
            params: []
          type: query
  - uid: audit_chain_broken
    title: audit_chain_broken
    condition: B
    for: 0s
    noDataState: OK
    execErrState: Error
    labels:
      service: datapulse
      severity: warning
    annotations:
      summary: 'audit_chain_broken: revisar docs/IR.md; confirmar antes de contener.'
    data:
    - refId: A
      relativeTimeRange:
        from: 600
        to: 0
      datasourceUid: loki
      model:
        refId: A
        expr: sum(count_over_time({job="datapulse"} | json | event="audit_verification"
          | ok="false" | __error__="" [5m]))
        queryType: instant
        instant: true
        intervalMs: 1000
        maxDataPoints: 43200
    - refId: B
      relativeTimeRange:
        from: 0
        to: 0
      datasourceUid: __expr__
      model:
        refId: B
        type: classic_conditions
        conditions:
        - evaluator:
            type: gt
            params:
            - 0
          operator:
            type: and
          query:
            params:
            - A
          reducer:
            type: last
            params: []
          type: query
```

## ops/grafana/dashboards/datapulse.json

```json
{
  "uid": "datapulse-security",
  "title": "DataPulse Security",
  "schemaVersion": 41,
  "version": 1,
  "refresh": "10s",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "panels": [
    {
      "id": 1,
      "type": "timeseries",
      "title": "Top IPs: login 401 (15 min)",
      "datasource": {
        "type": "loki",
        "uid": "loki"
      },
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 9
      },
      "targets": [
        {
          "refId": "A",
          "expr": "topk(10, sum by (ip) (count_over_time({job=\"datapulse\"} | json | event=\"request\" | __error__=\"\" | path=\"/api/auth/login/\" | status=401 [15m])))",
          "queryType": "range"
        }
      ]
    },
    {
      "id": 2,
      "type": "timeseries",
      "title": "5xx por endpoint (60 min)",
      "datasource": {
        "type": "loki",
        "uid": "loki"
      },
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 9
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (path) (count_over_time({job=\"datapulse\"} | json | event=\"request\" | __error__=\"\" | status>=500 [1h]))",
          "queryType": "range"
        }
      ]
    },
    {
      "id": 3,
      "type": "timeseries",
      "title": "p95 duraci\u00f3n ms por endpoint",
      "datasource": {
        "type": "loki",
        "uid": "loki"
      },
      "gridPos": {
        "x": 0,
        "y": 9,
        "w": 12,
        "h": 9
      },
      "targets": [
        {
          "refId": "A",
          "expr": "quantile_over_time(0.95, {job=\"datapulse\"} | json | event=\"request\" | __error__=\"\" | unwrap duracion_ms | __error__=\"\" [1h]) by (path)",
          "queryType": "range"
        }
      ]
    },
    {
      "id": 4,
      "type": "timeseries",
      "title": "Errores sync por pa\u00eds y operaci\u00f3n",
      "datasource": {
        "type": "loki",
        "uid": "loki"
      },
      "gridPos": {
        "x": 12,
        "y": 9,
        "w": 12,
        "h": 9
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (pais, operacion) (count_over_time({job=\"datapulse\"} | json | event=\"sync_error\" | __error__=\"\" [1h]))",
          "queryType": "range"
        }
      ]
    }
  ]
}
```

## ops/grafana/provisioning/dashboards/datapulse.yaml

```yaml
apiVersion: 1
providers:
  - name: datapulse
    folder: DataPulse
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

## ops/grafana/provisioning/datasources/loki.yaml

```yaml
apiVersion: 1
datasources:
  - name: Loki
    uid: loki
    type: loki
    access: proxy
    url: http://loki:3100
    isDefault: true
    editable: false
```

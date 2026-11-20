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
CACHE_SHARED = env.bool('CACHE_SHARED', default=not DEBUG)
SYNC_WORKER_REQUIRED = env.bool('SYNC_WORKER_REQUIRED', default=False)
CACHES = {'default': {
    'BACKEND': ('core.cache.SharedDatabaseCache' if CACHE_SHARED else
                'django.core.cache.backends.locmem.LocMemCache'),
    'LOCATION': 'datapulse_cache' if CACHE_SHARED else 'datapulse-local',
    'KEY_PREFIX': 'datapulse',
    'TIMEOUT': 300,
    'OPTIONS': {'MAX_ENTRIES': 10000},
}}
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
    'DEFAULT_THROTTLE_CLASSES': ['core.throttling.SharedAnonRateThrottle', 'core.throttling.SharedUserRateThrottle', 'core.security_auth.ActionThrottle'],
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


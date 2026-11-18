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

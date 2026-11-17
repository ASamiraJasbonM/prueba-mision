import ipaddress
import json
import logging
from contextvars import ContextVar
from time import perf_counter_ns
from django.utils import timezone

request_ip = ContextVar('request_ip', default=None)
logger = logging.getLogger('datapulse')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        result = {'timestamp': timezone.now().isoformat(), 'level': record.levelname, 'event': record.getMessage()}
        for key in ['metodo', 'path', 'usuario_id', 'ip', 'duracion_ms', 'status', 'pais', 'operacion', 'error_code', 'actualizados', 'errores']:
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
            return response
        finally:
            user = getattr(request, 'user', None)
            logger.info('request', extra={'metodo': request.method, 'path': request.path,
                'usuario_id': user.pk if user and user.is_authenticated else None,
                'ip': ip, 'duracion_ms': (perf_counter_ns()-started)//1000000,
                'status': response.status_code if response else 500})
            request_ip.reset(token)

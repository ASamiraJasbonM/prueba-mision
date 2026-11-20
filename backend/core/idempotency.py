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
                status = 202 if existing.response.get('estado_url') else 200
                return Response(existing.response, status=status)
            result = function(view, request, *args, **kwargs)
            if result.status_code in (200, 202):
                IdempotentRequest.objects.update_or_create(**lookup, defaults={
                    'body_hash': digest, 'response': result.data, 'expires': timezone.now() + timedelta(minutes=5)})
            return result
    return wrapped

"""Shared budgets, serialized per identity on the reference PostgreSQL engine."""
import hashlib

from django.conf import settings
from django.db import connection, transaction
from rest_framework.exceptions import APIException
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class ThrottleUnavailable(APIException):
    status_code = 503
    default_code = 'throttle_unavailable'
    default_detail = 'No se pudieron validar los límites. Intenta de nuevo más tarde.'


class SharedBudgetMixin:
    def allow_request(self, request, view):
        scope = getattr(self, 'scope', None) or getattr(view, 'throttle_scope', None)
        if (not settings.CACHE_SHARED or connection.vendor != 'postgresql' or not scope
                or (scope == 'anon' and request.user.is_authenticated)):
            return super().allow_request(request, view)
        identity = str(request.user.pk) if request.user.is_authenticated else self.get_ident(request)
        digest = hashlib.sha256(f'datapulse:throttle:{scope}:{identity}'.encode()).digest()
        lock_id = int.from_bytes(digest[:8], byteorder='big', signed=True)
        # All workers use the same database cache and transaction-scoped lock.
        # No lock is held while a view executes, writes business data or calls APIs.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [lock_id])
            return super().allow_request(request, view)

    def throttle_success(self):
        if not settings.CACHE_SHARED:
            return super().throttle_success()
        self.history.insert(0, self.now)
        # DatabaseCache reports failed writes as False; never silently grant an
        # unrecorded slot when the shared budget cannot be persisted.
        if not self.cache.set(self.key, self.history, self.duration):
            raise ThrottleUnavailable()
        return True


class SharedAnonRateThrottle(SharedBudgetMixin, AnonRateThrottle):
    pass


class SharedUserRateThrottle(SharedBudgetMixin, UserRateThrottle):
    pass

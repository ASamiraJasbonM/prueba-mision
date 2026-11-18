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

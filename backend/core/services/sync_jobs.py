"""Durable single-flight queue, with recoverable leases and fenced result writes."""
from datetime import timedelta
import logging
import uuid

from django.db import IntegrityError, transaction
from django.db.models import Q, F
from django.utils import timezone
from core.models import SyncJob, SyncWorkerPulse
from core.audit import audit
from .tasks import sync_and_recalculate

logger = logging.getLogger('datapulse')
ACTIVE = ['PENDIENTE', 'EJECUTANDO']


class LostLease(RuntimeError):
    pass


def enqueue(user):
    try:
        with transaction.atomic():
            job = SyncJob.objects.create(usuario=user)
            audit(user, 'CREAR', job)
            return job
    except IntegrityError:
        existing = SyncJob.objects.filter(estado__in=ACTIVE).first()
        if existing:
            return existing
        raise


def pulse():
    SyncWorkerPulse.objects.update_or_create(pk=1, defaults={'actualizado': timezone.now()})


def claim_job():
    now = timezone.now()
    SyncJob.objects.filter(estado='EJECUTANDO', lease_until__lt=now, intentos__gte=3).update(
        estado='FALLIDA', terminado=now, resultado={'mensaje': 'La ejecución se interrumpió tres veces. Puedes solicitar otra sincronización.'})
    eligible = Q(estado='PENDIENTE') | Q(estado='EJECUTANDO', lease_until__lt=now)
    candidate = SyncJob.objects.filter(eligible).order_by('creado').first()
    if not candidate:
        return None
    changed = SyncJob.objects.filter(pk=candidate.pk).filter(eligible).update(
        estado='EJECUTANDO', iniciado=now, lease_token=uuid.uuid4(),
        lease_until=now+timedelta(seconds=90), intentos=F('intentos')+1)
    return SyncJob.objects.get(pk=candidate.pk) if changed else None


def update_progress(job, progress):
    now = timezone.now()
    changed = SyncJob.objects.filter(pk=job.pk, estado='EJECUTANDO', lease_token=job.lease_token,
        lease_until__gt=now).update(progreso=progress, lease_until=now+timedelta(seconds=90))
    if not changed:
        raise LostLease()
    pulse()


def finish_job(job, state, result):
    now = timezone.now()
    with transaction.atomic():
        changed = SyncJob.objects.filter(pk=job.pk, estado='EJECUTANDO', lease_token=job.lease_token,
            lease_until__gt=now).update(estado=state, resultado=result, terminado=now,
                progreso={'fase': 'TERMINADA'}, lease_until=None)
        if changed:
            audit(job.usuario, 'EDITAR', job, {'estado': state})
    return bool(changed)


def process_next_job():
    pulse()
    job = claim_job()
    if job is None:
        return False
    try:
        result = sync_and_recalculate(batch=True, progress=lambda value: update_progress(job, value))
        errors = result.get('errores', []) + result.get('riesgo', {}).get('errores', [])
        # A successful HTTP response with unchanged data is still a successful sync.
        failed = errors and result.get('consultas_exitosas', 0) == 0
        state = 'FALLIDA' if failed else 'PARCIAL' if errors else 'COMPLETADA'
        finish_job(job, state, result)
    except LostLease:
        logger.warning('sync_lease_lost')
    except Exception as exc:
        logger.error('sync_job_error', extra={'error_code': type(exc).__name__})
        finish_job(job, 'FALLIDA', {'mensaje': 'No se pudo completar la sincronización. Los datos confirmados se conservan.'})
    return True

from .models import LogActividad


def audit(user, action, obj, details=None, ip=None):
    LogActividad.objects.create(usuario=user if user and user.is_authenticated else None,
        accion=action, entidad_afectada=obj.__class__.__name__, entidad_id=str(obj.pk),
        detalle=details or {}, ip_address=ip)

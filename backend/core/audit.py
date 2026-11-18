from .services.audit_chain import registrar
from .observability import request_ip


def audit(user, action, obj, details=None, ip=None):
    return registrar(usuario=user if user and user.is_authenticated else None,
        accion=action, entidad_afectada=obj.__class__.__name__, entidad_id=str(obj.pk),
        detalle=details or {}, ip_address=ip or request_ip.get())


log_actividad = audit

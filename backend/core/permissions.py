from rest_framework.permissions import BasePermission, SAFE_METHODS


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'ADMIN'


class PuedeEditarPortafolio(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.method in SAFE_METHODS or request.user.rol in ['ADMIN', 'ANALISTA'])

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return obj.es_publico or obj.usuario_id == request.user.pk or request.user.rol == 'ADMIN'
        return request.user.rol == 'ADMIN' or (request.user.rol == 'ANALISTA' and obj.usuario_id == request.user.pk)

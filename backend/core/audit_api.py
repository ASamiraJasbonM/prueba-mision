from rest_framework import generics, serializers
from .models import LogActividad
from .permissions import EsAdmin


class LogActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogActividad
        fields = ['id', 'usuario', 'accion', 'entidad_afectada', 'entidad_id', 'detalle', 'ip_address', 'fecha']
        read_only_fields = fields


class AuditListView(generics.ListAPIView):
    queryset = LogActividad.objects.select_related('usuario').all()
    serializer_class = LogActividadSerializer
    permission_classes = [EsAdmin]
    filterset_fields = ['accion', 'entidad_afectada', 'usuario']
    ordering_fields = ['fecha', 'accion']

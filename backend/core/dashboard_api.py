from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Pais, Portafolio, IndicadorEconomico
from .risk_api import latest_risks, user_alerts
from .services.numbers import quantize
from .services.sync import INDICATORS
from .services.risk_quality import risk_quality
from .permissions import EsAdmin
from .services import maintenance

COLORS = {'BAJO': '#22c55e', 'MODERADO': '#eab308', 'ALTO': '#f97316', 'CRITICO': '#ef4444'}


class DashboardSummarySerializer(serializers.Serializer):
    total_paises = serializers.IntegerField()
    alertas_activas = serializers.IntegerField()
    portafolios_usuario = serializers.IntegerField()
    promedio_irpc_region = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    paises_con_irpc = serializers.IntegerField()
    paises_irpc_parcial = serializers.IntegerField()
    paises_con_datos_no_verificados = serializers.IntegerField()
    paises_con_datos_rezagados = serializers.IntegerField()


class MapSerializer(serializers.Serializer):
    codigo_iso = serializers.CharField()
    nombre = serializers.CharField()
    latitud = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitud = serializers.DecimalField(max_digits=9, decimal_places=6)
    indice_compuesto = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    nivel_riesgo = serializers.CharField(allow_null=True)
    color = serializers.CharField()
    parcial = serializers.BooleanField()


class TrendQuerySerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=IndicadorEconomico.Tipo.choices, default='PIB')
    paises = serializers.CharField(required=False)


class TrendSerializer(serializers.Serializer):
    pais = serializers.CharField()
    tipo = serializers.CharField()
    anio = serializers.IntegerField()
    valor = serializers.DecimalField(max_digits=28, decimal_places=6, allow_null=True)
    unidad = serializers.CharField()
    fuente = serializers.CharField(allow_null=True)


class MaintenanceRunSerializer(serializers.Serializer):
    id = serializers.CharField()
    estado = serializers.CharField()
    iniciado = serializers.DateTimeField()
    terminado = serializers.DateTimeField(allow_null=True)
    actualizados = serializers.IntegerField()
    errores = serializers.ListField(child=serializers.DictField())
    cobertura = serializers.ListField(child=serializers.DictField())
    commit = serializers.CharField(allow_blank=True)
    ejecucion_url = serializers.URLField(allow_null=True)


class MaintenanceTaskSerializer(serializers.Serializer):
    tarea = serializers.CharField()
    ultima_ejecucion = MaintenanceRunSerializer(allow_null=True)
    ultimo_exito = MaintenanceRunSerializer(allow_null=True)


class DashboardViewSet(viewsets.GenericViewSet):
    serializer_class = DashboardSummarySerializer
    filter_backends = []

    @extend_schema(responses=MaintenanceTaskSerializer(many=True))
    @action(detail=False, methods=['get'], permission_classes=[EsAdmin])
    def mantenimiento(self, request):
        return Response(maintenance.summary())

    @extend_schema(responses=DashboardSummarySerializer)
    @action(detail=False, methods=['get'])
    def resumen(self, request):
        risks = list(latest_risks())
        qualities = [risk_quality(risk) for risk in risks]
        mean = quantize(sum((risk.indice_compuesto for risk in risks), Decimal('0')) / len(risks)) if risks else None
        data = {'total_paises': Pais.objects.count(),
            'alertas_activas': user_alerts(request.user).filter(leida_usuario=False).count(),
            'portafolios_usuario': Portafolio.objects.filter(usuario=request.user).count(),
            'promedio_irpc_region': mean, 'paises_con_irpc': len(risks),
            'paises_irpc_parcial': sum(bool(risk.detalle_calculo.get('parcial')) for risk in risks),
            'paises_con_datos_no_verificados': sum(not quality['solo_fuentes_externas'] for quality in qualities),
            'paises_con_datos_rezagados': sum(quality['datos_rezagados'] for quality in qualities)}
        return Response(DashboardSummarySerializer(data).data)

    @extend_schema(responses=MapSerializer(many=True))
    @action(detail=False, methods=['get'])
    def mapa(self, request):
        risks = {risk.pais_id: risk for risk in latest_risks()}
        rows = []
        for country in Pais.objects.order_by('codigo_iso'):
            risk = risks.get(country.pk)
            rows.append({'codigo_iso': country.pk, 'nombre': country.nombre,
                'latitud': country.latitud, 'longitud': country.longitud,
                'indice_compuesto': risk.indice_compuesto if risk else None,
                'nivel_riesgo': risk.nivel_riesgo if risk else None,
                'color': COLORS[risk.nivel_riesgo] if risk else '#9ca3af',
                'parcial': bool(risk.detalle_calculo.get('parcial')) if risk else True})
        return self.get_paginated_response(MapSerializer(self.paginate_queryset(rows), many=True).data)

    @extend_schema(parameters=[TrendQuerySerializer], responses=TrendSerializer(many=True))
    @action(detail=False, methods=['get'])
    def tendencias(self, request):
        query = TrendQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        kind = query.validated_data['tipo']
        codes = query.validated_data.get('paises')
        codes = [code.strip().upper() for code in codes.split(',')] if codes else list(Pais.objects.order_by('codigo_iso').values_list('pk', flat=True)[:3])
        if not 1 <= len(codes) <= 3 or len(set(codes)) != len(codes):
            raise ValidationError({'paises': 'Selecciona de uno a tres países distintos.'})
        if Pais.objects.filter(pk__in=codes).count() != len(codes):
            raise ValidationError({'paises': 'Uno de los países no existe o está inactivo.'})
        end = timezone.now().year - 1
        values = {(row.pais_id, row.anio): row for row in IndicadorEconomico.objects.filter(
            pais_id__in=codes, tipo=kind, anio__gte=end-4, anio__lte=end)}
        rows = []
        for code in codes:
            for year in range(end-4, end+1):
                record = values.get((code, year))
                rows.append({'pais': code, 'tipo': kind, 'anio': year, 'valor': record.valor if record else None,
                    'unidad': record.unidad if record else INDICATORS[kind][1], 'fuente': record.fuente if record else None})
        return self.get_paginated_response(TrendSerializer(self.paginate_queryset(rows), many=True).data)

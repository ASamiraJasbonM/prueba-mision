import django_filters
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Pais, IndicadorEconomico, TipoCambio
from .permissions import EsAdmin
from .services.sync import sync_indicators


class IndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicadorEconomico
        fields = '__all__'


class CambioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCambio
        fields = '__all__'


class PaisSerializer(serializers.ModelSerializer):
    moneda_codigo = serializers.CharField(read_only=True)
    moneda_nombre = serializers.CharField(read_only=True)

    class Meta:
        model = Pais
        fields = ['codigo_iso', 'nombre', 'moneda_codigo', 'moneda_nombre', 'region',
                  'latitud', 'longitud', 'poblacion', 'bandera_url', 'activo']


class PaisDetalleSerializer(PaisSerializer):
    indicadores = IndicadorSerializer(many=True, read_only=True)

    class Meta(PaisSerializer.Meta):
        fields = PaisSerializer.Meta.fields + ['indicadores']


class IndicadorFilter(django_filters.FilterSet):
    class Meta:
        model = IndicadorEconomico
        fields = ['tipo', 'anio']


class CambioFilter(django_filters.FilterSet):
    fecha_desde = django_filters.DateFilter(field_name='fecha', lookup_expr='gte')
    fecha_hasta = django_filters.DateFilter(field_name='fecha', lookup_expr='lte')

    class Meta:
        model = TipoCambio
        fields = ['fecha_desde', 'fecha_hasta']


class SyncReportSerializer(serializers.Serializer):
    paises_procesados = serializers.IntegerField(required=False)
    actualizados = serializers.IntegerField()
    errores = serializers.ListField(child=serializers.DictField())


class PaisViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pais.objects.select_related('moneda').all().order_by('codigo_iso')
    serializer_class = PaisSerializer
    lookup_field = 'codigo_iso'
    filterset_fields = ['region']
    filterset_class = None
    search_fields = ['nombre', 'codigo_iso']
    ordering_fields = ['nombre', 'codigo_iso', 'poblacion']

    def get_queryset(self):
        if self.action == 'indicadores':
            return IndicadorEconomico.objects.all()
        if self.action == 'tipo_cambio':
            return TipoCambio.objects.all()
        return super().get_queryset()

    def get_country(self):
        return get_object_or_404(Pais.objects.select_related('moneda'), codigo_iso=self.kwargs['codigo_iso'])

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PaisDetalleSerializer
        return super().get_serializer_class()

    @extend_schema(responses=IndicadorSerializer(many=True), parameters=[OpenApiParameter('codigo_iso', str, OpenApiParameter.PATH)])
    @action(detail=True, methods=['get'], queryset=IndicadorEconomico.objects.all(), filterset_class=IndicadorFilter, filterset_fields=[],
            ordering_fields=['anio', 'tipo', 'valor'], search_fields=[])
    def indicadores(self, request, codigo_iso=None):
        queryset = self.filter_queryset(IndicadorEconomico.objects.filter(pais=self.get_country()))
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(IndicadorSerializer(page, many=True).data)

    @extend_schema(responses=CambioSerializer(many=True), parameters=[OpenApiParameter('codigo_iso', str, OpenApiParameter.PATH)])
    @action(detail=True, methods=['get'], queryset=TipoCambio.objects.all(), url_path='tipo-cambio', filterset_class=CambioFilter, filterset_fields=[],
            ordering_fields=['fecha', 'tasa'], search_fields=[])
    def tipo_cambio(self, request, codigo_iso=None):
        queryset = self.filter_queryset(TipoCambio.objects.filter(moneda_origen=self.get_country().moneda, moneda_destino='USD'))
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(CambioSerializer(page, many=True).data)

    @extend_schema(request=None, responses=SyncReportSerializer)
    @action(detail=False, methods=['post'], url_path='sync-indicadores', permission_classes=[EsAdmin])
    def sync_indicadores(self, request):
        return Response(sync_indicators())

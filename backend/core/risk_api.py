import django_filters
from django.db.models import OuterRef, Subquery, Q, Exists, Case, When, F, BooleanField, Count
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_field, OpenApiParameter

from .models import Pais, IndiceRiesgo, Alerta, LecturaAlerta
from .permissions import EsAdmin
from .services.risk import recalculate
from .audit import audit
from .idempotency import idempotent
from .services.numbers import quantize


def latest_risks():
    latest = IndiceRiesgo.objects.filter(pais_id=OuterRef('pais_id')).order_by('-fecha_calculo', '-pk').values('pk')[:1]
    return IndiceRiesgo.objects.filter(pk=Subquery(latest), pais__activo=True).select_related('pais')


class RiesgoSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.CharField(source='pais.nombre', read_only=True)
    variacion = serializers.SerializerMethodField()
    tendencia = serializers.SerializerMethodField()

    class Meta:
        model = IndiceRiesgo
        fields = '__all__'

    @extend_schema_field(serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True))
    def get_variacion(self, obj):
        previous = IndiceRiesgo.objects.filter(pais_id=obj.pais_id).filter(
            Q(fecha_calculo__lt=obj.fecha_calculo) | Q(fecha_calculo=obj.fecha_calculo, pk__lt=obj.pk)).first()
        return str(quantize(obj.indice_compuesto-previous.indice_compuesto)) if previous else None

    def get_tendencia(self, obj) -> str:
        delta = self.get_variacion(obj)
        if delta is None:
            return 'SIN_HISTORICO'
        from decimal import Decimal
        return 'SUBE' if Decimal(delta) > 0 else 'BAJA' if Decimal(delta) < 0 else 'ESTABLE'


class RiesgoDetailSerializer(RiesgoSerializer):
    historico = serializers.SerializerMethodField()
    historico_url = serializers.SerializerMethodField()

    @extend_schema_field(RiesgoSerializer(many=True))
    def get_historico(self, obj):
        return RiesgoSerializer(IndiceRiesgo.objects.filter(pais_id=obj.pais_id)[:20], many=True).data

    def get_historico_url(self, obj) -> str:
        return f'/api/riesgo/{obj.pais_id}/historico/'


class RiskDateFilter(django_filters.FilterSet):
    fecha_desde = django_filters.DateFilter(field_name='fecha_calculo', lookup_expr='date__gte')
    fecha_hasta = django_filters.DateFilter(field_name='fecha_calculo', lookup_expr='date__lte')

    class Meta:
        model = IndiceRiesgo
        fields = ['fecha_desde', 'fecha_hasta', 'nivel_riesgo']


class RecalculateReportSerializer(serializers.Serializer):
    calculados = serializers.IntegerField()
    existentes = serializers.IntegerField()
    errores = serializers.ListField(child=serializers.DictField())


class RiesgoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IndiceRiesgo.objects.select_related('pais').all()
    serializer_class = RiesgoSerializer
    lookup_field = 'pais_id'
    lookup_url_kwarg = 'codigo_iso'
    filterset_class = RiskDateFilter
    ordering_fields = ['indice_compuesto', 'fecha_calculo', 'pais_id']
    ordering = ['-indice_compuesto', 'pais_id']

    def get_serializer_class(self):
        return RiesgoDetailSerializer if self.action == 'retrieve' else RiesgoSerializer

    def get_queryset(self):
        if self.action == 'historico':
            return super().get_queryset().filter(pais__activo=True)
        return latest_risks()

    @extend_schema(parameters=[OpenApiParameter('codigo_iso', str, OpenApiParameter.PATH)])
    @action(detail=True, methods=['get'])
    def historico(self, request, codigo_iso=None):
        get_object_or_404(Pais.objects.all(), pk=codigo_iso)
        records = self.filter_queryset(self.get_queryset().filter(pais_id=codigo_iso))
        return self.get_paginated_response(self.get_serializer(self.paginate_queryset(records), many=True).data)

    @extend_schema(request=None, responses=RecalculateReportSerializer, parameters=[])
    @action(detail=False, methods=['post'], permission_classes=[EsAdmin])
    @idempotent
    def calcular(self, request):
        return Response(recalculate())


def user_alerts(user):
    read = LecturaAlerta.objects.filter(alerta_id=OuterRef('pk'), usuario=user)
    return Alerta.objects.filter(Q(usuario=user) | Q(usuario__isnull=True), pais__activo=True).annotate(
        leida_usuario=Case(When(usuario__isnull=True, then=Exists(read)), default=F('leida'), output_field=BooleanField()))


class AlertaSerializer(serializers.ModelSerializer):
    leida = serializers.BooleanField(source='leida_usuario', read_only=True)

    class Meta:
        model = Alerta
        fields = ['id', 'usuario', 'pais', 'tipo_alerta', 'severidad', 'titulo', 'mensaje', 'leida', 'fecha_creacion']


class AlertaFilter(django_filters.FilterSet):
    leida = django_filters.BooleanFilter(field_name='leida_usuario')
    tipo = django_filters.CharFilter(field_name='tipo_alerta')

    class Meta:
        model = Alerta
        fields = ['leida', 'tipo', 'tipo_alerta', 'severidad']


class MarkedSerializer(serializers.Serializer):
    marcadas = serializers.IntegerField()


class AlertSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    no_leidas = serializers.IntegerField()
    por_tipo = serializers.DictField(child=serializers.IntegerField())
    por_severidad = serializers.DictField(child=serializers.IntegerField())


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    filterset_class = AlertaFilter
    ordering_fields = ['fecha_creacion', 'severidad', 'tipo_alerta']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Alerta.objects.none()
        return user_alerts(self.request.user)

    def mark(self, alert):
        if alert.usuario_id is None:
            _, created = LecturaAlerta.objects.get_or_create(alerta=alert, usuario=self.request.user)
            if created:
                audit(self.request.user, 'EDITAR', alert, {'leida': True})
        elif not alert.leida:
            alert.leida = True
            alert.save(update_fields=['leida'])
            audit(self.request.user, 'EDITAR', alert, {'leida': True})

    @extend_schema(request=None, responses=AlertaSerializer)
    @action(detail=True, methods=['put'])
    @transaction.atomic
    def leer(self, request, pk=None):
        alert = self.get_object()
        self.mark(alert)
        return Response(self.get_serializer(self.get_queryset().get(pk=alert.pk)).data)

    @extend_schema(request=None, responses=MarkedSerializer)
    @action(detail=False, methods=['put'], url_path='leer-todas')
    @transaction.atomic
    def leer_todas(self, request):
        alerts = list(self.get_queryset().filter(leida_usuario=False))
        for alert in alerts:
            self.mark(alert)
        return Response({'marcadas': len(alerts)})

    @extend_schema(responses=AlertSummarySerializer)
    @action(detail=False, methods=['get'])
    def resumen(self, request):
        alerts = self.get_queryset()
        return Response({'total': alerts.count(), 'no_leidas': alerts.filter(leida_usuario=False).count(),
            'por_tipo': {row['tipo_alerta']: row['total'] for row in alerts.order_by().values('tipo_alerta').annotate(total=Count('pk'))},
            'por_severidad': {row['severidad']: row['total'] for row in alerts.order_by().values('severidad').annotate(total=Count('pk'))}})

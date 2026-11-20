import re
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_field,
    OpenApiParameter,
    OpenApiTypes,
)

from .models import Portafolio, Posicion
from .permissions import PuedeEditarPortafolio
from .services import portfolios as domain
from .services.pdf_report import portfolio_pdf
from .audit import audit
from .api import ErrorResponseSerializer

IF_MATCH_PARAMETER = OpenApiParameter(
    "If-Match",
    str,
    OpenApiParameter.HEADER,
    required=True,
    pattern=r'^"[1-9][0-9]*"$',
    description='ETag fuerte de la versión actual del portafolio padre; por ejemplo: "2". No se lee versión del body DELETE.',
)


class PositionSerializer(serializers.ModelSerializer):
    eliminacion_hasta = serializers.SerializerMethodField()
    puede_eliminar = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_eliminacion_hasta(self, obj):
        return domain.correction_deadline(obj)

    def get_puede_eliminar(self, obj) -> bool:
        return domain.can_correct(obj)
    class Meta:
        model = Posicion
        fields = [
            "id",
            "portafolio",
            "pais",
            "tipo_activo",
            "monto_inversion_usd",
            "fecha_entrada",
            "fecha_salida",
            "notas",
            "fecha_creacion", "eliminacion_hasta", "puede_eliminar",
        ]
        read_only_fields = ["id", "portafolio", "fecha_salida", "fecha_creacion"]

    def validate_fecha_entrada(self, value):
        from django.utils import timezone

        if value > timezone.now().date():
            raise serializers.ValidationError("La entrada no puede ser futura.")
        return value


class PositionWriteSerializer(PositionSerializer):
    version = serializers.IntegerField(min_value=1, write_only=True)

    class Meta(PositionSerializer.Meta):
        fields = PositionSerializer.Meta.fields + ["version"]


class VersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1, max_value=2147483647)


def delete_version(request):
    value = request.headers.get("If-Match", "")
    match = re.fullmatch(r'"([1-9][0-9]*)"', value)
    if match is None:
        raise serializers.ValidationError(
            {"If-Match": 'Envía la versión vigente entre comillas, por ejemplo: "2".'}
        )
    serializer = VersionSerializer(data={"version": match.group(1)})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data["version"]


class DistributionSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    monto_usd = serializers.DecimalField(max_digits=16, decimal_places=2)
    porcentaje = serializers.DecimalField(max_digits=7, decimal_places=2)


class PortfolioSummarySerializer(serializers.Serializer):
    total_invertido_usd = serializers.DecimalField(max_digits=16, decimal_places=2)
    posiciones_activas = serializers.IntegerField()
    por_pais = DistributionSerializer(many=True)
    por_tipo_activo = DistributionSerializer(many=True)
    riesgo_promedio_ponderado = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    monto_con_riesgo_usd = serializers.DecimalField(max_digits=16, decimal_places=2)
    paises_con_datos_faltantes = serializers.ListField(child=serializers.CharField())
    version = serializers.IntegerField()


class PortfolioSerializer(serializers.ModelSerializer):
    version = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = Portafolio
        fields = [
            "id",
            "nombre",
            "descripcion",
            "usuario",
            "es_publico",
            "activo",
            "fecha_creacion",
            "fecha_modificacion",
            "version",
        ]
        read_only_fields = [
            "id",
            "usuario",
            "activo",
            "fecha_creacion",
            "fecha_modificacion",
        ]
        validators = []

    def validate_nombre(self, value):
        owner = self.instance.usuario if self.instance else self.context["request"].user
        query = Portafolio.todos.filter(usuario=owner, nombre=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError(
                "Ya existe un portafolio con este nombre para el usuario."
            )
        return value

    def validate(self, attrs):
        if self.instance and "version" not in attrs:
            raise serializers.ValidationError(
                {"version": "Envía la versión actual del portafolio."}
            )
        return attrs


class PortfolioDetailSerializer(PortfolioSerializer):
    posiciones = PositionSerializer(many=True, read_only=True)
    metricas = serializers.SerializerMethodField()

    class Meta(PortfolioSerializer.Meta):
        fields = PortfolioSerializer.Meta.fields + ["posiciones", "metricas"]

    @extend_schema_field(PortfolioSummarySerializer)
    def get_metricas(self, obj):
        return domain.portfolio_summary(obj)


class AvailabilitySerializer(serializers.Serializer):
    disponible = serializers.BooleanField()


class AvailabilityQuerySerializer(serializers.Serializer):
    nombre = serializers.CharField(min_length=3, max_length=100)
    excluir_id = serializers.IntegerField(min_value=1, required=False)


class PortafolioViewSet(viewsets.ModelViewSet):
    queryset = Portafolio.objects.all()
    serializer_class = PortfolioSerializer
    permission_classes = [PuedeEditarPortafolio]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["nombre", "fecha_creacion", "fecha_modificacion"]
    filterset_fields = ["es_publico"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Portafolio.objects.none()
        records = Portafolio.objects.select_related("usuario").all()
        if self.request.user.rol != "ADMIN":
            records = records.filter(Q(usuario=self.request.user) | Q(es_publico=True))
        return records

    def get_serializer_class(self):
        return (
            PortfolioDetailSerializer
            if self.action == "retrieve"
            else super().get_serializer_class()
        )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response["ETag"] = f'"{response.data["version"]}"'
        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("version", None)
        portfolio = domain.create_portfolio(request.user, data)
        return Response(
            self.get_serializer(portfolio).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        portfolio = self.get_object()
        serializer = self.get_serializer(portfolio, data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        version = data.pop("version")
        portfolio = domain.update_portfolio(request.user, portfolio.pk, version, data)
        return Response(self.get_serializer(portfolio).data)

    @extend_schema(
        request=None,
        parameters=[IF_MATCH_PARAMETER,
            OpenApiParameter('motivo', str, OpenApiParameter.QUERY, enum=['ARCHIVO', 'ERROR_CREACION', 'DUPLICADO', 'DESISTIMIENTO'])],
        responses={
            204: None,
            400: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
    )
    def destroy(self, request, *args, **kwargs):
        portfolio = self.get_object()
        domain.delete_portfolio(request.user, portfolio.pk, delete_version(request), request.query_params.get('motivo', 'ARCHIVO'))
        return Response(status=204)

    @extend_schema(request=PositionWriteSerializer, responses={201: PositionSerializer})
    @action(detail=True, methods=["post"])
    def posiciones(self, request, pk=None):
        portfolio = self.get_object()
        serializer = PositionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        version = data.pop("version")
        result = domain.add_position(request.user, portfolio.pk, version, data)
        return Response(PositionSerializer(result).data, status=201)

    @extend_schema(
        methods=["PUT"],
        request=PositionWriteSerializer,
        responses={200: PositionSerializer, 400: ErrorResponseSerializer},
        parameters=[OpenApiParameter("posicion_id", int, OpenApiParameter.PATH)],
    )
    @extend_schema(
        methods=["DELETE"],
        request=None,
        operation_id="portafolios_posiciones_destroy",
        responses={
            200: PositionSerializer,
            400: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
        parameters=[
            OpenApiParameter("posicion_id", int, OpenApiParameter.PATH),
            IF_MATCH_PARAMETER,
        ],
    )
    @action(
        detail=True,
        methods=["put", "delete"],
        url_path=r"posiciones/(?P<posicion_id>\d+)",
    )
    def posicion(self, request, pk=None, posicion_id=None):
        portfolio = self.get_object()
        if request.method == "DELETE":
            result = domain.close_position(
                request.user, portfolio.pk, posicion_id, delete_version(request)
            )
        else:
            serializer = PositionWriteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            version = data.pop("version")
            result = domain.edit_position(
                request.user, portfolio.pk, posicion_id, version, data
            )
        return Response(PositionSerializer(result).data)

    @extend_schema(
        methods=["DELETE"],
        request=None,
        operation_id="portafolios_posiciones_eliminar",
        responses={
            204: None,
            400: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
        parameters=[
            OpenApiParameter("posicion_id", int, OpenApiParameter.PATH),
            IF_MATCH_PARAMETER,
            OpenApiParameter('motivo', str, OpenApiParameter.QUERY, required=True, enum=['ERROR_CREACION', 'DUPLICADO']),
        ],
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"posiciones/(?P<posicion_id>\d+)/eliminar",
    )
    def eliminar_posicion(self, request, pk=None, posicion_id=None):
        portfolio = self.get_object()
        domain.delete_position(
            request.user, portfolio.pk, posicion_id, delete_version(request), request.query_params.get('motivo')
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses=PortfolioSummarySerializer)
    @action(detail=True, methods=["get"])
    def resumen(self, request, pk=None):
        portfolio = self.get_object()
        response = Response(domain.portfolio_summary(portfolio))
        response["ETag"] = f'"{portfolio.version}"'
        return response

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"], url_path="export/pdf")
    def export_pdf(self, request, pk=None):
        portfolio = self.get_object()
        content = portfolio_pdf(portfolio)
        audit(request.user, "EXPORT", portfolio)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="portafolio-{portfolio.pk}.pdf"'
        )
        return response

    @extend_schema(
        parameters=[AvailabilityQuerySerializer], responses=AvailabilitySerializer
    )
    @action(detail=False, methods=["get"], url_path="nombre-disponible")
    def nombre_disponible(self, request):
        serializer = AvailabilityQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        owner = request.user
        if "excluir_id" in serializer.validated_data:
            target = get_object_or_404(
                self.get_queryset(), pk=serializer.validated_data["excluir_id"]
            )
            domain.check_writer(request.user, target)
            owner = target.usuario
        records = Portafolio.todos.filter(
            usuario=owner, nombre=serializer.validated_data["nombre"]
        )
        if "excluir_id" in serializer.validated_data:
            records = records.exclude(pk=serializer.validated_data["excluir_id"])
        return Response({"disponible": not records.exists()})

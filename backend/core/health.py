from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes, authentication_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.cache import cache
from django.db import connection, DatabaseError
from core.api import ErrorResponseSerializer


class HealthSerializer(serializers.Serializer):
    pass


class ReadySerializer(serializers.Serializer):
    status = serializers.CharField()


@extend_schema(responses=HealthSerializer, auth=[])
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    return Response({})


@extend_schema(responses={200: ReadySerializer, 503: ErrorResponseSerializer}, auth=[])
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        cache.get('__readiness__')
    except (DatabaseError, OSError):
        return Response({'error': {'code': 'not_ready',
            'message': 'Servicio temporalmente no disponible.', 'details': {}}},
            status=503, headers={'Cache-Control': 'no-store'})
    return Response({'status': 'ready'}, headers={'Cache-Control': 'no-store'})

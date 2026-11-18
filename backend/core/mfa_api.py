import base64
import io
import json
import secrets
import hashlib
from urllib.parse import quote, urlencode
import qrcode
from django.db import transaction
from rest_framework import generics, serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from drf_spectacular.utils import extend_schema
from core.permissions import EsAdmin
from core.models import Usuario
from core.audit import audit
from core.services.crypto import encrypt
from core.services.mfa import verify_totp, verify_login


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=128, trim_whitespace=False)


class LoginCodeSerializer(CodeSerializer):
    mfa_token = serializers.CharField(max_length=2048, trim_whitespace=False)


class EnrollmentSerializer(serializers.Serializer):
    otpauth_url = serializers.CharField()
    qr = serializers.CharField()


class RecoverySerializer(serializers.Serializer):
    recovery_codes = serializers.ListField(child=serializers.CharField())


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class MFAEnrollView(generics.GenericAPIView):
    permission_classes = [EsAdmin]
    throttle_scope = 'mfa_verify'
    serializer_class = EnrollmentSerializer

    @extend_schema(request=None, responses=EnrollmentSerializer)
    @transaction.atomic
    def post(self, request):
        user = Usuario.objects.select_for_update().get(pk=request.user.pk)
        if user.mfa_enabled:
            raise ValidationError('MFA ya está habilitado. Desactívalo con el factor actual antes de reenrolar.')
        secret = base64.b32encode(secrets.token_bytes(20)).decode()
        user.mfa_secret_enc, user.mfa_last_t = encrypt(secret), -1
        user.save(update_fields=['mfa_secret_enc', 'mfa_last_t'])
        uri = f"otpauth://totp/{quote('DataPulse:' + user.email, safe='')}?{urlencode({'secret': secret, 'issuer': 'DataPulse', 'digits': 6, 'period': 30})}"
        buffer = io.BytesIO()
        qrcode.make(uri).save(buffer, format='PNG')
        audit(user, 'MFA_ENROLL', user)
        return Response({'otpauth_url': uri, 'qr': 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()})


class MFAVerifyView(generics.GenericAPIView):
    permission_classes = [EsAdmin]
    throttle_scope = 'mfa_verify'
    serializer_class = CodeSerializer

    @extend_schema(responses=RecoverySerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failed = False
        with transaction.atomic():
            user = Usuario.objects.select_for_update().get(pk=request.user.pk)
            if user.mfa_enabled:
                raise ValidationError('MFA ya está habilitado.')
            if not verify_totp(user, serializer.validated_data['code']):
                audit(user, 'MFA_VERIFY_FAIL', user)
                failed = True
            else:
                codes = [secrets.token_hex(16) for _ in range(10)]
                user.recovery_codes_enc = encrypt(json.dumps([hashlib.sha256(code.encode()).hexdigest() for code in codes]))
                user.mfa_enabled = True
                user.mfa_epoch += 1
                user.save(update_fields=['mfa_enabled', 'recovery_codes_enc', 'mfa_epoch'])
                # Sessions issued before enrollment must not bypass the new factor.
                for token in OutstandingToken.objects.filter(user=user):
                    BlacklistedToken.objects.get_or_create(token=token)
                audit(user, 'MFA_VERIFY_OK', user)
        if failed:
            raise AuthenticationFailed()
        return Response({'recovery_codes': codes})


class MFADisableView(generics.GenericAPIView):
    permission_classes = [EsAdmin]
    throttle_scope = 'mfa_verify'
    serializer_class = CodeSerializer

    @extend_schema(responses={204: None})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failed = False
        with transaction.atomic():
            user = Usuario.objects.select_for_update().get(pk=request.user.pk)
            if not user.mfa_enabled or not verify_totp(user, serializer.validated_data['code']):
                audit(user, 'MFA_VERIFY_FAIL', user)
                failed = True
            else:
                user.mfa_enabled, user.mfa_secret_enc, user.recovery_codes_enc = False, '', ''
                user.mfa_epoch += 1
                user.save(update_fields=['mfa_enabled', 'mfa_secret_enc', 'recovery_codes_enc', 'mfa_epoch'])
                audit(user, 'MFA_DISABLE', user)
        if failed:
            raise AuthenticationFailed()
        return Response(status=204)


class MFALoginView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'mfa_verify'
    serializer_class = LoginCodeSerializer

    def get_authenticate_header(self, request):
        return 'Bearer'

    @extend_schema(responses=TokenResponseSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(verify_login(**{'token': serializer.validated_data['mfa_token'], 'code': serializer.validated_data['code']}))

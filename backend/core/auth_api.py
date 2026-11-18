from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from rest_framework import generics, serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenObtainSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from core.audit import audit
from core.models import Usuario
from core.security_auth import check_captcha
from core.services.mfa import challenge


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'nombre_completo', 'rol', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'rol', 'activo', 'fecha_creacion']

    def validate(self, attrs):
        blocked = {'rol', 'activo', 'is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions'} & set(self.initial_data)
        if blocked:
            import logging
            from core.observability import request_ip
            logging.getLogger('datapulse').warning('privilege_escalation_attempt', extra={
                'usuario_id': self.instance.pk if self.instance else None, 'ip': request_ip.get(),
                'path': '/api/auth/me/' if self.instance else '/api/auth/register/'})
            raise serializers.ValidationError({key: 'Este campo no puede modificarse.' for key in blocked})
        return attrs

    def validate_email(self, value):
        value = value.strip().lower()
        query = Usuario.objects.filter(email__iexact=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError('Ya existe un usuario con este email.')
        return value


class RegisterSerializer(ProfileSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    captcha_key = serializers.CharField(write_only=True, required=False)
    captcha_answer = serializers.CharField(write_only=True, required=False)

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + ['password', 'captcha_key', 'captcha_answer']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        check_captcha(attrs)
        attrs.pop('captcha_key', None)
        attrs.pop('captcha_answer', None)
        validate_password(attrs['password'], Usuario(email=attrs.get('email', ''), nombre_completo=attrs.get('nombre_completo', '')))
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = Usuario.objects.create_user(**validated_data)
        audit(user, 'CREAR', user)
        return user


class RegisterView(generics.CreateAPIView):
    throttle_scope = 'register'
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    http_method_names = ['get', 'put', 'head', 'options']

    def get_object(self):
        return self.request.user

    @transaction.atomic
    def perform_update(self, serializer):
        user = serializer.save()
        audit(user, 'EDITAR', user)


class LoginSerializer(TokenObtainPairSerializer):
    captcha_key = serializers.CharField(write_only=True, required=False)
    captcha_answer = serializers.CharField(write_only=True, required=False)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['mfa_epoch'] = user.mfa_epoch
        return token

    def validate(self, attrs):
        attrs['email'] = attrs['email'].strip().lower()
        try:
            TokenObtainSerializer.validate(self, attrs)
        except AuthenticationFailed:
            self.context['request']._request._login_failed_this_request = True
            audit(None, 'LOGIN_FALLIDO', Usuario(pk=''), {'email': attrs['email']})
            raise
        user_logged_in.send(sender=Usuario, request=self.context['request'], user=self.user)
        audit(self.user, 'LOGIN', self.user)
        if self.user.rol == 'ADMIN' and self.user.mfa_enabled:
            return challenge(self.user)
        refresh = self.get_token(self.user)
        return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class LoginTokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class MFAPendingSerializer(serializers.Serializer):
    mfa_required = serializers.BooleanField()
    mfa_token = serializers.CharField()


@extend_schema(responses=PolymorphicProxySerializer(component_name='LoginResponse',
    serializers=[LoginTokensSerializer, MFAPendingSerializer], resource_type_field_name=None))
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_scope = 'login'


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer

    @extend_schema(responses={204: None})
    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = Usuario.objects.select_for_update().get(pk=request.user.pk)
        if not user.check_password(serializer.validated_data['current_password']):
            raise AuthenticationFailed()
        validate_password(serializer.validated_data['new_password'], user)
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        audit(user, 'PASSWORD_CHANGE', user)
        return Response(status=204)

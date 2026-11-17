from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from core.audit import audit
from core.models import Usuario


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'nombre_completo', 'rol', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'rol', 'activo', 'fecha_creacion']

    def validate(self, attrs):
        blocked = {'rol', 'activo', 'is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions'} & set(self.initial_data)
        if blocked:
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

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + ['password']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        validate_password(attrs['password'], Usuario(email=attrs.get('email', ''), nombre_completo=attrs.get('nombre_completo', '')))
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = Usuario.objects.create_user(**validated_data)
        audit(user, 'CREAR', user)
        return user


class RegisterView(generics.CreateAPIView):
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
    def validate(self, attrs):
        attrs['email'] = attrs['email'].strip().lower()
        result = super().validate(attrs)
        audit(self.user, 'LOGIN', self.user)
        return result


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

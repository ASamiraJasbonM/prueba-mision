from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ActiveJWTScheme(OpenApiAuthenticationExtension):
    target_class = 'core.authentication.ActiveJWTAuthentication'
    name = 'jwtAuth'

    def get_security_definition(self, auto_schema):
        return {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}


def active_user(user):
    return user is not None and user.is_active and user.activo


class ActiveJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not active_user(user):
            raise AuthenticationFailed('El usuario está inactivo.')
        return user

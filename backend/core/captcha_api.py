from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema


class CaptchaSerializer(serializers.Serializer):
    captcha_key = serializers.CharField()
    image_url = serializers.CharField()


class CaptchaView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CaptchaSerializer

    @extend_schema(responses=CaptchaSerializer)
    def get(self, request):
        CaptchaStore.remove_expired()
        key = CaptchaStore.generate_key()
        return Response({'captcha_key': key, 'image_url': captcha_image_url(key)})

from cryptography.fernet import Fernet
from django.conf import settings


def encrypt(value, key=None):
    return Fernet((key or settings.FIELD_ENCRYPTION_KEY).encode()).encrypt(value.encode()).decode()


def decrypt(value, key=None):
    return Fernet((key or settings.FIELD_ENCRYPTION_KEY).encode()).decrypt(value.encode()).decode()

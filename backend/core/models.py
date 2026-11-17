from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('El email es obligatorio.')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('rol', 'ADMIN')
        if not extra['is_staff'] or not extra['is_superuser'] or extra['rol'] != 'ADMIN':
            raise ValueError('Un superusuario requiere permisos ADMIN.')
        return self.create_user(email, password, **extra)


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        ANALISTA = 'ANALISTA', 'Analista'
        VIEWER = 'VIEWER', 'Consulta'

    username = None
    email = models.EmailField(unique=True)
    nombre_completo = models.CharField(max_length=200)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.ANALISTA)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre_completo']
    objects = UsuarioManager()

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='usuario_email_ci_unique')]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


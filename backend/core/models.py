from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from decimal import Decimal


class ActivoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class ActivoModel(models.Model):
    activo = models.BooleanField(default=True)
    objects = ActivoManager()
    todos = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = 'todos'


class Moneda(models.Model):
    codigo = models.CharField(max_length=3, primary_key=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.codigo


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
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret_enc = models.TextField(blank=True)
    recovery_codes_enc = models.TextField(blank=True)
    mfa_last_t = models.BigIntegerField(default=-1)
    mfa_epoch = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='usuario_email_ci_unique')]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Pais(ActivoModel):
    class Region(models.TextChoices):
        ANDINA = 'ANDINA', 'Andina'
        CONO_SUR = 'CONO_SUR', 'Cono sur'
        CENTROAMERICA = 'CENTROAMERICA', 'Centroamérica'
        CARIBE = 'CARIBE', 'Caribe'

    codigo_iso = models.CharField(max_length=2, primary_key=True)
    nombre = models.CharField(max_length=150, db_index=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='paises')
    region = models.CharField(max_length=15, choices=Region.choices, db_index=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    poblacion = models.PositiveBigIntegerField(default=0)
    bandera_url = models.URLField(blank=True)

    @property
    def moneda_codigo(self):
        return self.moneda_id

    @property
    def moneda_nombre(self):
        return self.moneda.nombre

    def __str__(self):
        return self.nombre


class IndicadorEconomico(models.Model):
    class Tipo(models.TextChoices):
        PIB = 'PIB', 'PIB'
        INFLACION = 'INFLACION', 'Inflación'
        DESEMPLEO = 'DESEMPLEO', 'Desempleo'
        BALANZA_COMERCIAL = 'BALANZA_COMERCIAL', 'Balanza comercial'
        DEUDA_PIB = 'DEUDA_PIB', 'Deuda/PIB'
        PIB_PERCAPITA = 'PIB_PERCAPITA', 'PIB per cápita'

    class Unidad(models.TextChoices):
        PORCENTAJE = 'PORCENTAJE', 'Porcentaje'
        USD = 'USD', 'USD'
        USD_MILES_MILLONES = 'USD_MILES_MILLONES', 'Miles de millones USD'

    class Fuente(models.TextChoices):
        WORLD_BANK = 'WORLD_BANK', 'World Bank'
        MANUAL = 'MANUAL', 'Manual'

    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='indicadores')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=28, decimal_places=6)
    unidad = models.CharField(max_length=20, choices=Unidad.choices)
    anio = models.PositiveSmallIntegerField()
    fuente = models.CharField(max_length=12, choices=Fuente.choices, default=Fuente.MANUAL)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['pais', 'tipo', 'anio'], name='indicador_natural_unique')]
        indexes = [models.Index(fields=['pais', 'tipo', 'anio'], name='indicador_pais_tipo_anio')]
        ordering = ['pais_id', 'tipo', '-anio']


class TipoCambio(models.Model):
    moneda_origen = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='tasas')
    moneda_destino = models.CharField(max_length=3, default='USD')
    tasa = models.DecimalField(max_digits=24, decimal_places=12, validators=[MinValueValidator(Decimal('0.000000000001'))])
    fecha = models.DateField()
    variacion_porcentual = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fuente = models.CharField(max_length=100, default='EXCHANGE_RATE_API')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['moneda_origen', 'moneda_destino', 'fecha'], name='cambio_natural_unique'),
            models.CheckConstraint(condition=models.Q(tasa__gt=0), name='cambio_tasa_positiva'),
        ]
        indexes = [models.Index(fields=['moneda_origen', 'moneda_destino', 'fecha'], name='cambio_moneda_fecha')]
        ordering = ['-fecha', 'pk']


class Portafolio(ActivoModel):
    nombre = models.CharField(max_length=100, validators=[MinLengthValidator(3)])
    descripcion = models.CharField(max_length=500, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='portafolios')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_modificacion = models.DateTimeField(default=timezone.now)
    es_publico = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'nombre'], name='portafolio_usuario_nombre_unique')]
        indexes = [models.Index(fields=['usuario', 'activo'], name='portafolio_usuario_activo')]
        ordering = ['-fecha_creacion', 'pk']


class Posicion(models.Model):
    class TipoActivo(models.TextChoices):
        RENTA_FIJA = 'RENTA_FIJA', 'Renta fija'
        RENTA_VARIABLE = 'RENTA_VARIABLE', 'Renta variable'
        COMMODITIES = 'COMMODITIES', 'Commodities'
        MONEDA = 'MONEDA', 'Moneda'

    portafolio = models.ForeignKey(Portafolio, on_delete=models.PROTECT, related_name='posiciones')
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='posiciones')
    tipo_activo = models.CharField(max_length=15, choices=TipoActivo.choices)
    monto_inversion_usd = models.DecimalField(max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('1000')), MaxValueValidator(Decimal('10000000'))])
    fecha_entrada = models.DateField()
    fecha_salida = models.DateField(null=True, blank=True)
    notas = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(fecha_salida__isnull=True) | models.Q(fecha_salida__gt=models.F('fecha_entrada')), name='posicion_salida_posterior'),
            models.CheckConstraint(condition=models.Q(monto_inversion_usd__gte=1000, monto_inversion_usd__lte=10000000), name='posicion_monto_limites'),
        ]
        indexes = [models.Index(fields=['portafolio', 'fecha_salida'], name='posicion_portafolio_salida')]
        ordering = ['-fecha_entrada', 'pk']

    def clean(self):
        super().clean()
        if self.fecha_salida and self.fecha_entrada and self.fecha_salida <= self.fecha_entrada:
            raise ValidationError({'fecha_salida': 'La salida debe ser posterior a la entrada.'})
        if self.fecha_entrada and self.fecha_entrada > timezone.now().date():
            raise ValidationError({'fecha_entrada': 'La entrada no puede ser futura.'})


class IndiceRiesgo(models.Model):
    class Nivel(models.TextChoices):
        BAJO = 'BAJO', 'Bajo'
        MODERADO = 'MODERADO', 'Moderado'
        ALTO = 'ALTO', 'Alto'
        CRITICO = 'CRITICO', 'Crítico'

    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='riesgos')
    fecha_calculo = models.DateTimeField(default=timezone.now)
    score_economico = models.DecimalField(max_digits=5, decimal_places=2)
    score_cambiario = models.DecimalField(max_digits=5, decimal_places=2)
    score_estabilidad = models.DecimalField(max_digits=5, decimal_places=2)
    indice_compuesto = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_riesgo = models.CharField(max_length=10, choices=Nivel.choices)
    detalle_calculo = models.JSONField(default=dict)
    clave_calculo = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(**{f'{f}__gte': 0, f'{f}__lte': 100}), name=f'{f}_rango')
                       for f in ['indice_compuesto', 'score_economico', 'score_cambiario', 'score_estabilidad']]
        indexes = [models.Index(fields=['pais', '-fecha_calculo'], name='riesgo_pais_fecha')]
        ordering = ['-fecha_calculo', '-pk']

    def clean(self):
        super().clean()
        for field in ['indice_compuesto', 'score_economico', 'score_cambiario', 'score_estabilidad']:
            value = getattr(self, field)
            if value is not None and not Decimal('0') <= Decimal(str(value)) <= Decimal('100'):
                raise ValidationError({field: 'El score debe estar entre 0 y 100.'})


class Alerta(models.Model):
    class Tipo(models.TextChoices):
        RIESGO = 'RIESGO', 'Riesgo'
        TIPO_CAMBIO = 'TIPO_CAMBIO', 'Tipo de cambio'
        INDICADOR = 'INDICADOR', 'Indicador'

    class Severidad(models.TextChoices):
        INFO = 'INFO', 'Información'
        WARNING = 'WARNING', 'Advertencia'
        CRITICAL = 'CRITICAL', 'Crítica'

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='alertas', null=True, blank=True)
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='alertas')
    tipo_alerta = models.CharField(max_length=12, choices=Tipo.choices)
    severidad = models.CharField(max_length=8, choices=Severidad.choices)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    clave_evento = models.CharField(max_length=200, unique=True, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['usuario', 'leida'], name='alerta_usuario_leida')]
        ordering = ['-fecha_creacion', '-pk']


class LecturaAlerta(models.Model):
    alerta = models.ForeignKey(Alerta, on_delete=models.CASCADE, related_name='lecturas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='lecturas_alertas')
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['alerta', 'usuario'], name='lectura_alerta_usuario_unique')]


class LogActividad(models.Model):
    class Accion(models.TextChoices):
        CREAR = 'CREAR', 'Crear'
        EDITAR = 'EDITAR', 'Editar'
        ELIMINAR = 'ELIMINAR', 'Eliminar'
        CONSULTAR = 'CONSULTAR', 'Consultar'
        LOGIN = 'LOGIN', 'Login'
        EXPORT = 'EXPORT', 'Exportar'
        LOGIN_FALLIDO = 'LOGIN_FALLIDO', 'Login fallido'
        LOGIN_BLOQUEADO = 'LOGIN_BLOQUEADO', 'Login bloqueado'
        PASSWORD_CHANGE = 'PASSWORD_CHANGE', 'Cambio de contraseña'
        MFA_ENROLL = 'MFA_ENROLL', 'Enrolar MFA'
        MFA_VERIFY_OK = 'MFA_VERIFY_OK', 'Verificación MFA correcta'
        MFA_VERIFY_FAIL = 'MFA_VERIFY_FAIL', 'Verificación MFA fallida'
        MFA_DISABLE = 'MFA_DISABLE', 'Deshabilitar MFA'
        CORRECCION = 'CORRECCION', 'Corrección de auditoría'

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='actividades', null=True, blank=True)
    accion = models.CharField(max_length=32, choices=Accion.choices)
    entidad_afectada = models.CharField(max_length=100)
    entidad_id = models.CharField(max_length=100)
    detalle = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    hash_anterior = models.CharField(max_length=64, null=True, blank=True)
    hash_actual = models.CharField(max_length=64, unique=True)
    firma_hmac = models.CharField(max_length=64)

    class Meta:
        ordering = ['-fecha', '-pk']


class AuditHead(models.Model):
    """Singleton used to serialize appends, including an initially empty chain."""
    hash_actual = models.CharField(max_length=64, default='', blank=True)


class IdempotentRequest(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    path = models.CharField(max_length=100)
    key = models.CharField(max_length=128)
    body_hash = models.CharField(max_length=64)
    response = models.JSONField()
    expires = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'path', 'key'], name='idempotency_user_path_key')]


class MFALoginChallenge(models.Model):
    digest = models.CharField(max_length=64, primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    expires = models.DateTimeField()
    used = models.BooleanField(default=False)


"""
Usuarios, roles, permisos y recuperación de contraseña.

Un usuario tiene un rol. El rol define qué puede hacer (permisos por módulo y
acción) y sobre qué delegaciones (alcance). Las delegaciones autorizadas de
un usuario con alcance por delegación son las que tiene asignadas.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from catalogos.models import Catalogo, Delegacion, validador_codigo

from .modulos import ACCIONES, NOMBRES


class Permiso(models.Model):
    modulo = models.CharField('módulo', max_length=30)
    accion = models.CharField('acción', max_length=10, choices=ACCIONES)

    class Meta:
        verbose_name = 'permiso'
        ordering = ['modulo', 'accion']
        constraints = [models.UniqueConstraint(fields=['modulo', 'accion'], name='permiso_unico')]

    def __str__(self):
        return f'{NOMBRES.get(self.modulo, self.modulo)} · {self.get_accion_display()}'

    @property
    def codigo(self):
        return f'{self.modulo}.{self.accion}'


class Rol(Catalogo):
    GLOBAL = 'GLOBAL'
    DELEGACION = 'DELEGACION'
    ALCANCES = [
        (GLOBAL, 'Todas las delegaciones'),
        (DELEGACION, 'Delegaciones asignadas'),
    ]

    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('ROL', 2)])
    nombre = models.CharField('nombre', max_length=60, unique=True)
    descripcion = models.CharField('descripción', max_length=200)
    alcance = models.CharField('alcance autorizado', max_length=12, choices=ALCANCES, default=DELEGACION)
    permisos = models.ManyToManyField(Permiso, blank=True, related_name='roles', verbose_name='permisos')
    protegido = models.BooleanField(
        'protegido', default=False,
        help_text='Rol del sistema: no se elimina, no se desactiva y conserva todos sus permisos.')

    class Meta:
        verbose_name = 'rol'
        verbose_name_plural = 'roles'
        ordering = ['codigo']
        constraints = [models.UniqueConstraint(Lower('nombre'), name='rol_nombre_unico_ci')]

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    def create_user(self, nombre_usuario, correo, password=None, **extra):
        if not nombre_usuario or not correo:
            raise ValueError('El usuario necesita nombre de usuario y correo.')
        usuario = self.model(nombre_usuario=nombre_usuario.lower(), correo=self.normalize_email(correo).lower(),
                             **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def por_identificador(self, identificador):
        """Busca por nombre de usuario o por correo, sin distinguir mayúsculas."""
        identificador = (identificador or '').strip()
        return self.filter(
            models.Q(nombre_usuario__iexact=identificador) | models.Q(correo__iexact=identificador)
        ).select_related('rol').first()


class Usuario(AbstractBaseUser):
    nombre_usuario = models.CharField(
        'nombre de usuario', max_length=40, unique=True,
        validators=[RegexValidator(r'^[a-z0-9._-]{3,40}$',
                                   'Use entre 3 y 40 caracteres: minúsculas, números, punto, guion o guion bajo.')])
    correo = models.EmailField('correo', unique=True)
    nombre = models.CharField('nombre completo', max_length=120)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='usuarios', verbose_name='rol')
    delegaciones = models.ManyToManyField(Delegacion, blank=True, related_name='usuarios',
                                          verbose_name='delegaciones autorizadas')
    is_active = models.BooleanField('activo', default=True)
    intentos_fallidos = models.PositiveSmallIntegerField('intentos fallidos', default=0)
    bloqueado_hasta = models.DateTimeField('bloqueado hasta', null=True, blank=True)
    creado = models.DateTimeField('creado', auto_now_add=True)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'nombre_usuario'
    EMAIL_FIELD = 'correo'
    REQUIRED_FIELDS = ['correo', 'nombre']

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def activo(self):
        return self.is_active

    @property
    def estado(self):
        return 'Activo' if self.is_active else 'Inactivo'

    @property
    def lista_delegaciones(self):
        return ', '.join(f'{d.codigo} {d.nombre}' for d in self.delegaciones.all())

    # ----- permisos -----------------------------------------------------
    def permisos_codigos(self):
        if not hasattr(self, '_permisos_cache'):
            if self.rol_id and self.rol.activo:
                self._permisos_cache = {
                    f'{m}.{a}' for m, a in self.rol.permisos.values_list('modulo', 'accion')
                }
            else:
                self._permisos_cache = set()
        return self._permisos_cache

    def tiene_permiso(self, modulo, accion='ver'):
        return self.is_active and f'{modulo}.{accion}' in self.permisos_codigos()

    @property
    def alcance_global(self):
        return bool(self.rol_id) and self.rol.alcance == Rol.GLOBAL

    def delegaciones_autorizadas(self):
        if self.alcance_global:
            return Delegacion.objects.filter(activo=True)
        return self.delegaciones.filter(activo=True)

    # ----- bloqueo por intentos fallidos ---------------------------------
    @property
    def bloqueado(self):
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())

    def registrar_fallo(self):
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= settings.SGR_LOGIN_MAX_INTENTOS:
            self.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.SGR_LOGIN_BLOQUEO_MIN)
            self.intentos_fallidos = 0
        self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])

    def limpiar_fallos(self):
        if self.intentos_fallidos or self.bloqueado_hasta:
            self.intentos_fallidos = 0
            self.bloqueado_hasta = None
            self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])

    @property
    def correo_enmascarado(self):
        return enmascarar_correo(self.correo)


def enmascarar_correo(correo):
    """ana.rojas@example.test -> a***@example.test"""
    usuario, _, dominio = (correo or '').partition('@')
    if not dominio:
        return '***'
    return f'{usuario[:1]}***@{dominio}'


class CodigoRecuperacion(models.Model):
    """
    Código de 6 dígitos para recuperar la contraseña.
    Se guarda como hash: ni la base de datos ni los respaldos lo muestran.
    """

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='codigos_recuperacion')
    codigo_hash = models.CharField(max_length=128)
    creado = models.DateTimeField(default=timezone.now)
    expira = models.DateTimeField()
    intentos = models.PositiveSmallIntegerField(default=0)
    verificado_en = models.DateTimeField(null=True, blank=True)
    usado_en = models.DateTimeField(null=True, blank=True)
    anulado = models.BooleanField(default=False)

    class Meta:
        ordering = ['-creado']

    @classmethod
    def emitir(cls, usuario, codigo):
        ahora = timezone.now()
        cls.objects.filter(usuario=usuario, usado_en__isnull=True, anulado=False).update(anulado=True)
        return cls.objects.create(
            usuario=usuario, codigo_hash=make_password(codigo), creado=ahora,
            expira=ahora + timedelta(minutes=settings.SGR_CODIGO_VIGENCIA_MIN))

    def coincide(self, codigo):
        return check_password(codigo, self.codigo_hash)

    @property
    def vencido(self):
        return timezone.now() >= self.expira

    @property
    def agotado(self):
        return self.intentos >= settings.SGR_CODIGO_MAX_INTENTOS

    @property
    def utilizable(self):
        return not (self.anulado or self.usado_en or self.vencido or self.agotado)

    def segundos_para_reenvio(self):
        disponible = self.creado + timedelta(seconds=settings.SGR_CODIGO_REENVIO_SEG)
        return max(0, int((disponible - timezone.now()).total_seconds()))


class CorreoSaliente(models.Model):
    """Bandeja de correos de prueba: permite demostrar la recuperación sin un servidor SMTP."""

    destinatario = models.EmailField()
    asunto = models.CharField(max_length=200)
    cuerpo = models.TextField()
    enviado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-enviado']
        verbose_name = 'correo de prueba'

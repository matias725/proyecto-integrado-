"""Registro de auditoría (RF-036, RNF-008)."""

from django.conf import settings
from django.db import models


class Auditoria(models.Model):
    EVENTOS = [
        ('ACCESO', 'Inicio de sesión'),
        ('ACCESO_FALLIDO', 'Inicio de sesión fallido'),
        ('SALIDA', 'Cierre de sesión'),
        ('ALTA', 'Alta'),
        ('MODIFICACION', 'Modificación'),
        ('ELIMINACION', 'Eliminación'),
        ('CAMBIO_ESTADO', 'Cambio de estado'),
        ('CAMBIO_CLAVE', 'Cambio de contraseña'),
        ('RECUPERACION', 'Recuperación de contraseña'),
        ('CAMBIO_CONTEXTO', 'Cambio de delegación activa'),
        ('EXPORTACION', 'Exportación'),
        ('ACCESO_DENEGADO', 'Acceso denegado'),
    ]

    fecha = models.DateTimeField('fecha', auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='eventos')
    usuario_texto = models.CharField('usuario', max_length=120, blank=True)
    evento = models.CharField('evento', max_length=20, choices=EVENTOS, db_index=True)
    entidad = models.CharField('entidad', max_length=60)
    registro = models.CharField('registro', max_length=40, blank=True)
    detalle = models.CharField('detalle', max_length=500, blank=True)
    delegacion = models.CharField('delegación activa', max_length=80, blank=True)
    ip = models.GenericIPAddressField('IP', null=True, blank=True)

    class Meta:
        verbose_name = 'evento de auditoría'
        verbose_name_plural = 'auditoría'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.fecha:%d-%m-%Y %H:%M} {self.evento} {self.entidad}'


def registrar(request, evento, entidad, registro='', detalle='', usuario=None):
    """Deja constancia de una operación. Nunca guarda contraseñas ni códigos."""
    usuario = usuario or (request.user if request and request.user.is_authenticated else None)
    delegacion = getattr(request, 'delegacion_activa', None) if request else None
    ip = None
    if request:
        reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
        ip = (reenviada.split(',')[0].strip() or request.META.get('REMOTE_ADDR')) or None
    return Auditoria.objects.create(
        usuario=usuario,
        usuario_texto=usuario.nombre if usuario else '',
        evento=evento,
        entidad=entidad,
        registro=str(registro or '')[:40],
        detalle=str(detalle or '')[:500],
        delegacion=str(delegacion or '')[:80],
        ip=ip,
    )

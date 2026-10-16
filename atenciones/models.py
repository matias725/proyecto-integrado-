"""Solicitantes y atenciones ciudadanas."""

import uuid

from django.conf import settings
from django.db import models

from catalogos.models import Delegacion, SubAtencion, TipoAtencion


class Solicitante(models.Model):
    """Vecino o vecina que solicita una atención. Se identifica por RUT."""

    rut = models.CharField('RUT', max_length=12, unique=True)
    nombre = models.CharField('nombre', max_length=150)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    creado = models.DateTimeField('registrado', auto_now_add=True)

    class Meta:
        verbose_name = 'solicitante'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.rut})'


class Atencion(models.Model):
    solicitante = models.ForeignKey(Solicitante, on_delete=models.PROTECT, related_name='atenciones')
    tipo = models.ForeignKey(TipoAtencion, on_delete=models.PROTECT, related_name='atenciones',
                             verbose_name='tipo de atención')
    subatencion = models.ForeignKey(SubAtencion, on_delete=models.PROTECT, related_name='atenciones',
                                    verbose_name='sub atención')
    descripcion = models.TextField('descripción', max_length=1000)
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name='atenciones',
                                   verbose_name='delegación')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='atenciones', verbose_name='responsable')
    creada = models.DateTimeField('fecha de registro', auto_now_add=True)
    # Identificador del formulario enviado: un segundo envío del mismo
    # formulario no crea un registro duplicado.
    token_envio = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    class Meta:
        verbose_name = 'atención'
        verbose_name_plural = 'atenciones'
        ordering = ['-creada']
        indexes = [models.Index(fields=['delegacion', '-creada'])]

    def __str__(self):
        return self.folio

    @property
    def folio(self):
        anio = self.creada.year if self.creada else ''
        return f'AT-{anio}-{self.pk:06d}' if self.pk else 'AT-nueva'

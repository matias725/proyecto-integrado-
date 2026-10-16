"""
Catálogos del SGR: delegaciones, ítems y metas, tipos y sub atenciones.

Cada catálogo tiene un código legible (DEL01, IT001...), un nombre único y un
estado. Los registros con relaciones no se eliminan: se desactivan.
"""

from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower


class Catalogo(models.Model):
    """Campos comunes a todos los catálogos."""

    activo = models.BooleanField('activo', default=True)
    creado = models.DateTimeField('creado', auto_now_add=True)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    class Meta:
        abstract = True

    @property
    def estado(self):
        return 'Activo' if self.activo else 'Inactivo'


def validador_codigo(prefijo, digitos):
    return RegexValidator(
        rf'^{prefijo}\d{{{digitos}}}$',
        f'Use el formato {prefijo} seguido de {digitos} dígitos, por ejemplo {prefijo}{"1".zfill(digitos)}.')


class Delegacion(Catalogo):
    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('DEL', 2)])
    nombre = models.CharField('nombre', max_length=80, unique=True)
    direccion = models.CharField('dirección', max_length=150)
    comuna = models.CharField('comuna', max_length=60, default='La Serena')

    class Meta:
        verbose_name = 'delegación'
        verbose_name_plural = 'delegaciones'
        ordering = ['codigo']
        constraints = [models.UniqueConstraint(Lower('nombre'), name='delegacion_nombre_unico_ci')]

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    @property
    def nombre_completo(self):
        return f'Delegación {self.nombre}'


class ItemMedicion(Catalogo):
    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('IT', 3)])
    nombre = models.CharField('nombre', max_length=120, unique=True)
    descripcion = models.CharField('descripción', max_length=250)

    class Meta:
        verbose_name = 'ítem'
        verbose_name_plural = 'ítems y metas'
        ordering = ['codigo']
        constraints = [models.UniqueConstraint(Lower('nombre'), name='item_nombre_unico_ci')]

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'


class TipoAtencion(Catalogo):
    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('TA', 3)])
    nombre = models.CharField('nombre', max_length=80, unique=True)
    descripcion = models.CharField('descripción', max_length=250)

    class Meta:
        verbose_name = 'tipo de atención'
        verbose_name_plural = 'tipos de atención'
        ordering = ['codigo']
        constraints = [models.UniqueConstraint(Lower('nombre'), name='tipo_nombre_unico_ci')]

    def __str__(self):
        return self.nombre


class SubAtencion(Catalogo):
    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('SA', 3)])
    nombre = models.CharField('nombre', max_length=100)
    tipo = models.ForeignKey(TipoAtencion, on_delete=models.PROTECT, related_name='subatenciones',
                             verbose_name='tipo de atención')

    class Meta:
        verbose_name = 'sub atención'
        verbose_name_plural = 'sub atenciones'
        ordering = ['codigo']
        constraints = [
            models.UniqueConstraint(Lower('nombre'), 'tipo', name='subatencion_nombre_por_tipo_ci'),
        ]

    def __str__(self):
        return self.nombre

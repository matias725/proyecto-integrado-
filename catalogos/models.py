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


# Comunas de la Región de Coquimbo. La Serena va primero porque es la comuna del municipio
# y queda seleccionada por defecto; se puede elegir otra.
COMUNA_POR_DEFECTO = 'La Serena'
COMUNAS = [
    'La Serena', 'Coquimbo', 'Andacollo', 'La Higuera', 'Paihuano', 'Vicuña',
    'Illapel', 'Canela', 'Los Vilos', 'Salamanca',
    'Ovalle', 'Combarbalá', 'Monte Patria', 'Punitaqui', 'Río Hurtado',
]


class Delegacion(Catalogo):
    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('DEL', 2)])
    nombre = models.CharField('nombre', max_length=80, unique=True)
    direccion = models.CharField('dirección', max_length=150)
    comuna = models.CharField('comuna', max_length=60, default=COMUNA_POR_DEFECTO,
                              choices=[(c, c) for c in COMUNAS])

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


class Sector(Catalogo):
    """
    Parte del territorio de una delegación (barrio, población o localidad), como la columna
    «TERRITORIO» del TUBO de la matriz: Latorre, Toqui... en Las Compañías; La Florida, Ceres... en La Antena.
    """

    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('SEC', 3)])
    nombre = models.CharField('nombre del sector', max_length=80)
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name='sectores',
                                   verbose_name='delegación')
    descripcion = models.CharField('referencia', max_length=200, blank=True,
                                   help_text='Villas, poblaciones o límites que abarca (opcional).')

    class Meta:
        verbose_name = 'sector'
        verbose_name_plural = 'sectores'
        ordering = ['delegacion__codigo', 'nombre']
        constraints = [
            # El mismo nombre puede repetirse en delegaciones distintas, no dentro de una misma
            models.UniqueConstraint(Lower('nombre'), 'delegacion', name='sector_nombre_por_delegacion_ci'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def territorio(self):
        return f'{self.delegacion.nombre} · {self.nombre}'


def texto_territorio(delegacion, sector=None, referencia=''):
    """«Las Compañías · sector Toqui · Pasaje 3»: delegación, sector y referencia, lo que exista."""
    partes = [delegacion.nombre if delegacion else 'Sin delegación']
    if sector:
        partes.append(f'sector {sector.nombre}')
    if referencia:
        partes.append(referencia)
    return ' · '.join(partes)


class ItemMedicion(Catalogo):
    CONTEO = 'CONTEO'
    TUBO = 'TUBO'
    MEDICIONES = [
        (CONTEO, 'Conteo de actividades realizadas'),
        (TUBO, 'Porcentaje de solicitudes del TUBO resueltas'),
    ]

    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('IT', 3)])
    nombre = models.CharField('nombre', max_length=120, unique=True)
    descripcion = models.CharField('descripción', max_length=250)
    medicion = models.CharField(
        'forma de medición', max_length=8, choices=MEDICIONES, default=CONTEO,
        help_text='Conteo: suma una unidad por actividad realizada. TUBO: la meta es un porcentaje (ej. 80) '
                  'de solicitudes del tubo de trabajo resueltas.')

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


class Cargo(Catalogo):
    """Cargo del descriptor de funciones de las delegaciones (año 2026)."""

    codigo = models.CharField('código', max_length=6, unique=True, validators=[validador_codigo('CAR', 2)])
    nombre = models.CharField('nombre', max_length=80, unique=True)
    descripcion = models.CharField('función principal', max_length=300)
    es_delegado = models.BooleanField(
        'es delegado', default=False,
        help_text='El delegado valida actividades y registra felicitaciones, reclamos y ausencias de su equipo.')

    class Meta:
        verbose_name = 'cargo'
        verbose_name_plural = 'cargos'
        ordering = ['codigo']
        constraints = [models.UniqueConstraint(Lower('nombre'), name='cargo_nombre_unico_ci')]

    def __str__(self):
        return self.nombre

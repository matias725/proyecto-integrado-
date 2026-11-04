"""
Matriz SGR: períodos, metas por cargo, organizaciones, actividades (TUBO de
trabajo), evidencias, ausencias (semáforo) y felicitaciones o reclamos.

Reemplaza las hojas Excel de la matriz trimestral de las delegaciones. Cada
hoja repetida por cargo (AP ADM, T OC 1-4, G SOC 1-5…) pasa a ser una fila de
MetaCargo, y cada fila del TUBO pasa a ser una Actividad con su historial.
Las reglas de puntaje del nuevo requerimiento viven en gestion/reglas.py.
"""

import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from catalogos.models import Cargo, Catalogo, Delegacion, ItemMedicion


# ---------------------------------------------------------------------------
# Períodos y metas
# ---------------------------------------------------------------------------
class Periodo(models.Model):
    ABIERTO = 'ABIERTO'
    CERRADO = 'CERRADO'
    ESTADOS = [(ABIERTO, 'Abierto'), (CERRADO, 'Cerrado')]

    nombre = models.CharField('nombre', max_length=40, unique=True, help_text='Por ejemplo «Trimestre 2026-Q4».')
    inicio = models.DateField('fecha de inicio')
    termino = models.DateField('fecha de término')
    estado = models.CharField('estado', max_length=8, choices=ESTADOS, default=ABIERTO)
    tope_item = models.PositiveSmallIntegerField(
        'tope por ítem (%)', default=120, validators=[MinValueValidator(100), MaxValueValidator(200)],
        help_text='Regla 7: sobre este porcentaje un ítem ya no suma puntaje.')
    tope_total = models.PositiveSmallIntegerField(
        'tope total (%)', default=150, validators=[MinValueValidator(100), MaxValueValidator(200)],
        help_text='Sobrecumplimiento máximo de un colaborador, incluidas las felicitaciones.')
    bono_felicitacion = models.PositiveSmallIntegerField(
        'bono por felicitación (%)', default=10, validators=[MaxValueValidator(50)])
    max_felicitaciones = models.PositiveSmallIntegerField('felicitaciones válidas como máximo', default=3)
    descuento_reclamo = models.PositiveSmallIntegerField(
        'descuento por reclamo (%)', default=20, validators=[MaxValueValidator(100)])
    umbral_naranjo = models.PositiveSmallIntegerField(
        'umbral naranjo (%)', default=60, validators=[MinValueValidator(1), MaxValueValidator(99)],
        help_text='Bajo este porcentaje de lo esperado al día, el semáforo queda en rojo.')
    cumplimiento_minimo = models.PositiveSmallIntegerField('cumplimiento mínimo (%)', default=80)
    creado = models.DateTimeField('creado', auto_now_add=True)
    # Un único período abierto a la vez: vale 1 si está abierto y NULL si no, con índice único.
    # MySQL no admite índices únicos parciales; una columna generada logra lo mismo en MySQL y SQLite.
    marca_abierto = models.GeneratedField(
        expression=models.Case(models.When(estado='ABIERTO', then=models.Value(1)),
                               output_field=models.PositiveSmallIntegerField()),
        output_field=models.PositiveSmallIntegerField(null=True), db_persist=True, unique=True, editable=False)

    class Meta:
        verbose_name = 'período'
        verbose_name_plural = 'períodos'
        ordering = ['-inicio']
        constraints = [
            models.CheckConstraint(condition=Q(termino__gt=models.F('inicio')), name='periodo_fechas_validas'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def dias(self):
        return (self.termino - self.inicio).days + 1

    @property
    def abierto(self):
        return self.estado == self.ABIERTO

    def contiene(self, fecha):
        return self.inicio <= fecha <= self.termino


class MetaCargo(models.Model):
    """Una fila de la hoja de un cargo: ítem, ponderador y meta trimestral."""

    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='metas', verbose_name='período')
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='metas', verbose_name='cargo')
    item = models.ForeignKey(ItemMedicion, on_delete=models.PROTECT, related_name='metas', verbose_name='ítem')
    meta = models.PositiveIntegerField(
        'meta del trimestre', validators=[MinValueValidator(1)],
        help_text='Cantidad de actividades; en ítems de tipo TUBO, porcentaje de solicitudes resueltas.')
    ponderador = models.DecimalField('ponderador (%)', max_digits=5, decimal_places=2,
                                     validators=[MinValueValidator(0.01), MaxValueValidator(100)])

    class Meta:
        verbose_name = 'meta por cargo'
        verbose_name_plural = 'metas por cargo'
        ordering = ['cargo__codigo', 'item__codigo']
        constraints = [models.UniqueConstraint(fields=['periodo', 'cargo', 'item'], name='meta_unica_por_cargo')]

    def __str__(self):
        return f'{self.cargo} · {self.item.nombre}'


# ---------------------------------------------------------------------------
# Organizaciones comunitarias (base JJVV)
# ---------------------------------------------------------------------------
class TipoOrganizacion(Catalogo):
    """Subfamilia de organización (correo de Gestión Delegaciones, 08-10-2026)."""

    TERRITORIAL = 'TERRITORIAL'
    FUNCIONAL = 'FUNCIONAL'
    FAMILIAS = [(TERRITORIAL, 'Territorial (Ley 19.418)'), (FUNCIONAL, 'Funcional (Ley 19.418 / 20.500)')]

    codigo = models.CharField('código', max_length=6, unique=True)
    nombre = models.CharField('subfamilia', max_length=60, unique=True)
    familia = models.CharField('familia', max_length=12, choices=FAMILIAS)

    class Meta:
        verbose_name = 'tipo de organización'
        verbose_name_plural = 'tipos de organización'
        ordering = ['familia', 'nombre']
        constraints = [models.UniqueConstraint(Lower('nombre'), name='tipo_org_nombre_unico_ci')]

    def __str__(self):
        return self.nombre


class Organizacion(models.Model):
    nombre = models.CharField('nombre', max_length=200)
    tipo = models.ForeignKey(TipoOrganizacion, on_delete=models.PROTECT, related_name='organizaciones',
                             verbose_name='subfamilia')
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name='organizaciones', verbose_name='territorio de delegación')
    domicilio = models.CharField('domicilio legal', max_length=200, blank=True)
    socios = models.PositiveIntegerField('socios activos', null=True, blank=True)
    fecha_constitucion = models.DateField('fecha de constitución', null=True, blank=True)
    registro_pj = models.PositiveIntegerField('N.º registro personalidad jurídica', unique=True)
    fecha_inscripcion = models.DateField('fecha de inscripción en el registro', null=True, blank=True)
    registro_directiva = models.PositiveIntegerField('N.º registro de directiva', null=True, blank=True)
    verificada = models.BooleanField('datos verificados', default=False)
    observacion = models.CharField('observación de calidad de datos', max_length=300, blank=True)
    activo = models.BooleanField('vigente', default=True)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    class Meta:
        verbose_name = 'organización'
        verbose_name_plural = 'organizaciones'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['delegacion', 'tipo'], name='org_delegacion_tipo'),
            models.Index(Lower('nombre'), name='org_nombre_ci'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def estado(self):
        return 'Vigente' if self.activo else 'No vigente'


# ---------------------------------------------------------------------------
# Actividades (TUBO de trabajo y gestiones de cada cargo)
# ---------------------------------------------------------------------------
class Actividad(models.Model):
    INGRESADO = 'INGRESADO'
    PENDIENTE = 'PENDIENTE'
    EN_PROCESO = 'EN_PROCESO'
    REALIZADO = 'REALIZADO'
    ESTADOS = [(INGRESADO, 'Ingresado'), (PENDIENTE, 'Pendiente'), (EN_PROCESO, 'En proceso'),
               (REALIZADO, 'Realizado')]

    ACCION = 'ACCION'
    GESTION = 'GESTION'
    NATURALEZAS = [
        (ACCION, 'Acción realizada (suma puntaje)'),
        (GESTION, 'Gestión previa: correo, coordinación, invitación (sin puntaje)'),
    ]

    VALIDACION_PENDIENTE = 'PENDIENTE'
    VALIDADA = 'VALIDADA'
    RECHAZADA = 'RECHAZADA'
    VALIDACIONES = [(VALIDACION_PENDIENTE, 'Por validar'), (VALIDADA, 'Validada'), (RECHAZADA, 'Rechazada')]

    INTERNA = 'INT'
    EXTERNA = 'EXT'
    ORIGENES = [(INTERNA, 'Interna (en la delegación)'), (EXTERNA, 'Externa (en terreno)')]

    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT, related_name='actividades',
                                verbose_name='período')
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name='actividades',
                                   verbose_name='delegación')
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='actividades', verbose_name='responsable')
    item = models.ForeignKey(ItemMedicion, on_delete=models.PROTECT, related_name='actividades',
                             verbose_name='ítem de la matriz')
    naturaleza = models.CharField('naturaleza', max_length=8, choices=NATURALEZAS, default=ACCION)
    origen = models.CharField('interna o externa', max_length=3, choices=ORIGENES, default=INTERNA)
    fecha = models.DateField('fecha de la actividad')
    titulo = models.CharField('actividad, solicitud o problema', max_length=200)
    descripcion = models.TextField('detalle', max_length=1500)
    solicitante_nombre = models.CharField('nombre del usuario', max_length=150, blank=True)
    solicitante_telefono = models.CharField('teléfono del usuario', max_length=20, blank=True)
    solicitante_es_delegado = models.BooleanField(
        'el solicitante es el delegado o la delegación', default=False,
        help_text='Regla 1: se registra como «otra gestión» y no suma puntaje.')
    organizacion = models.ForeignKey(Organizacion, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='actividades', verbose_name='organización')
    territorio = models.CharField('sector o territorio', max_length=80, blank=True)
    area_apoyo = models.CharField('área o persona de apoyo', max_length=120, blank=True)
    estado = models.CharField('estado en el TUBO', max_length=10, choices=ESTADOS, default=INGRESADO)
    fecha_compromiso = models.DateField('fecha de compromiso', null=True, blank=True)
    fecha_cierre = models.DateField('fecha de cierre', null=True, blank=True)

    validacion = models.CharField('validación', max_length=9, choices=VALIDACIONES, default=VALIDACION_PENDIENTE)
    validada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='actividades_validadas', verbose_name='validada por')
    validada_en = models.DateTimeField('validada el', null=True, blank=True)
    motivo_rechazo = models.CharField('motivo del rechazo', max_length=300, blank=True)

    # Resultado de las reglas 1, 2 y 5, calculado en el servidor al guardar
    puntua = models.BooleanField('suma puntaje', default=True, editable=False)
    motivo_sin_puntaje = models.CharField('motivo sin puntaje', max_length=300, blank=True, editable=False)

    ingresada_el = models.DateField('día de ingreso', editable=False)
    creada = models.DateTimeField('registrada', auto_now_add=True)
    token_envio = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    class Meta:
        verbose_name = 'actividad'
        verbose_name_plural = 'actividades'
        ordering = ['-fecha', '-id']
        indexes = [
            # Regla 3: conteo de ingresos del día por funcionario
            models.Index(fields=['funcionario', 'ingresada_el'], name='act_ingresos_diarios'),
            # Avance por ítem del período (tablero, informes). Índice «cubriente»: tiene todas las
            # columnas que filtra y agrupa el cálculo, así MySQL no lee la fila completa.
            models.Index(fields=['funcionario', 'periodo', 'estado', 'puntua', 'validacion', 'item'],
                         name='act_avance_item'),
            # Listado y TUBO de la delegación activa, más recientes primero
            models.Index(fields=['delegacion', '-fecha', '-id'], name='act_delegacion_fecha'),
            # Bandeja de validación: filtra y ordena por fecha sin ordenar en memoria
            models.Index(fields=['delegacion', 'validacion', '-fecha', '-id'], name='act_bandeja_validacion'),
        ]

    def __str__(self):
        return self.folio

    @property
    def folio(self):
        anio = self.fecha.year if self.fecha else ''
        return f'AC-{anio}-{self.pk:06d}' if self.pk else 'AC-nueva'

    @property
    def cuenta_para_avance(self):
        return self.puntua and self.validacion != self.RECHAZADA and self.estado == self.REALIZADO

    @property
    def vencida(self):
        from .reglas import hoy
        return bool(self.fecha_compromiso and self.estado != self.REALIZADO and self.fecha_compromiso < hoy())


class HistorialActividad(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='historial')
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    estado_anterior = models.CharField(max_length=10, blank=True)
    estado_nuevo = models.CharField(max_length=10)
    observacion = models.CharField('avance u observación', max_length=500)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'seguimiento de actividad'


def ruta_respaldo(instancia, nombre):
    """Nombre aleatorio: el nombre original nunca llega al disco (evita rutas maliciosas)."""
    extension = Path(nombre).suffix.lower()
    carpeta = instancia.__class__.__name__.lower()
    return f'{carpeta}/{uuid.uuid4().hex}{extension}'


class Evidencia(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='evidencias')
    archivo = models.FileField('archivo', upload_to=ruta_respaldo)
    nombre_original = models.CharField('nombre del archivo', max_length=150)
    tipo_mime = models.CharField(max_length=60)
    tamano = models.PositiveIntegerField('tamaño (bytes)')
    descripcion = models.CharField('descripción', max_length=200, blank=True)
    subida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    subida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-subida_en']
        verbose_name = 'evidencia'


# ---------------------------------------------------------------------------
# Semáforo: ausencias que ajustan la meta (regla 9)
# ---------------------------------------------------------------------------
class Ausencia(models.Model):
    LICENCIA = 'LICENCIA'
    VACACIONES = 'VACACIONES'
    EMERGENCIA = 'EMERGENCIA'
    ADMINISTRATIVO = 'ADMIN'
    COMPENSATORIO = 'COMPENSA'
    TIPOS = [(LICENCIA, 'Licencia médica'), (VACACIONES, 'Vacaciones'), (EMERGENCIA, 'Emergencia'),
             (ADMINISTRATIVO, 'Día administrativo'), (COMPENSATORIO, 'Compensatorio')]

    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT, related_name='ausencias', verbose_name='período')
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ausencias',
                                    verbose_name='funcionario')
    tipo = models.CharField('tipo', max_length=10, choices=TIPOS)
    desde = models.DateField('desde')
    hasta = models.DateField('hasta')
    observacion = models.CharField('observación', max_length=200, blank=True)
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-desde']
        verbose_name = 'ausencia'
        constraints = [models.CheckConstraint(condition=Q(hasta__gte=models.F('desde')),
                                              name='ausencia_fechas_validas')]
        indexes = [models.Index(fields=['periodo', 'funcionario'], name='aus_periodo_funcionario')]

    def __str__(self):
        return f'{self.get_tipo_display()} {self.desde:%d-%m} a {self.hasta:%d-%m}'

    @property
    def dias(self):
        return (self.hasta - self.desde).days + 1


# ---------------------------------------------------------------------------
# Felicitaciones y reclamos (regla 8 y hoja RECLAMOS)
# ---------------------------------------------------------------------------
class Observacion(models.Model):
    FELICITACION = 'FELICITACION'
    RECLAMO = 'RECLAMO'
    TIPOS = [(FELICITACION, 'Felicitación'), (RECLAMO, 'Reclamo')]
    CORREO = 'CORREO'
    WHATSAPP = 'WHATSAPP'
    LIBRO = 'LIBRO'
    MEDIOS = [(CORREO, 'Correo al delegado'), (WHATSAPP, 'WhatsApp al delegado'),
              (LIBRO, 'Libro de observaciones de la oficina')]

    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT, related_name='observaciones',
                                verbose_name='período')
    tipo = models.CharField('tipo', max_length=12, choices=TIPOS)
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='observaciones', verbose_name='funcionario')
    fecha = models.DateField('fecha de recepción')
    medio = models.CharField('medio formal', max_length=8, choices=MEDIOS)
    remitente = models.CharField('usuario que la emite', max_length=150)
    descripcion = models.CharField('descripción', max_length=500)
    respaldo = models.FileField('respaldo formal', upload_to=ruta_respaldo)
    respaldo_nombre = models.CharField(max_length=150)
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+',
                                       verbose_name='informada por')
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'felicitación o reclamo'
        verbose_name_plural = 'felicitaciones y reclamos'
        indexes = [models.Index(fields=['periodo', 'funcionario', 'tipo'], name='obs_periodo_funcionario')]

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.funcionario}'


def dias_habiles(desde, hasta):
    """Días de lunes a viernes entre dos fechas, ambas incluidas."""
    if hasta < desde:
        return 0
    total, dia = 0, desde
    while dia <= hasta:
        if dia.weekday() < 5:
            total += 1
        dia += timedelta(days=1)
    return total

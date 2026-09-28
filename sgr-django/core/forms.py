"""
Formularios del SGR.

La validación ocurre en el servidor (CU-18): aunque alguien desactive el
JavaScript del navegador o manipule la petición, Django revisa cada campo
antes de aceptar un registro.
"""

from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet, formset_factory

from . import calculos, datos
from .validadores import formatear_rut, validar_rut, validar_telefono


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
class FechaInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format='%Y-%m-%d')


def texto_largo(filas=3, ayuda=''):
    return forms.Textarea(attrs={'rows': filas, 'placeholder': ayuda})


def opciones(valores, vacia='Seleccione'):
    return [('', vacia)] + [(v, v) for v in valores]


def fecha_cl(fecha):
    return fecha.strftime('%d-%m-%Y')


ETIQUETAS_COMPROMISO = {
    'INGRESADO': 'Ingresado',
    'PENDIENTE': 'Pendiente',
    'EN_PROCESO': 'En proceso',
    'REALIZADO': 'Realizado',
}

# RF-018: desde cada estado solo se puede pasar a los indicados.
TRANSICIONES = {
    'INGRESADO': ['PENDIENTE', 'EN_PROCESO'],
    'PENDIENTE': ['EN_PROCESO', 'REALIZADO'],
    'EN_PROCESO': ['REALIZADO', 'PENDIENTE'],
    'REALIZADO': [],
}


# ---------------------------------------------------------------------------
# CU-01 · Acceso
# ---------------------------------------------------------------------------
class AccesoForm(forms.Form):
    usuario = forms.CharField(
        label='Usuario', max_length=50,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'placeholder': 'nombre.apellido'}))
    clave = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def clean(self):
        limpio = super().clean()
        if self.errors:
            return limpio
        self.cuenta = datos.verificar_cuenta(limpio.get('usuario'), limpio.get('clave'))
        if not self.cuenta:
            # Mensaje genérico: no revela si falló el usuario o la contraseña.
            raise ValidationError('Usuario o contraseña incorrectos. Verifique sus datos e intente nuevamente.')
        return limpio


# ---------------------------------------------------------------------------
# CU-07 · Registrar actividad
# ---------------------------------------------------------------------------
class ActividadForm(forms.Form):
    fecha = forms.DateField(
        label='Fecha de la actividad', widget=FechaInput(),
        help_text='Debe estar dentro del período abierto.')
    item = forms.ChoiceField(label='Ítem de medición')
    tipo = forms.ChoiceField(label='Tipo de actividad')
    descripcion = forms.CharField(
        label='Actividad, solicitud o problema atendido', min_length=10, max_length=500,
        widget=texto_largo(3, 'Describa la situación atendida'))
    accion = forms.CharField(
        label='Acción ejecutada', min_length=10, max_length=500,
        widget=texto_largo(3, 'Describa lo que se hizo para resolver o derivar'))
    contacto = forms.CharField(
        label='Nombre de contacto', required=False, max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'Persona u organización'}))
    telefono = forms.CharField(
        label='Teléfono de contacto', required=False, validators=[validar_telefono],
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+56 9 1234 5678'}))
    agenda = forms.BooleanField(
        label='Esta actividad genera un compromiso para la agenda colectiva', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].choices = opciones(datos.almacen['items'], 'Seleccione un ítem')
        self.fields['tipo'].choices = [('', 'Seleccione un tipo')] + [
            (t['nombre'], ('— ' if t['padre'] else '') + t['nombre'])
            for t in datos.almacen['tipos_actividad']
        ]

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha > calculos.hoy():
            raise ValidationError('La fecha no puede ser posterior a hoy.')
        periodo = calculos.periodo_abierto()
        if not periodo:
            raise ValidationError('No hay un período abierto para registrar actividades.')
        if not periodo['inicio'] <= fecha <= periodo['termino']:
            raise ValidationError(
                f"La fecha debe estar dentro del período abierto "
                f"({fecha_cl(periodo['inicio'])} al {fecha_cl(periodo['termino'])}).")
        return fecha


# ---------------------------------------------------------------------------
# CU-09 · Adjuntar evidencia
# ---------------------------------------------------------------------------
FIRMAS_ARCHIVO = {
    'image/jpeg': b'\xff\xd8\xff',
    'image/png': b'\x89PNG',
    'application/pdf': b'%PDF',
}


class EvidenciaForm(forms.Form):
    actividad = forms.ChoiceField(
        label='Actividad', help_text='Solo se listan sus actividades sin evidencia aprobada.')
    archivo = forms.FileField(
        label='Archivo de respaldo', help_text='JPG, PNG o PDF. Máximo 2 MB.',
        widget=forms.FileInput(attrs={'accept': '.jpg,.jpeg,.png,.pdf'}))
    observacion = forms.CharField(
        label='Observación', required=False, max_length=300,
        widget=texto_largo(2, 'Contexto de la evidencia, si corresponde'))

    def __init__(self, *args, actividades=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actividad'].choices = [('', 'Seleccione la actividad')] + [
            (a['codigo'], f"{a['codigo']} — {a['descripcion']}") for a in actividades
        ]

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        formatos = settings.SGR_EVIDENCIA_FORMATOS
        maximo = settings.SGR_EVIDENCIA_MAX_MB
        extension = Path(archivo.name).suffix.lower()

        if extension not in formatos:
            raise ValidationError('Formato no permitido. Use JPG, PNG o PDF.')
        if archivo.size == 0:
            raise ValidationError('El archivo está vacío.')
        if archivo.size > maximo * 1024 * 1024:
            raise ValidationError(
                f'El archivo pesa {archivo.size / 1048576:.1f} MB y supera el máximo de {maximo} MB.')

        # Se revisa el contenido real, no solo el nombre: un archivo renombrado
        # a .jpg no pasa si por dentro no es una imagen (RNF-017).
        cabecera = archivo.read(8)
        archivo.seek(0)
        if not cabecera.startswith(FIRMAS_ARCHIVO[formatos[extension]]):
            raise ValidationError('El contenido del archivo no corresponde a su extensión.')
        return archivo


# ---------------------------------------------------------------------------
# CU-10 · Validar evidencia
# ---------------------------------------------------------------------------
class ValidacionForm(forms.Form):
    codigo = forms.CharField(widget=forms.HiddenInput)
    resultado = forms.ChoiceField(label='Resultado', choices=[
        ('', 'Seleccione'),
        ('APROBADA', 'Aprobar'),
        ('RECHAZADA', 'Rechazar'),
        ('CORRECCION', 'Solicitar corrección'),
    ])
    observacion = forms.CharField(
        label='Observación', required=False, max_length=500,
        widget=texto_largo(3, 'Motivo de la decisión'),
        help_text='Obligatoria al rechazar o solicitar corrección.')

    def clean(self):
        limpio = super().clean()
        if limpio.get('resultado') in ('RECHAZADA', 'CORRECCION') and not limpio.get('observacion', '').strip():
            self.add_error('observacion', 'Indique el motivo: un rechazo o una corrección no pueden quedar sin observación.')
        return limpio


# ---------------------------------------------------------------------------
# CU-11 y CU-12 · Agenda colectiva
# ---------------------------------------------------------------------------
class CompromisoForm(forms.Form):
    solicitante = forms.CharField(
        label='Solicitante', min_length=4, max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'Vecino u organización'}))
    descripcion = forms.CharField(
        label='Compromiso adquirido', min_length=10, max_length=500, widget=texto_largo(3))
    territorio = forms.CharField(label='Territorio', max_length=120)
    responsable = forms.ChoiceField(label='Responsable')
    fecha = forms.DateField(
        label='Fecha comprometida', widget=FechaInput(),
        help_text='Si la fecha ya pasó, el compromiso aparecerá como vencido.')

    def __init__(self, *args, responsables=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].choices = opciones(responsables)


class EstadoCompromisoForm(forms.Form):
    estado = forms.ChoiceField(label='Estado nuevo')
    observacion = forms.CharField(
        label='Observación', min_length=5, max_length=300,
        widget=texto_largo(3, 'Qué cambió y por qué'))

    def __init__(self, *args, compromiso, **kwargs):
        super().__init__(*args, **kwargs)
        actual = compromiso['estado']
        permitidos = TRANSICIONES[actual]
        # Si alguien envía un estado fuera de esta lista, Django lo rechaza:
        # la regla de transición se cumple en el servidor, no solo en pantalla.
        self.fields['estado'].choices = [('', 'Seleccione')] + [
            (e, ETIQUETAS_COMPROMISO[e]) for e in permitidos
        ]
        self.fields['estado'].help_text = (
            f'Desde «{ETIQUETAS_COMPROMISO[actual]}» solo se permite pasar a: '
            + ', '.join(ETIQUETAS_COMPROMISO[e] for e in permitidos) + '.'
        )


# ---------------------------------------------------------------------------
# CU-08 · Atención social
# ---------------------------------------------------------------------------
class AtencionSocialForm(forms.Form):
    rut = forms.CharField(
        label='RUT de la persona usuaria', max_length=12, validators=[validar_rut],
        widget=forms.TextInput(attrs={'placeholder': '12.345.678-5'}),
        help_text='Si el RUT ya tiene un caso, la atención se agrega a ese caso.')
    nombre = forms.CharField(label='Nombre', min_length=5, max_length=150)
    tipo = forms.ChoiceField(label='Tipo de atención')
    fecha = forms.DateField(label='Fecha', widget=FechaInput())
    resultado = forms.CharField(label='Resultado', min_length=10, max_length=200, widget=texto_largo(3))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].choices = opciones(
            [t['nombre'] for t in datos.almacen['tipos_actividad'] if t['area'] == 'Social'])
        self.caso = None

    def clean_rut(self):
        return formatear_rut(self.cleaned_data['rut'])

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha > calculos.hoy():
            raise ValidationError('La fecha no puede ser posterior a hoy.')
        return fecha

    def clean(self):
        limpio = super().clean()
        rut = limpio.get('rut')
        if rut:
            self.caso = datos.buscar('casos_sociales', rut=rut)
            if self.caso and len(self.caso['gestiones']) >= 3:
                self.add_error('rut', 'Este caso ya tiene tres gestiones registradas (RN-012). '
                                      'Para continuar la atención debe abrirse un caso nuevo.')
        return limpio


# ---------------------------------------------------------------------------
# CU-02 · Delegaciones
# ---------------------------------------------------------------------------
class DelegacionForm(forms.Form):
    nombre = forms.CharField(label='Nombre', min_length=3, max_length=80, help_text='El nombre no puede repetirse.')
    ambito = forms.CharField(label='Ámbito territorial', min_length=8, max_length=150)
    correo = forms.EmailField(
        label='Correo', widget=forms.EmailInput(attrs={'placeholder': 'delegacion@laserena.cl'}))
    telefono = forms.CharField(
        label='Teléfono', required=False, validators=[validar_telefono],
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+56 9 1234 5678'}))

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if any(d['nombre'].lower() == nombre.lower() for d in datos.almacen['delegaciones']):
            raise ValidationError('Ya existe una delegación con ese nombre.')
        return nombre


# ---------------------------------------------------------------------------
# CU-03 · Usuarios y roles
# ---------------------------------------------------------------------------
class UsuarioForm(forms.Form):
    rut = forms.CharField(
        label='RUT', max_length=12, validators=[validar_rut],
        widget=forms.TextInput(attrs={'placeholder': '12.345.678-5'}))
    nombre = forms.CharField(label='Nombre completo', min_length=6, max_length=160)
    correo = forms.EmailField(label='Correo institucional')
    telefono = forms.CharField(
        label='Teléfono', required=False, validators=[validar_telefono],
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+56 9 1234 5678'}))
    cargo = forms.ChoiceField(label='Cargo')
    delegacion = forms.ChoiceField(label='Delegación')
    roles = forms.MultipleChoiceField(
        label='Roles', widget=forms.CheckboxSelectMultiple,
        help_text='Los permisos del usuario son la suma de todos sus roles.',
        error_messages={'required': 'Seleccione al menos un rol: sin rol el usuario no tendría permisos.'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cargo'].choices = opciones(datos.almacen['cargos'])
        self.fields['delegacion'].choices = opciones(
            [d['nombre'] for d in datos.almacen['delegaciones'] if d['estado'] == 'ACTIVA'])
        self.fields['roles'].choices = [(r, r) for r in datos.almacen['roles']]

    def clean_rut(self):
        rut = formatear_rut(self.cleaned_data['rut'])
        if datos.buscar('usuarios', rut=rut):
            raise ValidationError('Ya existe un usuario con ese RUT.')
        return rut

    def clean_correo(self):
        correo = self.cleaned_data['correo'].lower()
        if datos.buscar('usuarios', correo=correo):
            raise ValidationError('Ya existe un usuario con ese correo.')
        return correo


# ---------------------------------------------------------------------------
# CU-05 · Períodos
# ---------------------------------------------------------------------------
class PeriodoForm(forms.Form):
    nombre = forms.CharField(
        label='Nombre', min_length=5, max_length=60,
        widget=forms.TextInput(attrs={'placeholder': 'Trimestre 2026-Q4'}))
    inicio = forms.DateField(label='Fecha de inicio', widget=FechaInput())
    termino = forms.DateField(label='Fecha de término', widget=FechaInput())
    dias = forms.IntegerField(
        label='Días computables', required=False, min_value=1,
        help_text='Déjelo vacío para usar los días de calendario. Úselo si no se cuentan fines de semana.')
    umbral_verde = forms.IntegerField(label='Verde desde (%)', initial=100, min_value=1, max_value=200)
    umbral_ambar = forms.IntegerField(label='Ámbar desde (%)', initial=60, min_value=1, max_value=200)
    tope = forms.IntegerField(label='Tope de cumplimiento (%)', initial=150, min_value=100, max_value=300)

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if any(p['nombre'].lower() == nombre.lower() for p in datos.almacen['periodos']):
            raise ValidationError('Ya existe un período con ese nombre.')
        return nombre

    def clean(self):
        limpio = super().clean()
        inicio, termino = limpio.get('inicio'), limpio.get('termino')
        if inicio and termino:
            if termino < inicio:
                self.add_error('termino', 'La fecha de término no puede ser anterior al inicio.')
            else:
                calendario = (termino - inicio).days + 1
                dias = limpio.get('dias') or calendario
                if dias > calendario:
                    self.add_error('dias', f'El período tiene {calendario} días de calendario; '
                                           'los computables no pueden superarlos.')
                limpio['dias'] = dias
        verde, ambar = limpio.get('umbral_verde'), limpio.get('umbral_ambar')
        if verde and ambar and ambar >= verde:
            self.add_error('umbral_ambar', 'El umbral ámbar debe ser menor que el verde.')
        return limpio


# ---------------------------------------------------------------------------
# CU-06 · Metas y ponderaciones (formset)
# ---------------------------------------------------------------------------
class MetaForm(forms.Form):
    item = forms.ChoiceField(label='Ítem de medición')
    objetivo = forms.DecimalField(label='Meta del período', max_digits=10, decimal_places=2)
    ponderador = forms.DecimalField(
        label='Ponderador (%)', min_value=0, max_value=100, max_digits=5, decimal_places=2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].choices = opciones(datos.almacen['items'])

    def clean_objetivo(self):
        objetivo = self.cleaned_data['objetivo']
        if objetivo <= 0:
            raise ValidationError('La meta debe ser mayor que cero (RN-002).')
        return objetivo


class BaseMetaFormSet(BaseFormSet):
    """Reglas que involucran a todas las filas a la vez."""

    def clean(self):
        if any(self.errors):
            return
        vigentes = [
            f for f in self.forms
            if f.cleaned_data and not (self.can_delete and self._should_delete_form(f))
        ]
        if not vigentes:
            raise ValidationError('Configure al menos un ítem para el cargo.')

        items = [f.cleaned_data['item'] for f in vigentes]
        repetidos = sorted({i for i in items if items.count(i) > 1})
        if repetidos:
            raise ValidationError(f'El ítem «{repetidos[0]}» está repetido. Cada ítem se configura una sola vez.')

        suma = sum(f.cleaned_data['ponderador'] for f in vigentes)
        if suma != 100:
            def coma(n):
                return f'{n:.1f}'.replace('.', ',')
            raise ValidationError(
                f'La suma de ponderadores es {coma(suma)} % y debe cerrar en 100 % (RN-001). '
                f'{"Faltan" if suma < 100 else "Sobran"} {coma(abs(100 - suma))} puntos.')
        self.vigentes = vigentes


MetaFormSet = formset_factory(MetaForm, formset=BaseMetaFormSet, extra=0, can_delete=True)


# ---------------------------------------------------------------------------
# Filtros de búsqueda (CU-17)
# ---------------------------------------------------------------------------
class FiltroActividadesForm(forms.Form):
    delegacion = forms.ChoiceField(label='Delegación', required=False)
    item = forms.ChoiceField(label='Ítem de medición', required=False)
    estado = forms.ChoiceField(label='Estado', required=False, choices=[
        ('', 'Todos'), ('REGISTRADA', 'Registrada'), ('VALIDADA', 'Validada'), ('RECHAZADA', 'Rechazada'),
    ])
    texto = forms.CharField(
        label='Código o descripción', required=False, max_length=80,
        widget=forms.TextInput(attrs={'placeholder': 'EV-2026-000001'}))

    def __init__(self, *args, delegaciones=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delegacion'].choices = opciones(delegaciones, 'Todas')
        self.fields['item'].choices = opciones(datos.almacen['items'], 'Todos')


TIPOS_INFORME = [
    ('delegacion', 'Cumplimiento por delegación'),
    ('funcionario', 'Avance por funcionario'),
    ('agenda', 'Estado de la agenda colectiva'),
]


class InformeForm(forms.Form):
    tipo = forms.ChoiceField(label='Tipo de informe', choices=TIPOS_INFORME)
    delegacion = forms.ChoiceField(label='Delegación', required=False)
    desde = forms.DateField(label='Desde', widget=FechaInput())
    hasta = forms.DateField(label='Hasta', widget=FechaInput())

    def __init__(self, *args, delegaciones=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delegacion'].choices = opciones(delegaciones, 'Todas')

    def clean(self):
        limpio = super().clean()
        desde, hasta = limpio.get('desde'), limpio.get('hasta')
        if desde and hasta and hasta < desde:
            self.add_error('hasta', 'La fecha final no puede ser anterior a la inicial.')
        return limpio


EVENTOS_AUDITORIA = [
    ('', 'Todos los eventos'),
    ('ALTA', 'Alta'),
    ('CAMBIO_ESTADO', 'Cambio de estado'),
    ('CAMBIO_PARAMETRO', 'Cambio de parámetro'),
    ('VALIDACION', 'Validación'),
    ('ACCESO_DENEGADO', 'Acceso denegado'),
    ('EXPORTACION', 'Exportación'),
]


class FiltroAuditoriaForm(forms.Form):
    evento = forms.ChoiceField(label='Evento', required=False, choices=EVENTOS_AUDITORIA)

"""Formularios de la matriz SGR. Las reglas de negocio se validan aquí y de nuevo en el servidor."""

from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from catalogos.models import Cargo, ItemMedicion

from .models import Actividad, Ausencia, MetaCargo, Observacion, Organizacion, Periodo
from .reglas import fecha_minima_de_ingreso, hoy, normalizar_telefono, validar_fecha_actividad

# Firma de los primeros bytes de cada formato permitido: la extensión sola no basta
FIRMAS = {
    '.pdf': [b'%PDF-'],
    '.png': [b'\x89PNG\r\n\x1a\n'],
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
}


def validar_archivo(archivo):
    """Formato por extensión y por contenido, y tamaño máximo (OWASP: carga de archivos)."""
    extension = Path(archivo.name).suffix.lower()
    formatos = settings.SGR_EVIDENCIA_FORMATOS
    if extension not in formatos:
        raise ValidationError(f'Formato no permitido. Use {", ".join(sorted(formatos)).upper()}.')
    limite = settings.SGR_EVIDENCIA_MAX_MB * 1024 * 1024
    if archivo.size > limite:
        raise ValidationError(f'El archivo supera {settings.SGR_EVIDENCIA_MAX_MB} MB.')
    archivo.seek(0)
    cabecera = archivo.read(16)
    archivo.seek(0)
    if not any(cabecera.startswith(firma) for firma in FIRMAS.get(extension, [])):
        raise ValidationError('El contenido del archivo no corresponde a su extensión.')
    return formatos[extension]


class FechaInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%d', **kwargs)


# ---------------------------------------------------------------------------
# Actividades
# ---------------------------------------------------------------------------
class ActividadForm(forms.ModelForm):
    token_envio = forms.UUIDField(widget=forms.HiddenInput)

    class Meta:
        model = Actividad
        fields = ['fecha', 'item', 'naturaleza', 'origen', 'titulo', 'descripcion', 'solicitante_nombre',
                  'solicitante_telefono', 'solicitante_es_delegado', 'organizacion', 'territorio', 'area_apoyo',
                  'estado', 'fecha_compromiso']
        widgets = {
            'fecha': FechaInput(), 'fecha_compromiso': FechaInput(),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'solicitante_telefono': forms.TextInput(attrs={'type': 'tel', 'placeholder': '+56 9 1234 5678'}),
            'naturaleza': forms.RadioSelect,
        }

    def __init__(self, *args, funcionario=None, delegacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.funcionario = funcionario
        items = ItemMedicion.objects.filter(activo=True, medicion=ItemMedicion.CONTEO)
        periodo = Periodo.objects.filter(estado=Periodo.ABIERTO).first()
        if funcionario and funcionario.cargo_id and periodo:
            propios = items.filter(metas__periodo=periodo, metas__cargo_id=funcionario.cargo_id)
            if propios.exists():
                items = propios
        self.fields['item'].queryset = items.distinct().order_by('codigo')
        self.fields['item'].empty_label = 'Seleccione el ítem de su cargo'
        self.fields['item'].help_text = 'Solo se muestran los ítems con meta para su cargo en el período abierto.'
        organizaciones = Organizacion.objects.filter(activo=True)
        if delegacion:
            organizaciones = organizaciones.filter(delegacion=delegacion)
        self.fields['organizacion'].queryset = organizaciones.order_by('nombre')
        self.fields['organizacion'].empty_label = 'Ninguna'
        self.fields['organizacion'].help_text = 'Organizaciones del territorio de la delegación activa.'
        minima = fecha_minima_de_ingreso()
        self.fields['fecha'].widget.attrs.update({'min': minima.isoformat(), 'max': hoy().isoformat()})
        self.fields['fecha'].help_text = (f'Desde el {minima:%d-%m-%Y}: la semana anterior se cierra el lunes.')
        self.fields['solicitante_nombre'].help_text = 'Obligatorio para que la actividad sume puntaje.'
        self.fields['solicitante_telefono'].help_text = 'Obligatorio para que sume. Móvil o fijo, con o sin +56.'
        self.fields['fecha_compromiso'].help_text = 'Solo si es una solicitud que queda en seguimiento (TUBO).'
        self.fields['estado'].initial = Actividad.REALIZADO

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        validar_fecha_actividad(fecha)
        if not Periodo.objects.filter(estado=Periodo.ABIERTO, inicio__lte=fecha, termino__gte=fecha).exists():
            raise ValidationError('La fecha no pertenece al período abierto.')
        return fecha

    def clean_solicitante_nombre(self):
        return ' '.join(self.cleaned_data['solicitante_nombre'].split())

    def clean_solicitante_telefono(self):
        valor = self.cleaned_data['solicitante_telefono'].strip()
        if not valor:
            return ''
        normalizado = normalizar_telefono(valor)
        if not normalizado:
            raise ValidationError('Escriba un teléfono chileno de 9 dígitos, por ejemplo +56 9 1234 5678.')
        return normalizado

    def clean(self):
        limpio = super().clean()
        compromiso, fecha = limpio.get('fecha_compromiso'), limpio.get('fecha')
        if compromiso and fecha and compromiso < fecha:
            self.add_error('fecha_compromiso', 'La fecha de compromiso no puede ser anterior a la actividad.')
        if limpio.get('estado') != Actividad.REALIZADO and not compromiso:
            self.add_error('fecha_compromiso', 'Una solicitud pendiente necesita fecha de compromiso.')
        return limpio


class EstadoActividadForm(forms.Form):
    estado = forms.ChoiceField(label='Nuevo estado', choices=Actividad.ESTADOS)
    observacion = forms.CharField(label='Avance u observación', min_length=5, max_length=500,
                                  widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, actividad=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actividad = actividad

    def clean_estado(self):
        estado = self.cleaned_data['estado']
        if self.actividad and estado == self.actividad.estado:
            raise ValidationError('Elija un estado distinto del actual.')
        return estado


class EvidenciaForm(forms.Form):
    archivo = forms.FileField(label='Archivo de respaldo',
                              help_text='PDF, JPG o PNG de hasta 2 MB. Se guarda con un nombre aleatorio.')
    descripcion = forms.CharField(label='Descripción', max_length=200, required=False)

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        self.tipo_mime = validar_archivo(archivo)
        return archivo


class ValidacionForm(forms.Form):
    decision = forms.ChoiceField(choices=[(Actividad.VALIDADA, 'Validar'), (Actividad.RECHAZADA, 'Rechazar')])
    motivo = forms.CharField(max_length=300, required=False)

    def clean(self):
        limpio = super().clean()
        if limpio.get('decision') == Actividad.RECHAZADA and len((limpio.get('motivo') or '').strip()) < 5:
            self.add_error('motivo', 'Indique el motivo del rechazo (al menos 5 caracteres).')
        return limpio


# ---------------------------------------------------------------------------
# Ausencias, felicitaciones y reclamos (las registra el delegado)
# ---------------------------------------------------------------------------
class AusenciaForm(forms.ModelForm):
    class Meta:
        model = Ausencia
        fields = ['funcionario', 'tipo', 'desde', 'hasta', 'observacion']
        widgets = {'desde': FechaInput(), 'hasta': FechaInput()}

    def __init__(self, *args, funcionarios=None, periodo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.periodo = periodo
        self.fields['funcionario'].queryset = funcionarios
        self.fields['funcionario'].empty_label = 'Seleccione un funcionario'

    def clean(self):
        limpio = super().clean()
        desde, hasta, funcionario = limpio.get('desde'), limpio.get('hasta'), limpio.get('funcionario')
        if desde and hasta:
            if hasta < desde:
                self.add_error('hasta', 'La fecha de término no puede ser anterior al inicio.')
            elif self.periodo and (desde > self.periodo.termino or hasta < self.periodo.inicio):
                self.add_error('desde', f'La ausencia debe caer dentro de {self.periodo}.')
            elif funcionario and Ausencia.objects.filter(
                    funcionario=funcionario, desde__lte=hasta, hasta__gte=desde).exclude(pk=self.instance.pk).exists():
                self.add_error('desde', 'Se superpone con otra ausencia ya registrada para ese funcionario.')
        return limpio


class ObservacionForm(forms.ModelForm):
    class Meta:
        model = Observacion
        fields = ['tipo', 'funcionario', 'fecha', 'medio', 'remitente', 'descripcion', 'respaldo']
        widgets = {'fecha': FechaInput(), 'descripcion': forms.Textarea(attrs={'rows': 2})}
        labels = {'respaldo': 'Respaldo formal (captura del correo, WhatsApp o libro)'}

    def __init__(self, *args, funcionarios=None, periodo=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.periodo, self.actor = periodo, actor
        self.fields['funcionario'].queryset = funcionarios
        self.fields['funcionario'].empty_label = 'Seleccione un funcionario'
        self.fields['respaldo'].help_text = 'Obligatorio (regla 8). PDF, JPG o PNG de hasta 2 MB.'
        self.fields['medio'].help_text = ('Solo cuentan las recibidas por el delegado. Un mensaje del usuario al '
                                          'funcionario no es válido.')

    def clean_respaldo(self):
        archivo = self.cleaned_data['respaldo']
        validar_archivo(archivo)
        return archivo

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha > hoy():
            raise ValidationError('La fecha no puede ser posterior a hoy.')
        if self.periodo and not self.periodo.contiene(fecha):
            raise ValidationError(f'La fecha debe estar dentro de {self.periodo}.')
        return fecha

    def clean_funcionario(self):
        funcionario = self.cleaned_data['funcionario']
        if self.actor and funcionario.pk == self.actor.pk:
            raise ValidationError('No puede registrar una felicitación o reclamo sobre usted mismo.')
        return funcionario


# ---------------------------------------------------------------------------
# Configuración: períodos y metas
# ---------------------------------------------------------------------------
class PeriodoForm(forms.ModelForm):
    class Meta:
        model = Periodo
        fields = ['nombre', 'inicio', 'termino', 'tope_item', 'tope_total', 'bono_felicitacion',
                  'max_felicitaciones', 'descuento_reclamo', 'umbral_naranjo', 'cumplimiento_minimo']
        widgets = {'inicio': FechaInput(), 'termino': FechaInput()}

    def clean(self):
        limpio = super().clean()
        inicio, termino = limpio.get('inicio'), limpio.get('termino')
        if inicio and termino:
            if termino <= inicio:
                self.add_error('termino', 'El término debe ser posterior al inicio.')
            elif Periodo.objects.filter(inicio__lte=termino, termino__gte=inicio).exclude(pk=self.instance.pk).exists():
                self.add_error('inicio', 'Se superpone con otro período existente.')
        return limpio


class MetaForm(forms.ModelForm):
    class Meta:
        model = MetaCargo
        fields = ['cargo', 'item', 'meta', 'ponderador']

    def __init__(self, *args, periodo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.periodo = periodo
        self.fields['cargo'].queryset = Cargo.objects.filter(activo=True)
        self.fields['item'].queryset = ItemMedicion.objects.filter(activo=True)

    def clean(self):
        limpio = super().clean()
        cargo, item, ponderador = limpio.get('cargo'), limpio.get('item'), limpio.get('ponderador')
        if cargo and item and self.periodo:
            otras = MetaCargo.objects.filter(periodo=self.periodo, cargo=cargo).exclude(pk=self.instance.pk)
            if otras.filter(item=item).exists():
                self.add_error('item', 'Ese ítem ya tiene meta para el cargo en este período.')
            if ponderador is not None and sum(m.ponderador for m in otras) + ponderador > 100:
                self.add_error('ponderador', 'Los ponderadores del cargo sumarían más de 100 %.')
            if item.medicion == ItemMedicion.TUBO and limpio.get('meta') and limpio['meta'] > 100:
                self.add_error('meta', 'En un ítem de tipo TUBO la meta es un porcentaje (máximo 100).')
        return limpio

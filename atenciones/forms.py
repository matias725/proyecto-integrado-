"""Formulario de ingreso de atención ciudadana."""

from django import forms

from catalogos.models import SubAtencion, TipoAtencion
from core.validadores import formatear_rut, validar_rut, validar_telefono


class AtencionForm(forms.Form):
    token_envio = forms.UUIDField(widget=forms.HiddenInput)
    rut = forms.CharField(
        label='RUT del vecino o solicitante', max_length=12, validators=[validar_rut],
        widget=forms.TextInput(attrs={'placeholder': '12.345.678-5', 'autocomplete': 'off'}),
        help_text='Si ya está registrado, se completa su nombre.')
    nombre = forms.CharField(label='Nombre del solicitante', min_length=5, max_length=150)
    telefono = forms.CharField(
        label='Teléfono de contacto', required=False, validators=[validar_telefono],
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+56 9 1234 5678'}))
    tipo = forms.ModelChoiceField(
        label='Tipo de Atención', queryset=TipoAtencion.objects.none(), empty_label='Seleccione un tipo')
    subatencion = forms.ModelChoiceField(
        label='Sub Atención', queryset=SubAtencion.objects.none(), empty_label='Seleccione primero un tipo')
    descripcion = forms.CharField(
        label='Descripción de la atención', min_length=10, max_length=1000,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describa la solicitud y los antecedentes necesarios.'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoAtencion.objects.filter(activo=True).order_by('nombre')
        tipo_id = self.data.get('tipo') if self.is_bound else None
        subs = SubAtencion.objects.filter(activo=True, tipo__activo=True)
        # La lista de sub atenciones depende del tipo elegido
        self.fields['subatencion'].queryset = (subs.filter(tipo_id=tipo_id) if tipo_id and str(tipo_id).isdigit()
                                               else subs).order_by('nombre')
        if self.is_bound and tipo_id:
            self.fields['subatencion'].empty_label = 'Seleccione una sub atención'

    def clean_rut(self):
        return formatear_rut(self.cleaned_data['rut'])

    def clean_nombre(self):
        return ' '.join(self.cleaned_data['nombre'].split())

    def clean(self):
        limpio = super().clean()
        tipo, sub = limpio.get('tipo'), limpio.get('subatencion')
        if tipo and sub and sub.tipo_id != tipo.pk:
            self.add_error('subatencion', f'«{sub}» no pertenece al tipo «{tipo}». Elija una sub atención del tipo.')
        return limpio


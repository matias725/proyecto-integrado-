"""Formularios de los catálogos con sus reglas de integridad."""

from django import forms
from django.core.exceptions import ValidationError

from core.forms_base import FormularioCatalogo
from core.reglas import motivo_no_desactivar

from .models import Delegacion, ItemMedicion, SubAtencion, TipoAtencion


def validar_desactivacion(form):
    activo = form.cleaned_data['activo']
    if form.instance.pk and form.instance.activo and not activo:
        motivo = motivo_no_desactivar(form.instance)
        if motivo:
            raise ValidationError(motivo)
    return activo


class DelegacionForm(FormularioCatalogo):
    prefijo, digitos = 'DEL', 2

    class Meta:
        model = Delegacion
        fields = ['codigo', 'nombre', 'direccion', 'comuna', 'activo']

    def clean_activo(self):
        return validar_desactivacion(self)


class ItemForm(FormularioCatalogo):
    prefijo, digitos = 'IT', 3

    class Meta:
        model = ItemMedicion
        fields = ['codigo', 'nombre', 'descripcion', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}


class TipoAtencionForm(FormularioCatalogo):
    prefijo, digitos = 'TA', 3

    class Meta:
        model = TipoAtencion
        fields = ['codigo', 'nombre', 'descripcion', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}

    def clean_activo(self):
        return validar_desactivacion(self)


class SubAtencionForm(FormularioCatalogo):
    prefijo, digitos = 'SA', 3
    nombre_unico = False  # el nombre es único dentro de su tipo

    class Meta:
        model = SubAtencion
        fields = ['codigo', 'nombre', 'tipo', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tipos = TipoAtencion.objects.filter(activo=True)
        if self.instance.pk:
            tipos = tipos | TipoAtencion.objects.filter(pk=self.instance.tipo_id)
        self.fields['tipo'].queryset = tipos.distinct().order_by('nombre')
        self.fields['tipo'].help_text = 'Solo se ofrecen tipos de atención activos.'

    def clean(self):
        limpio = super().clean()
        tipo, nombre = limpio.get('tipo'), limpio.get('nombre')
        if tipo and nombre and SubAtencion.objects.filter(tipo=tipo, nombre__iexact=nombre).exclude(
                pk=self.instance.pk).exists():
            self.add_error('nombre', f'El tipo «{tipo}» ya tiene una sub atención con ese nombre.')
        if tipo and limpio.get('activo') and not tipo.activo:
            self.add_error('activo', 'No puede quedar activa mientras su tipo de atención esté inactivo.')
        if self.instance.pk and tipo and tipo.pk != self.instance.tipo_id and self.instance.atenciones.exists():
            self.add_error('tipo', 'Ya tiene atenciones registradas con el tipo actual; no se puede cambiar.')
        return limpio

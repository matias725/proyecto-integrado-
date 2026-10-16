"""Comportamiento común de los formularios de catálogos."""

import re

from django import forms
from django.core.exceptions import ValidationError


def siguiente_codigo(modelo, prefijo, digitos):
    numeros = [
        int(m.group(1)) for codigo in modelo.objects.values_list('codigo', flat=True)
        if (m := re.fullmatch(rf'{prefijo}(\d+)', codigo or ''))
    ]
    return f'{prefijo}{(max(numeros, default=0) + 1):0{digitos}d}'


class FormularioCatalogo(forms.ModelForm):
    """
    Normaliza el código a mayúsculas, propone el siguiente código libre y
    rechaza nombres duplicados sin distinguir mayúsculas ni tildes de más.
    """

    prefijo = ''
    digitos = 3
    nombre_unico = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'codigo' in self.fields:
            ejemplo = f'{self.prefijo}{"1".zfill(self.digitos)}'
            self.fields['codigo'].help_text = f'Formato {ejemplo}. Se propone el siguiente disponible.'
            self.fields['codigo'].widget.attrs.update({'maxlength': len(ejemplo), 'class': 'mayusculas'})
            if not self.instance.pk and not self.is_bound:
                self.initial.setdefault('codigo', siguiente_codigo(self._meta.model, self.prefijo, self.digitos))
        if 'activo' in self.fields:
            self.fields['activo'].label = 'Registro activo'

    def _duplicado(self, campo, valor):
        modelo = self._meta.model
        return modelo.objects.filter(**{f'{campo}__iexact': valor}).exclude(pk=self.instance.pk).exists()

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].strip().upper()
        if self._duplicado('codigo', codigo):
            raise ValidationError('Ya existe un registro con ese código.')
        return codigo

    def clean_nombre(self):
        nombre = re.sub(r'\s+', ' ', self.cleaned_data['nombre']).strip()
        if len(nombre) < 3:
            raise ValidationError('Escriba al menos 3 caracteres.')
        if self.nombre_unico and self._duplicado('nombre', nombre):
            raise ValidationError('Ya existe un registro con ese nombre.')
        return nombre

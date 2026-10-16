"""Requisitos de la contraseña, visibles en la pantalla de nueva clave."""

import re

from django.core.exceptions import ValidationError

REQUISITOS = [
    (r'.{8,}', 'Mínimo 8 caracteres'),
    (r'[A-ZÁÉÍÓÚÑ]', 'Al menos una letra mayúscula'),
    (r'[a-záéíóúñ]', 'Al menos una letra minúscula'),
    (r'\d', 'Al menos un número'),
    (r'[^A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]', 'Al menos un carácter especial, por ejemplo ! @ # $ %'),
]


class ComplejidadClaveValidator:
    def validate(self, password, user=None):
        faltan = [texto for patron, texto in REQUISITOS[1:] if not re.search(patron, password or '')]
        if faltan:
            raise ValidationError('La contraseña no cumple: ' + '; '.join(f.lower() for f in faltan) + '.',
                                  code='clave_debil')

    def get_help_text(self):
        return 'Debe incluir mayúscula, minúscula, número y carácter especial.'

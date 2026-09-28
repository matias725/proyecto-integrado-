"""Validadores de formato reutilizados por los formularios (CU-18)."""

import re

from django.core.exceptions import ValidationError


def limpiar_rut(valor):
    return re.sub(r'[^0-9kK]', '', valor or '').upper()


def digito_verificador(cuerpo):
    """Dígito verificador del RUT chileno por módulo 11."""
    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    return {11: '0', 10: 'K'}.get(resto, str(resto))


def formatear_rut(valor):
    """Devuelve el RUT con puntos y guion: 12.345.678-5."""
    limpio = limpiar_rut(valor)
    cuerpo, dv = limpio[:-1], limpio[-1:]
    con_puntos = f'{int(cuerpo):,}'.replace(',', '.') if cuerpo else ''
    return f'{con_puntos}-{dv}'


def validar_rut(valor):
    limpio = limpiar_rut(valor)
    if not re.fullmatch(r'\d{7,8}[0-9K]', limpio):
        raise ValidationError('Escriba el RUT con su dígito verificador, por ejemplo 12.345.678-5.')
    if digito_verificador(limpio[:-1]) != limpio[-1]:
        raise ValidationError('El RUT ingresado no es válido: el dígito verificador no corresponde.')


def validar_telefono(valor):
    if not re.fullmatch(r'\+?56\s?9\s?\d{4}\s?\d{4}', (valor or '').strip()):
        raise ValidationError('Use el formato de celular chileno +56 9 1234 5678.')

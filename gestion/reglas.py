"""
Reglas del nuevo requerimiento de la matriz SGR (correo de Coordinación de
Delegaciones, 08-10-2026). Todas se aplican en el servidor; los formularios
solo las anticipan para orientar al funcionario.

    1  Actividades donde el usuario es el delegado: «otra gestión», sin puntaje.
    2  Sin nombre y teléfono del usuario: sin puntaje.
    3  Máximo 7 ingresos diarios por funcionario.
    4  Cierre semanal: la semana (lunes a viernes) se cierra el lunes
       siguiente; desde el martes ya no se ingresan actividades de ella.
    5  Gestiones previas (correos, coordinaciones, invitaciones): sin puntaje.
    6  Ingresos para generar puntaje: alertas de calidad en el tablero.
    7  Tope de 120 % por ítem (configurable por período).
    8  Felicitaciones solo con respaldo formal y registradas por el delegado.
    9  Ausencias ingresadas por el delegado ajustan la meta.
   10  El puntaje se muestra también como resultado del equipo.
"""

import re
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

MAX_INGRESOS_DIARIOS = 7


def hoy():
    """Fecha de trabajo. SGR_FECHA_HOY permite fijarla en pruebas y demostraciones."""
    return getattr(settings, 'SGR_FECHA_HOY', None) or timezone.localdate()


# ---------------------------------------------------------------------------
# Regla 4: cierre semanal
# ---------------------------------------------------------------------------
def lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def ultimo_dia_de_ingreso(fecha):
    """La semana de `fecha` admite ingresos hasta el lunes siguiente inclusive."""
    return lunes_de(fecha) + timedelta(days=7)


def fecha_minima_de_ingreso(dia=None):
    """Fecha más antigua que todavía se puede ingresar en `dia`."""
    dia = dia or hoy()
    if dia.weekday() == 0:          # lunes: aún se completa la semana anterior
        return dia - timedelta(days=7)
    return lunes_de(dia)


def validar_fecha_actividad(fecha, dia=None):
    dia = dia or hoy()
    if fecha > dia:
        raise ValidationError('La fecha de la actividad no puede ser posterior a hoy.', code='futura')
    if dia > ultimo_dia_de_ingreso(fecha):
        raise ValidationError(
            f'La semana del {lunes_de(fecha):%d-%m-%Y} ya está cerrada: se podía ingresar hasta el lunes '
            f'{ultimo_dia_de_ingreso(fecha):%d-%m-%Y}. Regla 4 del requerimiento.', code='semana_cerrada')


# ---------------------------------------------------------------------------
# Regla 3: máximo de ingresos diarios
# ---------------------------------------------------------------------------
def ingresos_del_dia(funcionario, dia=None):
    from .models import Actividad
    return Actividad.objects.filter(funcionario=funcionario, ingresada_el=dia or hoy()).count()


def validar_cupo_diario(funcionario, dia=None):
    if ingresos_del_dia(funcionario, dia) >= MAX_INGRESOS_DIARIOS:
        raise ValidationError(
            f'Ya registró {MAX_INGRESOS_DIARIOS} actividades hoy, el máximo diario. Ingrese el resto mañana; '
            'recuerde que la semana se cierra el lunes siguiente. Regla 3 del requerimiento.', code='cupo_diario')


# ---------------------------------------------------------------------------
# Regla 2: teléfono del usuario
# ---------------------------------------------------------------------------
def normalizar_telefono(valor):
    """Acepta 9 dígitos (móvil 9XXXXXXXX o fijo 51XXXXXXX) con o sin +56. Devuelve '' si no es válido."""
    digitos = re.sub(r'\D', '', valor or '')
    if len(digitos) == 11 and digitos.startswith('56'):
        digitos = digitos[2:]
    if len(digitos) != 9 or digitos[0] not in '92345678':
        return ''
    if digitos[0] == '9':
        return f'+56 9 {digitos[1:5]} {digitos[5:]}'
    return f'+56 {digitos[:2]} {digitos[2:]}'


# ---------------------------------------------------------------------------
# Reglas 1, 2 y 5: ¿la actividad suma puntaje?
# ---------------------------------------------------------------------------
def evaluar_puntaje(actividad):
    """Devuelve (puntua, motivo). El motivo explica al funcionario por qué no suma."""
    from .models import Actividad

    motivos = []
    if actividad.solicitante_es_delegado:
        motivos.append('El solicitante es el delegado o la delegación: cuenta como otra gestión (regla 1).')
    if not actividad.solicitante_nombre.strip() or not actividad.solicitante_telefono.strip():
        motivos.append('Falta el nombre o el teléfono del usuario (regla 2).')
    if actividad.naturaleza == Actividad.GESTION:
        motivos.append('Es una gestión previa (correo, coordinación o invitación); el punto se da al realizar '
                       'la acción (regla 5).')
    return (not motivos, ' '.join(motivos))


def aplicar_reglas_de_puntaje(actividad):
    actividad.puntua, actividad.motivo_sin_puntaje = evaluar_puntaje(actividad)
    return actividad

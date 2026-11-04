"""
Etiquetas y filtros propios de los templates del SGR.

Uso en un template:  {% load sgr_tags %}
"""

import json

from django import template
from django.utils.html import format_html, json_script

from cuentas.modulos import ESTADOS as ESTADOS_MODULO, OPERATIVO

register = template.Library()

ESTADOS = {
    'VALIDADA': ('ok', 'Validada'),
    'REGISTRADA': ('neutro', 'Registrada'),
    'RECHAZADA': ('error', 'Rechazada'),
    'ANULADA': ('neutro', 'Anulada'),
    'APROBADA': ('ok', 'Aprobada'),
    'PENDIENTE': ('pendiente', 'Pendiente'),
    'SIN_EVIDENCIA': ('neutro', 'Sin evidencia'),
    'EN_CORRECCION': ('pendiente', 'En corrección'),
    'INGRESADO': ('neutro', 'Ingresado'),
    'EN_PROCESO': ('proceso', 'En proceso'),
    'REALIZADO': ('ok', 'Realizado'),
    'ACTIVA': ('ok', 'Activa'),
    'ACTIVO': ('ok', 'Activo'),
    'INACTIVA': ('neutro', 'Inactiva'),
    'INACTIVO': ('neutro', 'Inactivo'),
    'ABIERTO': ('ok', 'Abierto'),
    'POR_VALIDAR': ('pendiente', 'Por validar'),
    'CERRADO': ('neutro', 'Cerrado'),
}

CLASE_SEMAFORO = {'verde': 'ok', 'ambar': 'pendiente', 'rojo': 'error', 'neutro': 'neutro'}
TEXTO_SEMAFORO = {'verde': 'Verde', 'ambar': 'Naranjo', 'rojo': 'Rojo', 'neutro': 'Sin metas'}


@register.simple_tag
def estado(valor):
    """Insignia de estado con color y texto: {% estado actividad.estado %}"""
    clase, texto = ESTADOS.get(valor, ('neutro', valor))
    return format_html('<span class="estado {}">{}</span>', clase, texto)


@register.simple_tag
def insignia(clase, texto):
    return format_html('<span class="estado {}">{}</span>', clase, texto)


@register.filter
def clase_semaforo(color):
    return CLASE_SEMAFORO.get(color, 'neutro')


@register.simple_tag
def semaforo(color):
    """Insignia del semáforo con color y texto (no depende solo del color: accesibilidad)."""
    return format_html('<span class="estado {}"><i class="punto {}" aria-hidden="true"></i>{}</span>',
                       CLASE_SEMAFORO.get(color, 'neutro'), color, TEXTO_SEMAFORO.get(color, color))


@register.filter
def cifra(valor, decimales=1):
    """Número con coma decimal y punto de miles: 1234.5 -> 1.234,5"""
    try:
        texto = f'{float(valor):,.{int(decimales)}f}'
    except (TypeError, ValueError):
        return valor
    return texto.replace(',', '§').replace('.', ',').replace('§', '.')


@register.filter
def iniciales(nombre):
    return ''.join(p[0] for p in str(nombre).split()[:2]).upper()


@register.filter
def primer_nombre(nombre):
    return str(nombre).split()[0] if nombre else ''


@register.filter
def unir(lista, separador=' y '):
    return separador.join(lista or [])


@register.simple_tag
def rellenar(**valores):
    """
    Datos que un botón entrega al modal que abre.
    {% rellenar id_codigo=a.codigo %} escribe el código en el campo id_codigo.
    """
    return format_html('data-rellenar="{}"', json.dumps(valores, default=str, ensure_ascii=False))


@register.inclusion_tag('parciales/_medidor.html')
def medidor(fila, esperado, tope=120):
    """Barra de avance con la marca de lo esperado al día y el tope por ítem (regla 7)."""
    return {'fila': fila, 'esperado': esperado, 'tope': tope}


@register.simple_tag(takes_context=True)
def mensajes_json(context):
    """Entrega los mensajes de Django a SweetAlert2 como JSON seguro."""
    datos = [{'nivel': m.level_tag, 'texto': str(m)} for m in context.get('messages', [])]
    return json_script(datos, 'mensajes-sgr') if datos else ''


@register.filter
def estado_modulo(codigo):
    return 'operativo' if ESTADOS_MODULO.get(codigo) == OPERATIVO else 'simulado'


@register.simple_tag(takes_context=True)
def modulo_actual(context):
    """Enlace del menú que corresponde a la pantalla actual."""
    for grupo in context.get('menu', []):
        for enlace in grupo['enlaces']:
            if enlace['activo']:
                return enlace
    return None


@register.filter
def tiene_permiso(usuario, codigo):
    """{% if user|tiene_permiso:'atenciones.crear' %}"""
    modulo, _, accion = codigo.partition('.')
    return bool(getattr(usuario, 'is_authenticated', False)) and usuario.tiene_permiso(modulo, accion or 'ver')

"""
Reglas de cálculo del SGR (RN-003 a RN-008).

Equivale a la clase de servicio CalculadoraIndicadores del diagrama de
clases: todas las fórmulas viven en un solo lugar, de modo que un ajuste de
criterio institucional se hace aquí y afecta a todas las pantallas por igual.
"""

from django.conf import settings

from . import datos


def hoy():
    """Día de referencia del prototipo (ver SGR_FECHA_REFERENCIA)."""
    return settings.SGR_FECHA_REFERENCIA


def periodo_abierto():
    return next((p for p in datos.almacen['periodos'] if p['estado'] == 'ABIERTO'), None)


def dias_transcurridos(periodo, fecha=None):
    """Días computables transcurridos, acotados entre 0 y el total del período."""
    fecha = fecha or hoy()
    transcurridos = (fecha - periodo['inicio']).days + 1
    return max(0, min(transcurridos, periodo['dias']))


def meta_esperada_al_dia(periodo, fecha=None):
    """RN-007: días transcurridos / días totales x 100."""
    if not periodo['dias']:
        return 0.0
    return dias_transcurridos(periodo, fecha) / periodo['dias'] * 100


def cumplimiento(avance, objetivo):
    """RN-004: avance / meta x 100. Una meta igual a cero no es medible (RN-002)."""
    if not objetivo or objetivo <= 0:
        return 0.0
    return avance / objetivo * 100


def ponderado(porcentaje, ponderador, tope):
    """RN-005: el cumplimiento se limita al tope y se multiplica por el ponderador."""
    return min(porcentaje, tope) * ponderador / 100


def semaforo(porcentaje, esperado, periodo):
    """RN-008: verde si alcanza lo esperado; ámbar sobre el umbral; rojo bajo él."""
    if porcentaje >= esperado:
        return 'verde'
    if porcentaje >= esperado * periodo['umbral_ambar'] / 100:
        return 'ambar'
    return 'rojo'


TEXTO_SEMAFORO = {
    'verde': 'En nivel esperado',
    'ambar': 'Bajo lo esperado',
    'rojo': 'Requiere apoyo',
}


def indicadores(cargo, periodo, fecha=None):
    """Calcula los indicadores de un cargo en un período (CU-20)."""
    esperado = meta_esperada_al_dia(periodo, fecha)
    filas = []
    for meta in datos.almacen['metas']:
        if meta['cargo'] != cargo or meta['periodo'] != periodo['id']:
            continue
        porcentaje = cumplimiento(meta['avance'], meta['objetivo'])
        filas.append({
            **meta,
            'cumplimiento': porcentaje,
            'ponderado': ponderado(porcentaje, meta['ponderador'], periodo['tope']),
            'color': semaforo(porcentaje, esperado, periodo),
            'ancho': min(porcentaje, 100),
        })
    total = sum(f['ponderado'] for f in filas)
    return {
        'filas': filas,
        'esperado': esperado,
        'total': total,
        'color_total': semaforo(total, esperado, periodo),
    }

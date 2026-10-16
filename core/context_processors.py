"""Variables disponibles en todos los templates."""

from . import calculos, datos, permisos


def periodo_seleccionado(request):
    """Período elegido en la barra superior, o el abierto por defecto."""
    elegido = request.session.get('periodo_id')
    periodo = datos.buscar('periodos', id=elegido) if elegido else None
    return periodo or calculos.periodo_abierto() or datos.almacen['periodos'][0]


def sgr(request):
    usuario = permisos.usuario_actual(request)
    if not usuario:
        return {'usuario_actual': None}
    return {
        'usuario_actual': usuario,
        'menu': permisos.menu_para(usuario),
        'periodos': datos.almacen['periodos'],
        'periodo_actual': periodo_seleccionado(request),
        'fecha_referencia': calculos.hoy(),
    }

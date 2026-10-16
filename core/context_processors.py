"""Variables disponibles en todos los templates."""

from django.conf import settings

from cuentas.modulos import MODULOS, OPERATIVO, ORDEN_GRUPOS

from . import calculos, datos, permisos


def periodo_seleccionado(request):
    """Período elegido en los módulos simulados, o el abierto por defecto."""
    elegido = request.session.get('periodo_id')
    periodo = datos.buscar('periodos', id=elegido) if elegido else None
    return periodo or calculos.periodo_abierto() or datos.almacen['periodos'][0]


# Rutas adicionales que mantienen iluminado un enlace del menú
RUTAS_EXTRA = {
    'actividades': {'actividad_nueva', 'actividad_registrada'},
    'agenda': {'compromiso_estado'},
    'periodos': {'periodo_estado'},
    'auditoria': {'auditoria_exportar'},
}


def url_de(codigo, estado):
    if codigo in ('auditoria', 'correos') or estado != OPERATIVO:
        return codigo
    return f'{codigo}_lista'


def menu_para(usuario, actual=''):
    grupos = {}
    for codigo, nombre, estado, _acciones, icono, grupo in MODULOS:
        if usuario.tiene_permiso(codigo, 'ver'):
            url = url_de(codigo, estado)
            activo = (actual == url or actual.startswith(f'{codigo}_') or actual in RUTAS_EXTRA.get(codigo, ()))
            grupos.setdefault(grupo, []).append({
                'codigo': codigo, 'texto': nombre, 'icono': icono, 'url': url, 'activo': activo,
                'simulado': estado != OPERATIVO,
            })
    return [{'titulo': g, 'enlaces': grupos[g]} for g in ORDEN_GRUPOS if g in grupos]


def sgr(request):
    contexto = {'sgr_version': settings.SGR_VERSION, 'mostrar_cuentas_demo': settings.SGR_CUENTAS_DEMO}
    if not request.user.is_authenticated:
        return contexto
    contexto.update({
        'menu': menu_para(request.user, getattr(request.resolver_match, 'url_name', '') or ''),
        'delegacion_activa': getattr(request, 'delegacion_activa', None),
        'delegaciones_autorizadas': getattr(request, 'delegaciones_autorizadas', []),
        # Contexto de los módulos simulados heredados
        'usuario_actual': permisos.usuario_actual(request),
        'periodos': datos.almacen['periodos'],
        'periodo_actual': periodo_seleccionado(request),
        'fecha_referencia': calculos.hoy(),
    })
    return contexto

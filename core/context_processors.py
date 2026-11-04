"""Variables disponibles en todos los templates."""

from functools import lru_cache

from django.conf import settings
from django.contrib.staticfiles import finders

from cuentas.modulos import MANTENEDORES, MODULOS, ORDEN_GRUPOS


# Rutas adicionales que mantienen iluminado un enlace del menú
RUTAS_EXTRA = {
    'actividades': {'actividad_nueva', 'actividad_ver', 'actividades_exportar'},
    'evidencias': {'evidencia_descargar'},
    'validacion': {'validar'},
    'informes': {'informes_exportar'},
    'auditoria': {'auditoria_exportar'},
}


def url_de(codigo, _estado=None):
    return f'{codigo}_lista' if codigo in MANTENEDORES else codigo


def menu_para(usuario, actual=''):
    grupos = {}
    for codigo, nombre, estado, _acciones, icono, grupo in MODULOS:
        if usuario.tiene_permiso(codigo, 'ver'):
            url = url_de(codigo, estado)
            activo = (actual == url or actual.startswith(f'{codigo}_') or actual in RUTAS_EXTRA.get(codigo, ()))
            grupos.setdefault(grupo, []).append({
                'codigo': codigo, 'texto': nombre, 'icono': icono, 'url': url, 'activo': activo,
            })
    return [{'titulo': g, 'enlaces': grupos[g]} for g in ORDEN_GRUPOS if g in grupos]


LOGO = 'img/logo-municipalidad.png'


@lru_cache(maxsize=1)
def logo_institucional():
    """Ruta del logo oficial si el equipo lo agregó en static/img/ (ver README)."""
    return LOGO if finders.find(LOGO) else ''


def sgr(request):
    contexto = {'sgr_version': settings.SGR_VERSION, 'mostrar_cuentas_demo': settings.SGR_CUENTAS_DEMO,
                'logo_institucional': logo_institucional()}
    if not request.user.is_authenticated:
        return contexto
    contexto.update({
        'menu': menu_para(request.user, getattr(request.resolver_match, 'url_name', '') or ''),
        'delegacion_activa': getattr(request, 'delegacion_activa', None),
        'delegaciones_autorizadas': getattr(request, 'delegaciones_autorizadas', []),
    })
    return contexto

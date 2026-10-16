"""Auditoría, verificación de salud para AWS y página de error del servidor."""

from functools import reduce
from operator import or_

from django.conf import settings
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.views.decorators.http import require_safe

from cuentas.permisos import permiso_requerido

from .excel import respuesta_excel
from .models import Auditoria, registrar


def _filtrar(request):
    consulta = Auditoria.objects.all()
    texto = request.GET.get('q', '').strip()
    evento = request.GET.get('evento', '')
    filtros = []
    if not request.user.alcance_global:
        nombres = [str(d) for d in request.delegaciones_autorizadas]
        consulta = consulta.filter(delegacion__in=nombres)
    if texto:
        for palabra in texto.split()[:5]:
            consulta = consulta.filter(reduce(or_, (Q(**{f'{c}__icontains': palabra}) for c in
                                                    ('usuario_texto', 'entidad', 'detalle', 'registro', 'delegacion'))))
        filtros.append(('Búsqueda', texto))
    if evento in dict(Auditoria.EVENTOS):
        consulta = consulta.filter(evento=evento)
        filtros.append(('Evento', dict(Auditoria.EVENTOS)[evento]))
    return consulta, texto, evento, filtros


@require_safe
@permiso_requerido('auditoria', 'ver')
def auditoria(request):
    consulta, texto, evento, _ = _filtrar(request)
    pagina = Paginator(consulta, 20).get_page(request.GET.get('pagina'))
    return render(request, 'core/auditoria.html', {
        'pagina': pagina, 'texto': texto, 'evento': evento, 'eventos': Auditoria.EVENTOS,
    })


@require_safe
@permiso_requerido('auditoria', 'ver')
def auditoria_exportar(request):
    consulta, _t, _e, filtros = _filtrar(request)
    filas = [[e.fecha, e.usuario_texto, e.get_evento_display(), e.entidad, e.registro, e.detalle, e.delegacion,
              e.ip] for e in consulta[:20000]]
    registrar(request, 'EXPORTACION', 'auditoria', detalle=f'{len(filas)} eventos')
    return respuesta_excel('auditoria', 'Auditoría', ['Fecha', 'Usuario', 'Evento', 'Entidad', 'Registro',
                                                      'Detalle', 'Delegación', 'IP'], filas, filtros, request.user)


def salud(request):
    """Lo consulta el balanceador o el monitoreo de AWS. No expone datos."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        base = 'ok'
    except Exception:  # noqa: BLE001 - se informa el estado, no el detalle
        base = 'error'
    estado = 200 if base == 'ok' else 503
    return JsonResponse({'estado': 'ok' if estado == 200 else 'degradado', 'base_de_datos': base,
                         'version': settings.SGR_VERSION}, status=estado)


def error_servidor(request):
    plantilla = loader.get_template('500.html')
    return HttpResponseServerError(plantilla.render({'sgr_version': settings.SGR_VERSION}))


def acceso_denegado(request, exception=None):
    """Manejador 403 global: registra el intento y muestra la pantalla institucional."""
    from cuentas.permisos import denegar
    return denegar(request, str(exception or '')[:200])


def csrf_fallido(request, reason=''):
    """El formulario venció (p. ej. pestaña abierta mucho tiempo). No se guardó nada."""
    plantilla = loader.get_template('csrf.html')
    return HttpResponseForbidden(plantilla.render({'volver': request.path}, request))

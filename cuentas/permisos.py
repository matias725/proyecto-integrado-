"""
Control de acceso en el servidor (RNF-005).

Ocultar un botón no protege nada: cada vista operativa declara el módulo y la
acción que exige, y la petición se rechaza con 403 si el rol no lo permite.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render

from core.models import registrar


def denegar(request, detalle=''):
    registrar(request, 'ACCESO_DENEGADO', request.path[:60], detalle=detalle)
    return render(request, '403.html', {'detalle': detalle}, status=403)


def permiso_requerido(modulo, accion='ver'):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.tiene_permiso(modulo, accion):
                return denegar(request, f'{modulo}.{accion}')
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def sesion_requerida(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return vista(request, *args, **kwargs)
    return envoltura

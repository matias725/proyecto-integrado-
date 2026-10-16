"""
Control de acceso por rol (RNF-005).

El menú oculta lo que un rol no puede usar, pero la protección real está en
el decorador @requiere_permiso: aunque alguien escriba la dirección a mano,
la vista se niega y el intento queda en la auditoría.
"""

from functools import wraps

from django.shortcuts import redirect, render

from . import datos

TODOS = {'Administrador', 'Coordinador', 'Delegado', 'Funcionario', 'Verificador', 'Consulta'}

PERMISOS = {
    'tablero':         TODOS,
    'actividades':     {'Funcionario', 'Verificador', 'Delegado', 'Coordinador', 'Administrador'},
    'actividad_nueva': {'Funcionario', 'Administrador'},
    'evidencias':      {'Funcionario', 'Verificador', 'Administrador'},
    'validacion':      {'Verificador', 'Coordinador', 'Administrador'},
    'agenda':          {'Funcionario', 'Delegado', 'Coordinador', 'Administrador'},
    'atencion_social': {'Funcionario', 'Delegado', 'Administrador'},
    'delegaciones':    {'Administrador'},
    'usuarios':        {'Administrador'},
    'periodos':        {'Coordinador', 'Administrador'},
    'metas':           {'Coordinador', 'Administrador'},
    'informes':        {'Delegado', 'Coordinador', 'Administrador'},
    'auditoria':       {'Administrador'},
}

# Roles que ven todas las delegaciones. El resto queda limitado a la suya (CA-07).
ROLES_TRANSVERSALES = {'Coordinador', 'Administrador'}

MENU = [
    ('Operación', [
        ('tablero', 'Tablero', 'bi-speedometer2', ['tablero']),
        ('actividades', 'Actividades', 'bi-journal-text',
         ['actividades', 'actividad_nueva', 'actividad_registrada']),
        ('evidencias', 'Evidencias', 'bi-paperclip', ['evidencias']),
        ('validacion', 'Validación', 'bi-patch-check', ['validacion']),
        ('agenda', 'Agenda colectiva', 'bi-calendar-week', ['agenda', 'compromiso_estado']),
        ('atencion_social', 'Atención social', 'bi-people', ['atencion_social']),
    ]),
    ('Configuración', [
        ('delegaciones', 'Delegaciones', 'bi-geo-alt', ['delegaciones']),
        ('usuarios', 'Usuarios', 'bi-person-gear', ['usuarios']),
        ('periodos', 'Períodos', 'bi-calendar3', ['periodos']),
        ('metas', 'Metas', 'bi-bullseye', ['metas']),
    ]),
    ('Información', [
        ('informes', 'Informes', 'bi-file-earmark-bar-graph', ['informes']),
        ('auditoria', 'Auditoría', 'bi-clock-history', ['auditoria']),
    ]),
]


def usuario_actual(request):
    return request.session.get('usuario')


def puede(usuario, seccion):
    return bool(usuario) and bool(set(usuario['roles']) & PERMISOS.get(seccion, set()))


def tiene_rol(usuario, *roles):
    return bool(usuario) and bool(set(usuario['roles']) & set(roles))


def ambito(usuario):
    """Delegación a la que se limita el usuario, o None si ve todas."""
    if tiene_rol(usuario, *ROLES_TRANSVERSALES):
        return None
    return usuario['delegacion']


def en_ambito(usuario, registros, campo='delegacion'):
    limite = ambito(usuario)
    return [r for r in registros if limite is None or r[campo] == limite]


def menu_para(usuario):
    grupos = []
    for titulo, enlaces in MENU:
        visibles = [
            {'id': ident, 'texto': texto, 'icono': icono, 'url': ident, 'activos': activos}
            for ident, texto, icono, activos in enlaces
            if puede(usuario, ident)
        ]
        if visibles:
            grupos.append({'titulo': titulo, 'enlaces': visibles})
    return grupos


def requiere_permiso(seccion):
    """Exige sesión iniciada y un rol autorizado para la sección."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            usuario = usuario_actual(request)
            if not usuario:
                return redirect('acceso')
            if not puede(usuario, seccion):
                datos.registrar_auditoria(
                    usuario['nombre'], 'ACCESO_DENEGADO', seccion, None, '—', request.path)
                return render(request, '403.html', {'seccion': seccion}, status=403)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador

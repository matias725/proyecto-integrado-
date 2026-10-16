"""
Adaptador para los módulos simulados heredados de la EV1.

Esas pantallas trabajan con datos en memoria (core/datos.py) y esperaban un
diccionario de usuario con nombre, roles y delegación. Aquí ese diccionario se
construye desde el usuario real autenticado, de modo que el acceso a los
módulos simulados también lo decide el rol definido en la base de datos.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login

from cuentas.permisos import denegar

# Sección heredada -> (módulo, acción) del sistema de permisos real
SECCIONES = {
    'tablero': ('tablero', 'ver'),
    'actividades': ('actividades', 'ver'),
    'actividad_nueva': ('actividades', 'crear'),
    'evidencias': ('evidencias', 'ver'),
    'validacion': ('validacion', 'ver'),
    'agenda': ('agenda', 'ver'),
    'atencion_social': ('atencion_social', 'ver'),
    'periodos': ('periodos', 'ver'),
    'metas': ('metas', 'ver'),
    'informes': ('informes', 'ver'),
}

ROLES_TRANSVERSALES = {'Coordinador', 'Administrador'}


def _roles_heredados(usuario):
    roles = set()
    if usuario.rol.protegido:
        roles.add('Administrador')
    if usuario.alcance_global:
        roles.add('Coordinador')
    if usuario.tiene_permiso('validacion', 'editar'):
        roles.add('Verificador')
    if usuario.tiene_permiso('actividades', 'crear') or usuario.tiene_permiso('evidencias', 'crear'):
        roles.add('Funcionario')
    if usuario.tiene_permiso('usuarios', 'ver') and not usuario.alcance_global:
        roles.add('Delegado')
    return sorted(roles) or ['Consulta']


def usuario_actual(request):
    if not request.user.is_authenticated:
        return None
    activa = getattr(request, 'delegacion_activa', None)
    return {
        'nombre': request.user.nombre,
        'roles': _roles_heredados(request.user),
        'delegacion': activa.nombre if activa else '',
        'permisos': request.user.permisos_codigos(),
    }


def puede(usuario, seccion):
    modulo, accion = SECCIONES.get(seccion, (seccion, 'ver'))
    return bool(usuario) and f'{modulo}.{accion}' in usuario.get('permisos', set())


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


def requiere_permiso(seccion):
    """Exige sesión y el permiso real correspondiente a la sección simulada."""
    modulo, accion = SECCIONES[seccion]

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

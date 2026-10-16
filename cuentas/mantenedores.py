"""Mantenedores de roles y usuarios."""

from django.db.models import Count

from core.crud import Mantenedor

from .forms import RolForm, UsuarioForm
from .models import Rol, Usuario


class Roles(Mantenedor):
    modulo = 'roles'
    modelo = Rol
    formulario = RolForm
    titulo = 'Roles y permisos'
    singular = 'rol'
    femenino = False
    descripcion = 'Cada rol define qué módulos y acciones están permitidos y sobre qué delegaciones.'
    traza = 'RF-002 · RNF-005 · CU-03 · HU-26'
    plantilla_formulario = 'cuentas/rol_formulario.html'
    columnas = [('codigo', 'Código'), ('nombre', 'Rol'), ('get_alcance_display', 'Alcance'),
                ('total_permisos', 'Permisos'), ('total_usuarios', 'Usuarios')]
    busqueda = ['codigo', 'nombre', 'descripcion']
    exportar = [('codigo', 'Código'), ('nombre', 'Rol'), ('descripcion', 'Descripción'),
                ('get_alcance_display', 'Alcance'), ('total_permisos', 'Permisos'),
                ('total_usuarios', 'Usuarios'), ('estado', 'Estado')]
    detalle = [('codigo', 'Código'), ('nombre', 'Rol'), ('descripcion', 'Descripción'),
               ('get_alcance_display', 'Alcance autorizado'), ('protegido', 'Rol del sistema'),
               ('estado', 'Estado'), ('actualizado', 'Última modificación')]
    relacionados = [('usuarios', 'Usuarios con este rol', [('nombre', 'Nombre'), ('correo', 'Correo'),
                                                            ('estado', 'Estado')])]

    def consulta(self, request):
        return Rol.objects.annotate(total_permisos=Count('permisos', distinct=True),
                                    total_usuarios=Count('usuarios', distinct=True))


class Usuarios(Mantenedor):
    modulo = 'usuarios'
    modelo = Usuario
    formulario = UsuarioForm
    titulo = 'Usuarios del sistema'
    singular = 'usuario'
    femenino = False
    campo_activo = 'is_active'
    orden = ['nombre']
    descripcion = 'Cuentas de acceso. Un perfil por delegación solo administra usuarios de sus delegaciones.'
    traza = 'RF-002 · RNF-004 · CU-03 · HU-26'
    plantilla_formulario = 'cuentas/usuario_formulario.html'
    columnas = [('nombre', 'Nombre'), ('correo', 'Correo'), ('rol.nombre', 'Rol'),
                ('lista_delegaciones', 'Delegación')]
    busqueda = ['nombre', 'nombre_usuario', 'correo', 'rol__nombre', 'delegaciones__nombre',
                'delegaciones__codigo']
    # Sin contraseña, intentos ni bloqueos: solo datos autorizados
    exportar = [('nombre', 'Nombre'), ('nombre_usuario', 'Usuario'), ('correo', 'Correo'), ('rol.nombre', 'Rol'),
                ('lista_delegaciones', 'Delegaciones'), ('estado', 'Estado'), ('last_login', 'Último acceso')]
    detalle = [('nombre', 'Nombre'), ('nombre_usuario', 'Usuario'), ('correo', 'Correo'), ('rol.nombre', 'Rol'),
               ('rol.get_alcance_display', 'Alcance del rol'), ('lista_delegaciones', 'Delegaciones autorizadas'),
               ('estado', 'Estado'), ('last_login', 'Último acceso'), ('creado', 'Creado')]

    def consulta(self, request):
        consulta = Usuario.objects.select_related('rol').prefetch_related('delegaciones')
        if not request.user.alcance_global:
            consulta = consulta.filter(delegaciones__in=request.delegaciones_autorizadas).distinct()
        return consulta

    def puede_modificar(self, request, obj):
        # Sin alcance global no se modifican cuentas con más privilegios que el propio
        return request.user.alcance_global or not (obj.alcance_global or obj.rol.protegido)

    def kwargs_formulario(self, request):
        return {'actor': request.user}


ROLES = Roles()
USUARIOS = Usuarios()

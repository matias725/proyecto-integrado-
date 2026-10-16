"""Declaración de los mantenedores de catálogos."""

from django.db.models import Count, Q

from core.crud import Mantenedor

from .forms import DelegacionForm, ItemForm, SubAtencionForm, TipoAtencionForm
from .models import Delegacion, ItemMedicion, SubAtencion, TipoAtencion


class Delegaciones(Mantenedor):
    modulo = 'delegaciones'
    modelo = Delegacion
    formulario = DelegacionForm
    titulo = 'Delegaciones municipales'
    singular = 'delegación'
    descripcion = 'Unidades territoriales del sistema. Un perfil por delegación solo ve las que tiene autorizadas.'
    traza = 'RF-001 · CU-02 · HU-26'
    columnas = [('codigo', 'Código'), ('nombre', 'Nombre'), ('direccion', 'Dirección'), ('comuna', 'Comuna')]
    busqueda = ['codigo', 'nombre', 'direccion', 'comuna']
    exportar = [('codigo', 'Código'), ('nombre', 'Nombre'), ('direccion', 'Dirección'), ('comuna', 'Comuna'),
                ('estado', 'Estado'), ('total_usuarios', 'Usuarios'), ('total_atenciones', 'Atenciones')]
    detalle = [('codigo', 'Código'), ('nombre', 'Nombre'), ('direccion', 'Dirección'), ('comuna', 'Comuna'),
               ('estado', 'Estado'), ('creado', 'Creada'), ('actualizado', 'Última modificación')]
    relacionados = [('usuarios', 'Usuarios asignados', [('nombre', 'Nombre'), ('rol.nombre', 'Rol'),
                                                         ('estado', 'Estado')])]

    def consulta(self, request):
        consulta = Delegacion.objects.annotate(
            total_usuarios=Count('usuarios', distinct=True), total_atenciones=Count('atenciones', distinct=True))
        if not request.user.alcance_global:
            consulta = consulta.filter(pk__in=[d.pk for d in request.delegaciones_autorizadas])
        return consulta


class Items(Mantenedor):
    modulo = 'items'
    modelo = ItemMedicion
    formulario = ItemForm
    titulo = 'Ítems y metas'
    singular = 'ítem'
    femenino = False
    descripcion = 'Ítems con los que se mide la gestión de cada cargo y se configuran las metas.'
    traza = 'RF-003, RF-004 · CU-04, CU-06 · HU-04, HU-27'
    columnas = [('codigo', 'Código'), ('nombre', 'Nombre'), ('descripcion', 'Descripción')]
    busqueda = ['codigo', 'nombre', 'descripcion']
    exportar = [('codigo', 'Código'), ('nombre', 'Nombre'), ('descripcion', 'Descripción'), ('estado', 'Estado')]
    detalle = [('codigo', 'Código'), ('nombre', 'Nombre'), ('descripcion', 'Descripción'), ('estado', 'Estado'),
               ('creado', 'Creado'), ('actualizado', 'Última modificación')]


class TiposAtencion(Mantenedor):
    modulo = 'tipos_atencion'
    modelo = TipoAtencion
    formulario = TipoAtencionForm
    titulo = 'Tipos de Atención'
    singular = 'tipo de atención'
    femenino = False
    descripcion = 'Clasificación principal de las atenciones. Un tipo con sub atenciones activas no se desactiva.'
    traza = 'RF-004 · CU-04 · HU-27'
    columnas = [('codigo', 'Código'), ('nombre', 'Nombre'), ('descripcion', 'Descripción'),
                ('total_subatenciones', 'Sub atenciones')]
    busqueda = ['codigo', 'nombre', 'descripcion']
    exportar = [('codigo', 'Código'), ('nombre', 'Nombre'), ('descripcion', 'Descripción'),
                ('total_subatenciones', 'Sub atenciones'), ('estado', 'Estado')]
    detalle = [('codigo', 'Código'), ('nombre', 'Nombre'), ('descripcion', 'Descripción'), ('estado', 'Estado'),
               ('creado', 'Creado'), ('actualizado', 'Última modificación')]
    relacionados = [('subatenciones', 'Sub atenciones asociadas', [('codigo', 'Código'), ('nombre', 'Nombre'),
                                                                    ('estado', 'Estado')])]

    def consulta(self, request):
        return TipoAtencion.objects.annotate(total_subatenciones=Count('subatenciones'))


class SubAtenciones(Mantenedor):
    modulo = 'sub_atenciones'
    modelo = SubAtencion
    formulario = SubAtencionForm
    titulo = 'Sub Atención'
    singular = 'sub atención'
    descripcion = 'Detalle de cada tipo de atención. Solo las activas de un tipo activo se ofrecen al registrar.'
    traza = 'RF-004 · CU-04 · HU-27'
    columnas = [('codigo', 'Código'), ('nombre', 'Nombre'), ('tipo.nombre', 'Tipo asociado')]
    busqueda = ['codigo', 'nombre', 'tipo__nombre', 'tipo__codigo']
    exportar = [('codigo', 'Código'), ('nombre', 'Nombre'), ('tipo.codigo', 'Código del tipo'),
                ('tipo.nombre', 'Tipo de atención'), ('estado', 'Estado')]
    detalle = [('codigo', 'Código'), ('nombre', 'Nombre'), ('tipo.nombre', 'Tipo de atención'),
               ('tipo.estado', 'Estado del tipo'), ('estado', 'Estado'), ('creado', 'Creada'),
               ('actualizado', 'Última modificación')]

    def consulta(self, request):
        consulta = SubAtencion.objects.select_related('tipo')
        tipo = request.GET.get('tipo')
        if tipo and tipo.isdigit():
            consulta = consulta.filter(Q(tipo_id=int(tipo)))
        return consulta


DELEGACIONES = Delegaciones()
ITEMS = Items()
TIPOS_ATENCION = TiposAtencion()
SUB_ATENCIONES = SubAtenciones()

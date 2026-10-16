"""
Motor común de los mantenedores (CRUD).

Cada catálogo se declara como una subclase de Mantenedor indicando su modelo,
formulario, columnas y campos de búsqueda. El motor entrega las siete
operaciones con permisos, alcance y auditoría ya resueltos:

    listar · ver · crear · editar · activar/desactivar · eliminar · exportar
"""

from functools import reduce
from operator import or_

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import capfirst
from django.views.decorators.http import require_POST

from cuentas.permisos import denegar, permiso_requerido

from .excel import respuesta_excel
from .models import Auditoria, registrar
from .reglas import motivo_no_activar, motivo_no_desactivar, motivo_no_eliminar


def valor(obj, ruta):
    """Lee 'tipo.nombre' o 'get_alcance_display' desde un objeto."""
    for parte in ruta.split('.'):
        obj = getattr(obj, parte, None)
        if callable(obj):
            obj = obj()
        if obj is None:
            return ''
    if obj is True:
        return 'Sí'
    if obj is False:
        return 'No'
    return obj


class Mantenedor:
    modulo = ''              # código del módulo en cuentas/modulos.py
    modelo = None
    formulario = None
    titulo = ''              # "Delegaciones municipales"
    singular = ''            # "delegación"
    femenino = True          # para "creada" o "creado"
    columnas = []            # [(ruta, etiqueta)]
    busqueda = []            # lookups del ORM para la búsqueda parcial
    exportar = []            # [(ruta, etiqueta)] sin contraseñas ni campos internos
    detalle = []             # [(ruta, etiqueta)]
    orden = ['codigo']
    campo_activo = 'activo'
    traza = ''
    descripcion = ''
    plantilla_formulario = 'crud/formulario.html'
    relacionados = []        # [(ruta del queryset, etiqueta, columnas)] mostrados en la ficha

    # ---------------- Ganchos que cada mantenedor puede redefinir ----------------
    def consulta(self, request):
        """Registros que el usuario puede ver según su alcance."""
        return self.modelo.objects.all()

    def puede_modificar(self, request, obj):
        return True

    def kwargs_formulario(self, request):
        return {}

    def nombre_archivo(self):
        return self.modulo.replace('_', '-')

    # ---------------- Utilidades internas ----------------
    @property
    def participio(self):
        return 'a' if self.femenino else 'o'

    def url(self, accion, **kwargs):
        return reverse(f'{self.modulo}_{accion}', kwargs=kwargs or None)

    def obtener(self, request, pk):
        """Devuelve el registro, None si existe pero está fuera del alcance del
        perfil (ruta alterada a mano) o lanza 404 si no existe."""
        try:
            return self.consulta(request).get(pk=pk)
        except (self.modelo.DoesNotExist, ValueError):
            if str(pk).isdigit() and self.modelo.objects.filter(pk=pk).exists():
                return None
            raise Http404

    def fuera_de_alcance(self, request, pk):
        return denegar(request, f'{self.modulo} #{pk} fuera del alcance del perfil')

    def filtrar(self, request):
        consulta = self.consulta(request)
        texto = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        if texto:
            palabras = texto.split()[:5]
            for palabra in palabras:
                consulta = consulta.filter(reduce(or_, (Q(**{f'{c}__icontains': palabra}) for c in self.busqueda)))
        if estado == 'activos':
            consulta = consulta.filter(**{self.campo_activo: True})
        elif estado == 'inactivos':
            consulta = consulta.filter(**{self.campo_activo: False})
        filtros = []
        if texto:
            filtros.append(('Búsqueda', texto))
        if estado:
            filtros.append(('Estado', capfirst(estado)))
        return consulta.order_by(*self.orden).distinct(), texto, estado, filtros

    def contexto(self, request, **extra):
        usuario = request.user
        return {
            'm': self,
            'puede_crear': usuario.tiene_permiso(self.modulo, 'crear'),
            'puede_editar': usuario.tiene_permiso(self.modulo, 'editar'),
            'puede_eliminar': usuario.tiene_permiso(self.modulo, 'eliminar'),
            **extra,
        }

    def _activo(self, obj):
        return getattr(obj, self.campo_activo)

    def _fijar_activo(self, obj, valor_nuevo):
        setattr(obj, self.campo_activo, valor_nuevo)
        obj.save(update_fields=[self.campo_activo, 'actualizado'])

    # ---------------- Vistas ----------------
    def vista_listar(self, request):
        consulta, texto, estado, _filtros = self.filtrar(request)
        pagina = Paginator(consulta, settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
        filas = [{'obj': o, 'celdas': [valor(o, ruta) for ruta, _ in self.columnas],
                  'activo': self._activo(o), 'modificable': self.puede_modificar(request, o)}
                 for o in pagina.object_list]
        return render(request, 'crud/lista.html', self.contexto(
            request, pagina=pagina, filas=filas, texto=texto, estado=estado,
            total_general=self.consulta(request).count()))

    def vista_exportar(self, request):
        consulta, _texto, _estado, filtros = self.filtrar(request)
        filas = [[valor(o, ruta) for ruta, _ in self.exportar] for o in consulta]
        registrar(request, 'EXPORTACION', self.modulo, detalle=f'{len(filas)} registros · '
                  + ('; '.join(f'{k}: {v}' for k, v in filtros) or 'sin filtros'))
        return respuesta_excel(self.nombre_archivo(), self.titulo, [e for _, e in self.exportar], filas,
                               filtros, request.user)

    def vista_ver(self, request, pk):
        obj = self.obtener(request, pk)
        if obj is None:
            return self.fuera_de_alcance(request, pk)
        historial = Auditoria.objects.filter(entidad=self.modulo, registro=str(obj.pk))[:8]
        return render(request, 'crud/detalle.html', self.contexto(
            request, obj=obj, campos=[(e, valor(obj, r)) for r, e in self.detalle],
            relacionados=self.relacionados_de(obj), historial=historial,
            activo=self._activo(obj), modificable=self.puede_modificar(request, obj)))

    def relacionados_de(self, obj):
        bloques = []
        for ruta, etiqueta, columnas in self.relacionados:
            consulta = getattr(obj, ruta).all()
            bloques.append({'etiqueta': etiqueta, 'total': consulta.count(),
                            'encabezados': [e for _, e in columnas],
                            'filas': [[valor(o, r) for r, _ in columnas] for o in consulta[:10]]})
        return bloques

    def vista_formulario(self, request, pk=None):
        obj = self.obtener(request, pk) if pk else None
        if pk and obj is None:
            return self.fuera_de_alcance(request, pk)
        if obj is not None and not self.puede_modificar(request, obj):
            return denegar(request, f'{self.modulo}.editar fuera de alcance')
        form = self.formulario(request.POST if request.method == 'POST' else None,
                               instance=obj, **self.kwargs_formulario(request))
        if request.method == 'POST':
            if form.is_valid():
                try:
                    with transaction.atomic():
                        estado_previo = self._activo(obj) if obj else None
                        guardado = form.save()
                        if obj is None:
                            registrar(request, 'ALTA', self.modulo, guardado.pk, str(guardado))
                        else:
                            registrar(request, 'MODIFICACION', self.modulo, guardado.pk,
                                      'Campos: ' + ', '.join(form.changed_data or ['sin cambios']))
                            if estado_previo is not None and estado_previo != self._activo(guardado):
                                registrar(request, 'CAMBIO_ESTADO', self.modulo, guardado.pk,
                                          'Activado' if self._activo(guardado) else 'Desactivado')
                except IntegrityError:
                    form.add_error(None, 'Otro usuario guardó un registro con los mismos datos. Revise e intente de nuevo.')
                else:
                    accion = 'cread' if obj is None else 'actualizad'
                    messages.success(request, f'{capfirst(self.singular)} «{guardado}» {accion}{self.participio} '
                                              'correctamente.')
                    return redirect(self.url('ver', pk=guardado.pk))
            messages.error(request, 'No se guardó. Revise los campos marcados en el formulario.')
        return render(request, self.plantilla_formulario, self.contexto(request, form=form, obj=obj))

    def vista_estado(self, request, pk):
        obj = self.obtener(request, pk)
        if obj is None:
            return self.fuera_de_alcance(request, pk)
        if not self.puede_modificar(request, obj):
            return denegar(request, f'{self.modulo}.editar fuera de alcance')
        nuevo = not self._activo(obj)
        motivo = motivo_no_activar(obj) if nuevo else motivo_no_desactivar(obj, request.user)
        if motivo:
            messages.error(request, f'No se pudo {"activar" if nuevo else "desactivar"}: {motivo}')
        else:
            self._fijar_activo(obj, nuevo)
            registrar(request, 'CAMBIO_ESTADO', self.modulo, obj.pk, 'Activado' if nuevo else 'Desactivado')
            messages.success(request, f'{capfirst(self.singular)} «{obj}» '
                                      f'{"activad" if nuevo else "desactivad"}{self.participio}.')
        volver = request.POST.get('volver', '')
        if not url_has_allowed_host_and_scheme(volver, {request.get_host()}, request.is_secure()):
            volver = self.url('lista')
        return redirect(volver)

    def vista_eliminar(self, request, pk):
        obj = self.obtener(request, pk)
        if obj is None:
            return self.fuera_de_alcance(request, pk)
        if not self.puede_modificar(request, obj):
            return denegar(request, f'{self.modulo}.eliminar fuera de alcance')
        motivo = motivo_no_eliminar(obj, request.user)
        if not motivo:
            nombre = str(obj)
            try:
                with transaction.atomic():
                    obj.delete()
            except (ProtectedError, IntegrityError):
                motivo = 'Tiene registros asociados. Puede desactivarlo en su lugar.'
            else:
                registrar(request, 'ELIMINACION', self.modulo, pk, nombre)
                messages.success(request, f'{capfirst(self.singular)} «{nombre}» eliminad{self.participio}.')
                return redirect(self.url('lista'))
        messages.error(request, f'No se pudo eliminar: {motivo}')
        return redirect(self.url('ver', pk=pk))

    # ---------------- Rutas ----------------
    def urls(self, prefijo):
        m = self.modulo
        return [
            path(f'{prefijo}/', permiso_requerido(m, 'ver')(self.vista_listar), name=f'{m}_lista'),
            path(f'{prefijo}/exportar/', permiso_requerido(m, 'ver')(self.vista_exportar), name=f'{m}_exportar'),
            path(f'{prefijo}/nuevo/', permiso_requerido(m, 'crear')(self.vista_formulario), name=f'{m}_crear'),
            path(f'{prefijo}/<int:pk>/', permiso_requerido(m, 'ver')(self.vista_ver), name=f'{m}_ver'),
            path(f'{prefijo}/<int:pk>/editar/', permiso_requerido(m, 'editar')(self.vista_formulario),
                 name=f'{m}_editar'),
            path(f'{prefijo}/<int:pk>/estado/', require_POST(permiso_requerido(m, 'editar')(self.vista_estado)),
                 name=f'{m}_estado'),
            path(f'{prefijo}/<int:pk>/eliminar/',
                 require_POST(permiso_requerido(m, 'eliminar')(self.vista_eliminar)), name=f'{m}_eliminar'),
        ]

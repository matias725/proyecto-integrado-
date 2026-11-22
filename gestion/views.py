"""
Pantallas de la matriz SGR. Cada vista declara el módulo y la acción que exige
y limita lo que muestra a la delegación activa (control de acceso por objeto).
"""

import uuid
from datetime import date, timedelta
from functools import reduce
from operator import or_

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.db.models.functions import TruncMonth
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from atenciones.models import Atencion, SeguimientoAtencion, Solicitante
from catalogos.models import Cargo, Delegacion, ItemMedicion, Sector
from core.excel import respuesta_excel
from core.models import registrar
from cuentas.models import Usuario
from cuentas.permisos import denegar, permiso_requerido

from . import calculos
from .forms import (ActividadForm, AusenciaForm, EnviarCompromisoForm, EstadoActividadForm, EvidenciaForm, MetaForm,
                    ObservacionForm, PeriodoForm, ValidacionForm, item_tubo)
from .models import (Actividad, Ausencia, Evidencia, HistorialActividad, MetaCargo, Observacion, Periodo)
from .reglas import (MAX_INGRESOS_DIARIOS, aplicar_reglas_de_puntaje, fecha_minima_de_ingreso, hoy,
                     ingresos_del_dia, validar_cupo_diario, validar_fecha_actividad)


# ---------------------------------------------------------------------------
# Utilidades de alcance
# ---------------------------------------------------------------------------
def ve_equipo(usuario):
    """Delegado, coordinación y consulta ven a todo el equipo; el funcionario, lo suyo."""
    return usuario.alcance_global or usuario.tiene_permiso('validacion', 'ver')


def equipo(request):
    """Funcionarios activos de la delegación activa."""
    if not request.delegacion_activa:
        return Usuario.objects.none()
    return (Usuario.objects.filter(delegaciones=request.delegacion_activa, is_active=True)
            .select_related('cargo', 'rol').order_by('nombre'))


def periodo_elegido(request):
    elegido = request.GET.get('periodo') or request.session.get('periodo_id')
    periodo = Periodo.objects.filter(pk=elegido).first() if str(elegido or '').isdigit() else None
    periodo = periodo or calculos.periodo_vigente()
    if periodo:
        request.session['periodo_id'] = periodo.pk
    return periodo


def actividades_visibles(request):
    if not request.delegacion_activa:
        return Actividad.objects.none()
    consulta = Actividad.objects.filter(delegacion=request.delegacion_activa)
    if not ve_equipo(request.user):
        consulta = consulta.filter(funcionario=request.user)
    return consulta.select_related('funcionario', 'item', 'organizacion', 'periodo', 'sector', 'delegacion')


def obtener_actividad(request, pk):
    actividad = Actividad.objects.select_related('funcionario', 'item', 'delegacion', 'organizacion',
                                                 'validada_por', 'periodo', 'sector').filter(pk=pk).first()
    if actividad is None:
        raise Http404
    if actividad.delegacion not in request.delegaciones_autorizadas or (
            not ve_equipo(request.user) and actividad.funcionario_id != request.user.pk):
        return None
    return actividad


def sin_periodo(request):
    messages.error(request, 'No hay un período configurado. Pida a la coordinación que abra uno.')
    return redirect('inicio')


# ---------------------------------------------------------------------------
# Tablero (hojas por cargo + SEMAFORO + RESUMEN)
# ---------------------------------------------------------------------------
@permiso_requerido('tablero', 'ver')
def tablero(request):
    periodo = periodo_elegido(request)
    if periodo is None:
        return sin_periodo(request)
    integrantes = list(equipo(request))
    resultado = calculos.indicadores(periodo, integrantes)
    fichas = resultado['fichas']
    elegido = request.GET.get('funcionario', '')
    propia = next((f for f in fichas if f['funcionario'].pk == request.user.pk), None)
    ficha = propia
    if ve_equipo(request.user):
        # Sin elección, el delegado (que no tiene metas propias) ve la primera ficha con metas del equipo
        con_metas = propia if propia and not propia['sin_metas'] else None
        ficha = next((f for f in fichas if str(f['funcionario'].pk) == elegido), None) or con_metas or (
            fichas[0] if fichas else None)
    base = actividades_visibles(request).filter(periodo=periodo)
    return render(request, 'gestion/tablero.html', {
        'periodo': periodo, 'periodos': Periodo.objects.all(), 'ficha': ficha, 'fichas': fichas,
        'esperado': resultado['esperado'], 'dias_transcurridos': resultado['dias_transcurridos'],
        'equipo': calculos.resultado_equipo(fichas, resultado['esperado'], periodo),
        've_equipo': ve_equipo(request.user),
        'alertas': calculos.alertas_de_registro(periodo, request.delegacion_activa)
        if ve_equipo(request.user) and request.delegacion_activa else [],
        'total_actividades': base.count(),
        'por_validar': base.filter(validacion=Actividad.VALIDACION_PENDIENTE).count(),
        'vencidas': base.filter(fecha_compromiso__lt=hoy()).exclude(estado=Actividad.REALIZADO).count(),
        'sin_puntaje': base.filter(puntua=False).count(),
        'ingresos_hoy': ingresos_del_dia(request.user), 'max_diario': MAX_INGRESOS_DIARIOS,
    })


# ---------------------------------------------------------------------------
# Actividades (registro diario y TUBO de trabajo)
# ---------------------------------------------------------------------------
BUSQUEDA = ['titulo', 'descripcion', 'solicitante_nombre', 'territorio', 'sector__nombre', 'organizacion__nombre',
            'funcionario__nombre', 'item__nombre', 'area_apoyo']


def _filtrar_actividades(request):
    consulta = actividades_visibles(request)
    periodo = periodo_elegido(request)
    if periodo:
        consulta = consulta.filter(periodo=periodo)
    texto = request.GET.get('q', '').strip()
    filtros = [('Delegación', request.delegacion_activa), ('Período', periodo)]
    for palabra in texto.split()[:5]:
        condicion = reduce(or_, (Q(**{f'{c}__icontains': palabra}) for c in BUSQUEDA))
        numero = palabra.upper().split('-')[-1]
        if numero.isdigit():
            condicion |= Q(pk=int(numero))
        consulta = consulta.filter(condicion)
    if texto:
        filtros.append(('Búsqueda', texto))
    estado = request.GET.get('estado', '')
    if estado in dict(Actividad.ESTADOS):
        consulta = consulta.filter(estado=estado)
        filtros.append(('Estado', dict(Actividad.ESTADOS)[estado]))
    puntaje = request.GET.get('puntaje', '')
    if puntaje in ('si', 'no'):
        consulta = consulta.filter(puntua=puntaje == 'si')
        filtros.append(('Suma puntaje', 'Sí' if puntaje == 'si' else 'No'))
    funcionario = request.GET.get('funcionario', '')
    if funcionario.isdigit() and ve_equipo(request.user):
        consulta = consulta.filter(funcionario_id=int(funcionario))
        filtros.append(('Funcionario', Usuario.objects.filter(pk=funcionario).first()))
    return consulta, texto, filtros


@permiso_requerido('actividades', 'ver')
def actividades(request):
    consulta, texto, _filtros = _filtrar_actividades(request)
    pagina = Paginator(consulta, settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
    return render(request, 'gestion/actividades.html', {
        'pagina': pagina, 'texto': texto, 'estados': Actividad.ESTADOS, 'estado': request.GET.get('estado', ''),
        'puntaje': request.GET.get('puntaje', ''), 'funcionario': request.GET.get('funcionario', ''),
        'integrantes': equipo(request) if ve_equipo(request.user) else [],
        'periodo': periodo_elegido(request), 'periodos': Periodo.objects.all(),
        'puede_crear': request.user.tiene_permiso('actividades', 'crear'),
        'ingresos_hoy': ingresos_del_dia(request.user), 'max_diario': MAX_INGRESOS_DIARIOS,
    })


@permiso_requerido('actividades', 'ver')
def actividades_exportar(request):
    consulta, _texto, filtros = _filtrar_actividades(request)
    filas = [[a.folio, a.fecha, a.ingresada_el, a.funcionario.nombre, a.item.nombre, a.get_naturaleza_display(),
              a.origen, a.titulo, a.solicitante_nombre, a.solicitante_telefono,
              a.organizacion.nombre if a.organizacion else '', a.sector.nombre if a.sector else '', a.territorio,
              a.get_estado_display(),
              a.fecha_compromiso, a.get_validacion_display(), 'Sí' if a.puntua else 'No', a.motivo_sin_puntaje]
             for a in consulta]
    registrar(request, 'EXPORTACION', 'actividades', detalle=f'{len(filas)} registros')
    return respuesta_excel('actividades', 'TUBO de trabajo y actividades',
                           ['Folio', 'Fecha', 'Ingresada el', 'Responsable', 'Ítem', 'Naturaleza', 'INT/EXT',
                            'Actividad', 'Usuario', 'Teléfono', 'Organización', 'Sector', 'Referencia', 'Estado',
                            'Compromiso', 'Validación', 'Suma puntaje', 'Motivo sin puntaje'],
                           filas, filtros, request.user)


@permiso_requerido('actividades', 'crear')
def actividad_nueva(request):
    if not request.delegacion_activa:
        messages.error(request, 'Su cuenta no tiene una delegación autorizada.')
        return redirect('inicio')
    periodo = Periodo.objects.filter(estado=Periodo.ABIERTO).first()
    if periodo is None:
        return sin_periodo(request)
    if not request.user.cargo_id:
        messages.warning(request, 'Su cuenta no tiene cargo asignado: sus actividades no se medirán en la matriz.')

    kwargs = {'funcionario': request.user, 'delegacion': request.delegacion_activa}
    if request.method == 'POST':
        form = ActividadForm(request.POST, **kwargs)
        previa = Actividad.objects.filter(token_envio=request.POST.get('token_envio') or None,
                                          funcionario=request.user).first()
        if previa:
            messages.info(request, f'La actividad {previa.folio} ya estaba registrada. No se creó un duplicado.')
            return redirect('actividad_ver', pk=previa.pk)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Regla 3 dentro de la transacción: bloquea la fila del funcionario para que dos
                    # envíos simultáneos no superen el máximo diario.
                    Usuario.objects.select_for_update().filter(pk=request.user.pk).first()
                    validar_cupo_diario(request.user)
                    validar_fecha_actividad(form.cleaned_data['fecha'])
                    actividad = form.save(commit=False)
                    actividad.funcionario = request.user
                    actividad.delegacion = request.delegacion_activa
                    actividad.periodo = periodo
                    actividad.ingresada_el = hoy()
                    actividad.token_envio = form.cleaned_data['token_envio']
                    if actividad.estado == Actividad.REALIZADO:
                        actividad.fecha_cierre = actividad.fecha
                    aplicar_reglas_de_puntaje(actividad)
                    actividad.save()
                    HistorialActividad.objects.create(actividad=actividad, usuario=request.user,
                                                      estado_nuevo=actividad.estado, observacion='Ingreso')
            except ValidationError as error:
                form.add_error(None, error)
            except IntegrityError:
                previa = Actividad.objects.filter(token_envio=form.cleaned_data['token_envio']).first()
                if previa:
                    return redirect('actividad_ver', pk=previa.pk)
                form.add_error(None, 'No se pudo guardar. Intente nuevamente.')
            else:
                registrar(request, 'ALTA', 'actividades', actividad.pk, f'{actividad.folio} · {actividad.item}')
                if actividad.puntua:
                    messages.success(request, f'Actividad {actividad.folio} registrada. Suma puntaje en '
                                              f'«{actividad.item}»' + (' cuando quede realizada.'
                                                                      if actividad.estado != Actividad.REALIZADO
                                                                      else '.'))
                else:
                    messages.warning(request, f'Actividad {actividad.folio} registrada sin puntaje. '
                                              f'{actividad.motivo_sin_puntaje}')
                return redirect('actividad_ver', pk=actividad.pk)
        messages.error(request, 'No se guardó. Revise los campos marcados en el formulario.')
    else:
        form = ActividadForm(initial={'token_envio': uuid.uuid4(), 'fecha': hoy(), 'estado': Actividad.REALIZADO},
                             **kwargs)
    return render(request, 'gestion/actividad_nueva.html', {
        'form': form, 'periodo': periodo, 'ingresos_hoy': ingresos_del_dia(request.user),
        'max_diario': MAX_INGRESOS_DIARIOS, 'fecha_minima': fecha_minima_de_ingreso(), 'hoy': hoy(),
    })


@permiso_requerido('actividades', 'ver')
def actividad_ver(request, pk):
    actividad = obtener_actividad(request, pk)
    if actividad is None:
        return denegar(request, f'actividad {pk} fuera de alcance')
    es_responsable = actividad.funcionario_id == request.user.pk
    puede_seguir = es_responsable or request.user.tiene_permiso('validacion', 'editar')
    return render(request, 'gestion/actividad_ver.html', {
        'a': actividad, 'historial': actividad.historial.select_related('usuario'),
        'evidencias': actividad.evidencias.select_related('subida_por'),
        'form_estado': EstadoActividadForm(actividad=actividad) if puede_seguir and actividad.periodo.abierto else None,
        'form_evidencia': EvidenciaForm() if (es_responsable and request.user.tiene_permiso('evidencias', 'crear')
                                              and actividad.periodo.abierto) else None,
        'puede_validar': (request.user.tiene_permiso('validacion', 'editar') and not es_responsable
                          and actividad.periodo.abierto),
        'nueva': request.GET.get('nueva') == '1',
    })


@require_POST
@permiso_requerido('actividades', 'crear')
def actividad_estado(request, pk):
    actividad = obtener_actividad(request, pk)
    if actividad is None:
        return denegar(request, f'actividad {pk} fuera de alcance')
    if actividad.funcionario_id != request.user.pk and not request.user.tiene_permiso('validacion', 'editar'):
        return denegar(request, f'actividad {pk}: solo el responsable o el delegado cambian su estado')
    if not actividad.periodo.abierto:
        messages.error(request, 'El período está cerrado: sus actividades ya no se modifican.')
        return redirect('actividad_ver', pk=pk)
    form = EstadoActividadForm(request.POST, actividad=actividad)
    if form.is_valid():
        anterior = actividad.estado
        actividad.estado = form.cleaned_data['estado']
        actividad.fecha_cierre = hoy() if actividad.estado == Actividad.REALIZADO else None
        actividad.save(update_fields=['estado', 'fecha_cierre'])
        HistorialActividad.objects.create(actividad=actividad, usuario=request.user, estado_anterior=anterior,
                                          estado_nuevo=actividad.estado, observacion=form.cleaned_data['observacion'])
        registrar(request, 'CAMBIO_ESTADO', 'actividades', actividad.pk, f'{anterior} → {actividad.estado}')
        messages.success(request, f'{actividad.folio} quedó «{actividad.get_estado_display()}».')
    else:
        messages.error(request, ' '.join(e for errores in form.errors.values() for e in errores))
    return redirect('actividad_ver', pk=pk)


# ---------------------------------------------------------------------------
# Evidencias
# ---------------------------------------------------------------------------
@require_POST
@permiso_requerido('evidencias', 'crear')
def evidencia_subir(request, pk):
    actividad = obtener_actividad(request, pk)
    if actividad is None or actividad.funcionario_id != request.user.pk:
        return denegar(request, f'evidencia para actividad {pk} ajena')
    form = EvidenciaForm(request.POST, request.FILES)
    if form.is_valid():
        archivo = form.cleaned_data['archivo']
        evidencia = Evidencia.objects.create(
            actividad=actividad, archivo=archivo, nombre_original=archivo.name[:150], tipo_mime=form.tipo_mime,
            tamano=archivo.size, descripcion=form.cleaned_data['descripcion'], subida_por=request.user)
        registrar(request, 'ALTA', 'evidencias', evidencia.pk, f'{actividad.folio} · {evidencia.nombre_original}')
        messages.success(request, 'Evidencia adjuntada.')
    else:
        messages.error(request, ' '.join(e for errores in form.errors.values() for e in errores))
    return redirect('actividad_ver', pk=pk)


@permiso_requerido('evidencias', 'ver')
def evidencias(request):
    consulta = Evidencia.objects.filter(actividad__in=actividades_visibles(request)).select_related(
        'actividad', 'actividad__funcionario', 'subida_por')
    pagina = Paginator(consulta, settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
    return render(request, 'gestion/evidencias.html', {'pagina': pagina})


@permiso_requerido('evidencias', 'ver')
def evidencia_descargar(request, pk):
    """Los archivos no se publican en una carpeta abierta: se entregan tras validar el alcance."""
    evidencia = get_object_or_404(Evidencia.objects.select_related('actividad'), pk=pk)
    if obtener_actividad(request, evidencia.actividad_id) is None:
        return denegar(request, f'evidencia {pk} fuera de alcance')
    return FileResponse(evidencia.archivo.open('rb'), as_attachment=True, filename=evidencia.nombre_original,
                        content_type=evidencia.tipo_mime)


# ---------------------------------------------------------------------------
# Validación por el delegado
# ---------------------------------------------------------------------------
@permiso_requerido('validacion', 'ver')
def validacion(request):
    consulta = actividades_visibles(request).filter(validacion=Actividad.VALIDACION_PENDIENTE,
                                                    periodo__estado=Periodo.ABIERTO).annotate(
        total_evidencias=Count('evidencias')).order_by('fecha', 'id')
    pagina = Paginator(consulta, settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
    return render(request, 'gestion/validacion.html', {
        'pagina': pagina, 'puede_validar': request.user.tiene_permiso('validacion', 'editar')})


@require_POST
@permiso_requerido('validacion', 'editar')
def validar(request, pk):
    actividad = obtener_actividad(request, pk)
    if actividad is None:
        return denegar(request, f'validación de actividad {pk} fuera de alcance')
    if actividad.funcionario_id == request.user.pk:
        return denegar(request, f'actividad {pk}: nadie valida sus propias actividades')
    form = ValidacionForm(request.POST)
    if not actividad.periodo.abierto:
        messages.error(request, 'El período está cerrado.')
    elif form.is_valid():
        actividad.validacion = form.cleaned_data['decision']
        actividad.motivo_rechazo = form.cleaned_data['motivo'] if actividad.validacion == Actividad.RECHAZADA else ''
        actividad.validada_por, actividad.validada_en = request.user, timezone.now()
        actividad.save(update_fields=['validacion', 'motivo_rechazo', 'validada_por', 'validada_en'])
        registrar(request, 'MODIFICACION', 'validacion', actividad.pk,
                  f'{actividad.folio} {actividad.validacion} {actividad.motivo_rechazo}'[:500])
        messages.success(request, f'{actividad.folio} {actividad.get_validacion_display().lower()}.')
    else:
        messages.error(request, ' '.join(e for errores in form.errors.values() for e in errores))
    destino = request.POST.get('volver')
    return redirect('validacion' if destino == 'bandeja' else reverse('actividad_ver', args=[pk]))


# ---------------------------------------------------------------------------
# Agenda colectiva: solicitudes del TUBO con fecha de compromiso
# ---------------------------------------------------------------------------
PLAZOS = [('vencidas', 'Vencidas'), ('semana', 'Vencen en 7 días'), ('al_dia', 'Al día (más de 7 días)'),
          ('realizadas', 'Realizadas')]
# El TUBO completo vive en Compromisos: por defecto en tarjetas por estado; «tablero» queda como alias
VISTAS_AGENDA = ('tubo', 'tabla')


def _fecha_get(request, clave):
    try:
        return date.fromisoformat(request.GET.get(clave, ''))
    except ValueError:
        return None


def _filtrar_compromisos(request):
    """Compromisos del TUBO (actividades con fecha de compromiso) según los filtros de la tabla."""
    periodo = periodo_elegido(request)
    consulta = actividades_visibles(request).filter(fecha_compromiso__isnull=False)
    if periodo:
        consulta = consulta.filter(periodo=periodo)
    filtros = [('Delegación', request.delegacion_activa), ('Período', periodo)]
    elegidos = {}
    texto = request.GET.get('q', '').strip()
    for palabra in texto.split()[:5]:
        condicion = reduce(or_, (Q(**{f'{c}__icontains': palabra}) for c in BUSQUEDA))
        numero = palabra.upper().split('-')[-1]
        if numero.isdigit():
            condicion |= Q(pk=int(numero))
        consulta = consulta.filter(condicion)
    if texto:
        filtros.append(('Búsqueda', texto))
    estado = request.GET.get('estado', '')
    if estado in dict(Actividad.ESTADOS):
        consulta = consulta.filter(estado=estado)
        filtros.append(('Estado', dict(Actividad.ESTADOS)[estado]))
        elegidos['estado'] = estado
    funcionario = request.GET.get('funcionario', '')
    if funcionario.isdigit() and ve_equipo(request.user):
        consulta = consulta.filter(funcionario_id=int(funcionario))
        filtros.append(('Responsable', Usuario.objects.filter(pk=funcionario).first()))
        elegidos['funcionario'] = funcionario
    sector = request.GET.get('sector', '')
    if sector == 'ninguno':
        consulta = consulta.filter(sector__isnull=True)
        filtros.append(('Sector', 'Sin sector'))
        elegidos['sector'] = sector
    elif sector.isdigit():
        consulta = consulta.filter(sector_id=int(sector))
        filtros.append(('Sector', Sector.objects.filter(pk=sector).first()))
        elegidos['sector'] = sector
    plazo, dia = request.GET.get('plazo', ''), hoy()
    pendientes = consulta.exclude(estado=Actividad.REALIZADO)
    if plazo == 'vencidas':
        consulta = pendientes.filter(fecha_compromiso__lt=dia)
    elif plazo == 'semana':
        consulta = pendientes.filter(fecha_compromiso__gte=dia, fecha_compromiso__lte=dia + timedelta(days=7))
    elif plazo == 'al_dia':
        consulta = pendientes.filter(fecha_compromiso__gt=dia + timedelta(days=7))
    elif plazo == 'realizadas':
        consulta = consulta.filter(estado=Actividad.REALIZADO)
    if plazo in dict(PLAZOS):
        filtros.append(('Plazo', dict(PLAZOS)[plazo]))
        elegidos['plazo'] = plazo
    desde, hasta = _fecha_get(request, 'desde'), _fecha_get(request, 'hasta')
    if desde:
        consulta = consulta.filter(fecha_compromiso__gte=desde)
        filtros.append(('Compromiso desde', desde))
    if hasta:
        consulta = consulta.filter(fecha_compromiso__lte=hasta)
        filtros.append(('Compromiso hasta', hasta))
    # Primero lo pendiente por fecha de compromiso (lo más urgente arriba); al final lo realizado
    consulta = consulta.annotate(cerrada=Case(When(estado=Actividad.REALIZADO, then=Value(1)), default=Value(0),
                                              output_field=IntegerField())).order_by('cerrada', 'fecha_compromiso',
                                                                                      'id')
    return consulta, periodo, texto, elegidos, desde, hasta, filtros


@permiso_requerido('agenda', 'ver')
def agenda(request):
    consulta, periodo, texto, elegidos, desde, hasta, _filtros = _filtrar_compromisos(request)
    vista = request.GET.get('vista', 'tubo')
    vista = 'tubo' if vista == 'tablero' else vista
    vista = vista if vista in VISTAS_AGENDA else 'tubo'
    por_estado = dict(consulta.order_by().values_list('estado').annotate(n=Count('id')))
    total = sum(por_estado.values())
    resueltas = por_estado.get(Actividad.REALIZADO, 0)
    vencidas = consulta.filter(fecha_compromiso__lt=hoy()).exclude(estado=Actividad.REALIZADO).count()
    contexto = {
        'periodo': periodo, 'periodos': Periodo.objects.all(), 'hoy': hoy(), 'vista': vista, 'texto': texto,
        'estados': Actividad.ESTADOS, 'plazos': PLAZOS, 'desde': desde, 'hasta': hasta, **elegidos,
        'integrantes': equipo(request) if ve_equipo(request.user) else [],
        'sectores': Sector.objects.filter(delegacion=request.delegacion_activa).order_by('nombre')
        if request.delegacion_activa else [],
        'hay_filtros': bool(texto or elegidos or desde or hasta),
        'total': total, 'resueltas': resueltas, 'vencidas': vencidas,
        'porcentaje': resueltas / total * 100 if total else 0,
        'en_proceso': por_estado.get(Actividad.EN_PROCESO, 0),
        'por_iniciar': por_estado.get(Actividad.INGRESADO, 0) + por_estado.get(Actividad.PENDIENTE, 0),
    }
    if vista == 'tubo':
        contexto['columnas'] = [{'codigo': codigo, 'nombre': nombre, 'total': por_estado.get(codigo, 0),
                                 'filas': list(consulta.filter(estado=codigo)[:30])}
                                for codigo, nombre in Actividad.ESTADOS]
    else:
        contexto['pagina'] = Paginator(consulta, settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
    return render(request, 'gestion/agenda.html', contexto)


@permiso_requerido('agenda', 'ver')
def agenda_exportar(request):
    consulta, _periodo, _texto, _elegidos, _desde, _hasta, filtros = _filtrar_compromisos(request)
    filas = []
    for a in consulta:
        dias = a.dias_compromiso
        filas.append([a.folio, a.fecha, a.fecha_compromiso,
                      '' if dias is None else (f'{-dias} días de atraso' if dias < 0 else f'faltan {dias} días'),
                      a.titulo, a.solicitante_nombre, a.organizacion.nombre if a.organizacion else '',
                      a.sector.nombre if a.sector else '', a.territorio, a.funcionario.nombre, a.area_apoyo,
                      a.get_estado_display(), a.fecha_cierre, a.get_validacion_display()])
    registrar(request, 'EXPORTACION', 'agenda', detalle=f'{len(filas)} compromisos · '
              + '; '.join(f'{k}: {v}' for k, v in filtros[2:]) if filtros[2:] else f'{len(filas)} compromisos')
    return respuesta_excel('compromisos-tubo', 'Compromisos del TUBO de trabajo',
                           ['Folio', 'Fecha solicitud', 'Fecha compromiso', 'Plazo', 'Actividad', 'Solicitante',
                            'Organización', 'Sector', 'Referencia', 'Responsable', 'Área de apoyo', 'Estado',
                            'Fecha de cierre', 'Validación'], filas, filtros, request.user)


# ---------------------------------------------------------------------------
# «Enviar a compromiso»: una atención ciudadana pasa al TUBO de Compromisos
# ---------------------------------------------------------------------------
@require_POST
@permiso_requerido('actividades', 'crear')
def atencion_a_compromiso(request, pk):
    atencion = get_object_or_404(Atencion.objects.select_related('solicitante', 'tipo', 'subatencion',
                                                                 'delegacion'), pk=pk)
    volver = reverse('atenciones_ver', args=[pk]) + '#enviar-compromiso'
    if atencion.delegacion not in request.delegaciones_autorizadas:
        return denegar(request, f'atención {pk} de otra delegación')
    previa = Actividad.objects.filter(atencion=atencion).first()
    if previa:
        messages.info(request, f'La atención {atencion.folio} ya está en Compromisos como {previa.folio}.')
        return redirect(volver)
    if not atencion.abierta:
        messages.error(request, 'La atención está cerrada: reábrala para enviarla a compromiso.')
        return redirect(volver)
    periodo = Periodo.objects.filter(estado=Periodo.ABIERTO).first()
    if periodo is None or not periodo.contiene(hoy()):
        messages.error(request, 'No hay un trimestre abierto que incluya el día de hoy.')
        return redirect(volver)
    item = item_tubo(request.user, periodo)
    if item is None:
        messages.error(request, 'No hay un ítem de tipo TUBO activo en la matriz. Pida a la coordinación que lo cree.')
        return redirect(volver)
    form = EnviarCompromisoForm(request.POST, delegacion=atencion.delegacion)
    if not form.is_valid():
        for errores in form.errors.values():
            for mensaje in errores:
                messages.error(request, mensaje)
        return redirect(volver)
    d = form.cleaned_data
    solicitante = atencion.solicitante
    try:
        with transaction.atomic():
            Usuario.objects.select_for_update().filter(pk=request.user.pk).first()
            validar_cupo_diario(request.user)
            actividad = Actividad(
                periodo=periodo, delegacion=atencion.delegacion, funcionario=request.user, item=item,
                naturaleza=Actividad.ACCION, fecha=hoy(), ingresada_el=hoy(), atencion=atencion,
                titulo=f'{atencion.tipo.nombre} · {atencion.subatencion.nombre}'[:200],
                descripcion=f'{atencion.descripcion}\n\nOrigen: atención {atencion.folio}.'[:1500],
                solicitante_nombre=solicitante.nombre, solicitante_telefono=solicitante.telefono,
                organizacion=d['organizacion'], sector=d['sector'], area_apoyo=d['area_apoyo'],
                estado=Actividad.INGRESADO, fecha_compromiso=d['fecha_compromiso'])
            aplicar_reglas_de_puntaje(actividad)
            actividad.save()
            HistorialActividad.objects.create(actividad=actividad, usuario=request.user,
                                              estado_nuevo=actividad.estado,
                                              observacion=f'Ingreso desde la atención {atencion.folio}')
            SeguimientoAtencion.objects.create(
                atencion=atencion, usuario=request.user,
                comentario=f'Enviada a compromiso ({actividad.folio}) con fecha {actividad.fecha_compromiso:%d-%m-%Y}.')
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return redirect(volver)
    except IntegrityError:
        messages.info(request, f'La atención {atencion.folio} ya estaba en Compromisos.')
        return redirect(volver)
    registrar(request, 'ALTA', 'actividades', actividad.pk, f'{actividad.folio} · compromiso desde {atencion.folio}')
    messages.success(request, f'Atención enviada a Compromisos como {actividad.folio}, '
                              f'con compromiso al {actividad.fecha_compromiso:%d-%m-%Y}.')
    return redirect(volver)


# ---------------------------------------------------------------------------
# Atención social: historial por vecino a partir de las atenciones reales
# ---------------------------------------------------------------------------
@permiso_requerido('atencion_social', 'ver')
def atencion_social(request):
    delegacion = request.delegacion_activa
    texto = request.GET.get('q', '').strip()
    consulta = Solicitante.objects.filter(atenciones__delegacion=delegacion).annotate(
        total=Count('atenciones', filter=Q(atenciones__delegacion=delegacion))).order_by('-total', 'nombre')
    if texto:
        consulta = consulta.filter(Q(nombre__icontains=texto) | Q(rut__icontains=texto))
    pagina = Paginator(consulta.distinct(), settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
    elegido = request.GET.get('rut', '')
    caso = None
    if elegido:
        # El vecino puede venir de sus atenciones o de la directiva de una organización de la delegación
        solicitante = Solicitante.objects.filter(
            Q(atenciones__delegacion=delegacion) | Q(cargos_directiva__organizacion__delegacion=delegacion),
            rut=elegido).first()
        if solicitante:
            caso = {'solicitante': solicitante, 'atenciones': Atencion.objects.filter(
                solicitante=solicitante, delegacion=delegacion).select_related('tipo', 'subatencion', 'responsable'),
                'cargos': solicitante.cargos_directiva.select_related('organizacion').order_by('organizacion__nombre')}
    return render(request, 'gestion/atencion_social.html', {'pagina': pagina, 'texto': texto, 'caso': caso})


# ---------------------------------------------------------------------------
# Semáforo: ausencias (regla 9)
# ---------------------------------------------------------------------------
@permiso_requerido('ausencias', 'ver')
def ausencias(request):
    periodo = periodo_elegido(request)
    if periodo is None:
        return sin_periodo(request)
    integrantes = equipo(request)
    form = None
    if request.user.tiene_permiso('ausencias', 'crear') and periodo.abierto:
        form = AusenciaForm(request.POST or None, funcionarios=integrantes.exclude(pk=request.user.pk),
                            periodo=periodo)
        if request.method == 'POST':
            if form.is_valid():
                ausencia = form.save(commit=False)
                ausencia.periodo, ausencia.registrada_por = periodo, request.user
                ausencia.save()
                registrar(request, 'ALTA', 'ausencias', ausencia.pk, f'{ausencia.funcionario} · {ausencia}')
                messages.success(request, f'Ausencia registrada. La meta de {ausencia.funcionario} se ajusta '
                                          f'en {ausencia.dias} días.')
                return redirect('ausencias')
            messages.error(request, 'No se guardó. Revise los campos marcados.')
    elif request.method == 'POST':
        return denegar(request, 'ausencias.crear')
    resultado = calculos.indicadores(periodo, list(integrantes))
    return render(request, 'gestion/ausencias.html', {
        'periodo': periodo, 'form': form, 'fichas': resultado['fichas'], 'esperado': resultado['esperado'],
        'ausencias': Ausencia.objects.filter(periodo=periodo, funcionario__in=integrantes).select_related(
            'funcionario', 'registrada_por')})


@require_POST
@permiso_requerido('ausencias', 'eliminar')
def ausencia_eliminar(request, pk):
    ausencia = get_object_or_404(Ausencia, pk=pk)
    if not equipo(request).filter(pk=ausencia.funcionario_id).exists() or not ausencia.periodo.abierto:
        return denegar(request, f'ausencia {pk} fuera de alcance')
    registrar(request, 'ELIMINACION', 'ausencias', pk, f'{ausencia.funcionario} · {ausencia}')
    ausencia.delete()
    messages.success(request, 'Ausencia eliminada; la meta vuelve a calcularse.')
    return redirect('ausencias')


# ---------------------------------------------------------------------------
# Felicitaciones y reclamos (regla 8)
# ---------------------------------------------------------------------------
@permiso_requerido('observaciones', 'ver')
def observaciones(request):
    periodo = periodo_elegido(request)
    if periodo is None:
        return sin_periodo(request)
    integrantes = equipo(request)
    form = None
    if request.user.tiene_permiso('observaciones', 'crear') and periodo.abierto:
        form = ObservacionForm(request.POST or None, request.FILES or None,
                               funcionarios=integrantes.exclude(pk=request.user.pk), periodo=periodo,
                               actor=request.user)
        if request.method == 'POST':
            if form.is_valid():
                obs = form.save(commit=False)
                obs.periodo, obs.registrada_por = periodo, request.user
                obs.respaldo_nombre = form.cleaned_data['respaldo'].name[:150]
                obs.save()
                registrar(request, 'ALTA', 'observaciones', obs.pk, str(obs))
                messages.success(request, f'{obs.get_tipo_display()} registrada para {obs.funcionario}.')
                return redirect('observaciones')
            messages.error(request, 'No se guardó. Revise los campos marcados.')
    elif request.method == 'POST':
        return denegar(request, 'observaciones.crear')
    consulta = Observacion.objects.filter(periodo=periodo, funcionario__in=integrantes)
    if not ve_equipo(request.user):
        consulta = consulta.filter(funcionario=request.user)
    return render(request, 'gestion/observaciones.html', {
        'periodo': periodo, 'form': form,
        'registros': consulta.select_related('funcionario', 'registrada_por')})


@permiso_requerido('observaciones', 'ver')
def observacion_respaldo(request, pk):
    obs = get_object_or_404(Observacion, pk=pk)
    if not equipo(request).filter(pk=obs.funcionario_id).exists() or (
            not ve_equipo(request.user) and obs.funcionario_id != request.user.pk):
        return denegar(request, f'respaldo {pk} fuera de alcance')
    return FileResponse(obs.respaldo.open('rb'), as_attachment=True, filename=obs.respaldo_nombre)


# ---------------------------------------------------------------------------
# Configuración: períodos y metas
# ---------------------------------------------------------------------------
def parametros_periodo(periodo):
    """Parámetros de cálculo con su explicación, para mostrarlos como tarjetas."""
    return [
        ('bi-graph-up-arrow', 'Tope por ítem', f'{periodo.tope_item} %',
         'Sobre este cumplimiento un ítem ya no suma (regla 7).'),
        ('bi-trophy', 'Tope total', f'{periodo.tope_total} %',
         'Máximo de un funcionario, incluidas las felicitaciones.'),
        ('bi-award', 'Felicitación', f'+{periodo.bono_felicitacion} %',
         f'Por cada una con respaldo, hasta {periodo.max_felicitaciones} (regla 8).'),
        ('bi-exclamation-octagon', 'Reclamo', f'−{periodo.descuento_reclamo} %',
         'Se descuenta del total por cada reclamo formal.'),
        ('bi-speedometer', 'Umbral naranjo', f'{periodo.umbral_naranjo} %',
         'Bajo este % de lo esperado al día, el semáforo pasa a rojo.'),
        ('bi-check2-circle', 'Cumplimiento mínimo', f'{periodo.cumplimiento_minimo} %',
         'Bajo este total se marca al funcionario en el tablero.'),
    ]


@permiso_requerido('periodos', 'ver')
def periodos(request):
    form = None
    if request.user.tiene_permiso('periodos', 'crear'):
        form = PeriodoForm(request.POST or None)
        if request.method == 'POST':
            if form.is_valid():
                periodo = form.save(commit=False)
                periodo.estado = Periodo.CERRADO      # se abre explícitamente
                periodo.save()
                registrar(request, 'ALTA', 'periodos', periodo.pk, str(periodo))
                messages.success(request, f'{periodo} creado. Copie las metas y ábralo cuando corresponda.')
                return redirect('periodo_ver', pk=periodo.pk)
            messages.error(request, 'No se guardó. Revise los campos marcados.')
    elif request.method == 'POST':
        return denegar(request, 'periodos.crear')
    lista = list(Periodo.objects.annotate(
        total_metas=Count('metas', distinct=True), total_cargos=Count('metas__cargo', distinct=True),
        total_actividades=Count('actividades', distinct=True),
        total_realizadas=Count('actividades', filter=Q(actividades__estado=Actividad.REALIZADO), distinct=True)))
    abierto = next((p for p in lista if p.abierto), None)
    resumen = None
    if abierto:
        base = Actividad.objects.filter(periodo=abierto)
        if not request.user.alcance_global:
            base = base.filter(delegacion__in=request.delegaciones_autorizadas)
        resumen = base.aggregate(
            total=Count('id'), realizadas=Count('id', filter=Q(estado=Actividad.REALIZADO)),
            suman=Count('id', filter=Q(puntua=True)),
            por_validar=Count('id', filter=Q(validacion=Actividad.VALIDACION_PENDIENTE)),
            vencidas=Count('id', filter=Q(fecha_compromiso__lt=hoy()) & ~Q(estado=Actividad.REALIZADO)))
        resumen['funcionarios'] = base.values('funcionario').distinct().count()
    return render(request, 'gestion/periodos.html', {
        'form': form, 'periodos': lista, 'abierto': abierto, 'resumen': resumen,
        'parametros': parametros_periodo(abierto) if abierto else [],
        'alcance_global': request.user.alcance_global,
        'puede_editar': request.user.tiene_permiso('periodos', 'editar')})


@permiso_requerido('periodos', 'ver')
def periodo_ver(request, pk):
    """Detalle de un período: línea de tiempo, parámetros, actividades y resultado por delegación y cargo."""
    periodo = get_object_or_404(Periodo, pk=pk)
    autorizadas = list(Delegacion.objects.filter(activo=True)) if request.user.alcance_global \
        else list(request.delegaciones_autorizadas)
    base = Actividad.objects.filter(periodo=periodo, delegacion__in=autorizadas)
    total = base.count()
    conteo_estado = dict(base.order_by().values_list('estado').annotate(n=Count('id')))
    maximo = max(conteo_estado.values(), default=0)
    por_estado = [{'codigo': c, 'nombre': n, 'total': conteo_estado.get(c, 0),
                   'ancho': conteo_estado.get(c, 0) / maximo * 100 if maximo else 0} for c, n in Actividad.ESTADOS]
    por_mes = list(base.annotate(mes=TruncMonth('fecha')).order_by('mes').values('mes').annotate(
        total=Count('id'), realizadas=Count('id', filter=Q(estado=Actividad.REALIZADO))))
    maximo_mes = max((m['total'] for m in por_mes), default=0)
    for m in por_mes:
        m['ancho'] = m['total'] / maximo_mes * 100 if maximo_mes else 0
    totales = base.aggregate(
        realizadas=Count('id', filter=Q(estado=Actividad.REALIZADO)), suman=Count('id', filter=Q(puntua=True)),
        validadas=Count('id', filter=Q(validacion=Actividad.VALIDADA)),
        rechazadas=Count('id', filter=Q(validacion=Actividad.RECHAZADA)),
        por_validar=Count('id', filter=Q(validacion=Actividad.VALIDACION_PENDIENTE)),
        compromisos=Count('id', filter=Q(fecha_compromiso__isnull=False)),
        vencidas=Count('id', filter=Q(fecha_compromiso__lt=hoy()) & ~Q(estado=Actividad.REALIZADO)))
    # Resultado del equipo por delegación (regla 10), con el mismo cálculo del tablero
    por_delegacion = []
    conteo_delegacion = {f['delegacion_id']: f for f in base.order_by().values('delegacion_id').annotate(
        total=Count('id'), realizadas=Count('id', filter=Q(estado=Actividad.REALIZADO)),
        suman=Count('id', filter=Q(puntua=True)))}
    for delegacion in autorizadas:
        funcionarios = list(Usuario.objects.filter(delegaciones=delegacion, is_active=True, cargo__isnull=False)
                            .select_related('cargo'))
        resultado = calculos.indicadores(periodo, funcionarios)
        equipo_del = calculos.resultado_equipo(resultado['fichas'], resultado['esperado'], periodo)
        datos = conteo_delegacion.get(delegacion.pk, {})
        por_delegacion.append({'delegacion': delegacion, 'equipo': equipo_del, 'total': datos.get('total', 0),
                               'realizadas': datos.get('realizadas', 0), 'suman': datos.get('suman', 0),
                               'ancho': min(equipo_del['promedio'], 100) if equipo_del else 0})
    metas_cargo = list(MetaCargo.objects.filter(periodo=periodo).values('cargo__codigo', 'cargo__nombre').annotate(
        items=Count('id'), ponderacion=Sum('ponderador')).order_by('cargo__codigo'))
    for m in metas_cargo:
        m['completa'] = abs(float(m['ponderacion'] or 0) - 100) < 0.01
    ausencias = Ausencia.objects.filter(periodo=periodo, funcionario__delegaciones__in=autorizadas).distinct()
    observaciones = dict(Observacion.objects.filter(periodo=periodo, funcionario__delegaciones__in=autorizadas)
                         .order_by().values_list('tipo').annotate(n=Count('id', distinct=True)))
    return render(request, 'gestion/periodo_ver.html', {
        'periodo': periodo, 'parametros': parametros_periodo(periodo), 'total': total, 'totales': totales,
        'por_estado': por_estado, 'por_mes': por_mes, 'por_delegacion': por_delegacion, 'metas_cargo': metas_cargo,
        'esperado': calculos.esperado_al_dia(periodo), 'ausencias': ausencias.count(),
        'dias_ausencia': sum(calculos.dias_ausencia(periodo, [a.funcionario_id for a in ausencias]).values()),
        'felicitaciones': observaciones.get(Observacion.FELICITACION, 0),
        'reclamos': observaciones.get(Observacion.RECLAMO, 0),
        'alcance_global': request.user.alcance_global,
        'puede_editar': request.user.tiene_permiso('periodos', 'editar'),
        'puede_metas': request.user.tiene_permiso('metas', 'ver'),
        'otro_abierto': Periodo.objects.filter(estado=Periodo.ABIERTO).exclude(pk=periodo.pk).first()})


@require_POST
@permiso_requerido('periodos', 'editar')
def periodo_estado(request, pk, accion):
    periodo = get_object_or_404(Periodo, pk=pk)
    volver = redirect('periodo_ver', pk=pk) if request.POST.get('volver') == 'detalle' else redirect('periodos')
    if accion == 'abrir':
        if Periodo.objects.filter(estado=Periodo.ABIERTO).exclude(pk=pk).exists():
            messages.error(request, 'Ya hay un período abierto. Ciérrelo antes de abrir otro.')
            return volver
        periodo.estado = Periodo.ABIERTO
    elif accion == 'cerrar':
        periodo.estado = Periodo.CERRADO
    elif accion == 'copiar':
        origen = Periodo.objects.exclude(pk=pk).filter(metas__isnull=False).order_by('-inicio').first()
        if origen is None:
            messages.error(request, 'No hay otro período con metas para copiar.')
        else:
            creadas = 0
            for m in origen.metas.all():
                _, nueva = MetaCargo.objects.get_or_create(periodo=periodo, cargo=m.cargo, item=m.item, defaults={
                    'meta': m.meta, 'ponderador': m.ponderador})
                creadas += nueva
            registrar(request, 'ALTA', 'metas', periodo.pk, f'{creadas} metas copiadas desde {origen}')
            messages.success(request, f'Se copiaron {creadas} metas desde {origen}.')
        return volver
    else:
        raise Http404
    periodo.save(update_fields=['estado'])
    registrar(request, 'CAMBIO_ESTADO', 'periodos', periodo.pk, f'{periodo} {periodo.estado}')
    messages.success(request, f'{periodo} quedó {periodo.get_estado_display().lower()}.')
    return volver


@permiso_requerido('metas', 'ver')
def metas(request):
    periodo = periodo_elegido(request)
    if periodo is None:
        return sin_periodo(request)
    editar = None
    if request.GET.get('editar', '').isdigit():
        editar = MetaCargo.objects.filter(pk=request.GET['editar'], periodo=periodo).first()
    form = None
    # Un período cerrado con actividades queda congelado: sus metas ya no cambian
    editable = periodo.abierto or not periodo.actividades.exists()
    if request.user.tiene_permiso('metas', 'editar') and editable:
        form = MetaForm(request.POST or None, instance=editar, periodo=periodo)
        if request.method == 'POST':
            if form.is_valid():
                meta = form.save(commit=False)
                meta.periodo = periodo
                meta.save()
                registrar(request, 'MODIFICACION' if editar else 'ALTA', 'metas', meta.pk,
                          f'{meta} meta={meta.meta} ponderador={meta.ponderador}')
                messages.success(request, f'Meta «{meta}» guardada.')
                return redirect('metas')
            messages.error(request, 'No se guardó. Revise los campos marcados.')
    elif request.method == 'POST':
        return denegar(request, 'metas.editar')
    cargos = []
    todas = MetaCargo.objects.filter(periodo=periodo).select_related('cargo', 'item')
    for cargo in Cargo.objects.filter(activo=True):
        filas = [m for m in todas if m.cargo_id == cargo.pk]
        suma = sum(float(m.ponderador) for m in filas)
        cargos.append({'cargo': cargo, 'filas': filas, 'suma': suma, 'completo': abs(suma - 100) < 0.01})
    return render(request, 'gestion/metas.html', {'periodo': periodo, 'cargos': cargos, 'form': form,
                                                  'editar': editar, 'periodos': Periodo.objects.all()})


@require_POST
@permiso_requerido('metas', 'editar')
def meta_eliminar(request, pk):
    meta = get_object_or_404(MetaCargo, pk=pk)
    if not meta.periodo.abierto and meta.periodo.actividades.exists():
        messages.error(request, 'El período está cerrado: sus metas quedan congeladas.')
    else:
        registrar(request, 'ELIMINACION', 'metas', pk, str(meta))
        meta.delete()
        messages.success(request, 'Meta eliminada.')
    return redirect('metas')


# ---------------------------------------------------------------------------
# Informes (hoja RESUMEN)
# ---------------------------------------------------------------------------
def _datos_informe(request):
    periodo = periodo_elegido(request)
    resultado = calculos.indicadores(periodo, list(equipo(request)))
    return periodo, resultado


@permiso_requerido('informes', 'ver')
def informes(request):
    periodo = periodo_elegido(request)
    if periodo is None:
        return sin_periodo(request)
    periodo, resultado = _datos_informe(request)
    base = Actividad.objects.filter(periodo=periodo, delegacion=request.delegacion_activa)
    por_item = (base.values('item__codigo', 'item__nombre').annotate(
        total=Count('id'), suman=Count('id', filter=Q(puntua=True, estado=Actividad.REALIZADO)),
        sin=Count('id', filter=Q(puntua=False))).order_by('item__codigo'))
    return render(request, 'gestion/informes.html', {
        'periodo': periodo, 'periodos': Periodo.objects.all(), 'fichas': resultado['fichas'],
        'esperado': resultado['esperado'], 'por_item': por_item,
        'equipo': calculos.resultado_equipo(resultado['fichas'], resultado['esperado'], periodo),
        'organizaciones': request.delegacion_activa.organizaciones.values('tipo__nombre').annotate(
            n=Count('id')).order_by('-n') if request.delegacion_activa else []})


@permiso_requerido('informes', 'ver')
def informes_exportar(request):
    periodo, resultado = _datos_informe(request)
    filas = []
    for f in resultado['fichas']:
        for fila in f['filas'] or [{}]:
            filas.append([f['funcionario'].nombre, f['cargo'].nombre if f['cargo'] else '', fila.get('item', ''),
                          fila.get('ponderador', ''), fila.get('meta', ''), round(fila.get('meta_ajustada', 0), 1),
                          round(fila.get('avance', 0), 1), round(fila.get('cumplimiento', 0), 1),
                          round(fila.get('ponderado', 0), 2), f['dias_ausencia'], f['felicitaciones_validas'],
                          f['reclamos'], round(f['total'], 1), calculos.TEXTO_SEMAFORO.get(f['color'], '')])
    registrar(request, 'EXPORTACION', 'informes', detalle=f'{periodo} · {len(filas)} filas')
    return respuesta_excel('matriz-sgr', f'Matriz SGR {periodo}',
                           ['Funcionario', 'Cargo', 'Ítem', 'Ponderador %', 'Meta', 'Meta ajustada', 'Avance',
                            'Cumplimiento %', 'Ponderado', 'Días ausencia', 'Felicitaciones', 'Reclamos',
                            'Total %', 'Semáforo'],
                           filas, [('Delegación', request.delegacion_activa), ('Período', periodo),
                                   ('Esperado al día', f'{resultado["esperado"]:.1f} %')], request.user)

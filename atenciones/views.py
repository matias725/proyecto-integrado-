"""Ingreso, consulta y exportación de atenciones ciudadanas."""

import uuid
from functools import reduce
from operator import or_

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from catalogos.models import SubAtencion, TipoAtencion
from core.excel import respuesta_excel
from core.models import registrar
from core.validadores import formatear_rut, limpiar_rut, validar_rut
from cuentas.permisos import denegar, permiso_requerido

from .forms import AtencionForm, SeguimientoForm
from .models import Atencion, SeguimientoAtencion, Solicitante

BUSQUEDA = ['solicitante__nombre', 'solicitante__rut', 'tipo__nombre', 'subatencion__nombre', 'descripcion',
            'responsable__nombre']


def _consulta(request):
    """Atenciones de la delegación activa: el contexto decide lo que se ve."""
    if not request.delegacion_activa:
        return Atencion.objects.none()
    return Atencion.objects.filter(delegacion=request.delegacion_activa).select_related(
        'solicitante', 'tipo', 'subatencion', 'responsable', 'delegacion')


def _filtrar(request):
    consulta = _consulta(request)
    texto = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    filtros = []
    if texto:
        for palabra in texto.split()[:5]:
            condicion = reduce(or_, (Q(**{f'{c}__icontains': palabra}) for c in BUSQUEDA))
            numero = palabra.upper().replace('AT-', '').split('-')[-1]
            if numero.isdigit():
                condicion |= Q(pk=int(numero))
            consulta = consulta.filter(condicion)
        filtros.append(('Búsqueda', texto))
    if tipo.isdigit():
        consulta = consulta.filter(tipo_id=int(tipo))
        filtros.append(('Tipo', TipoAtencion.objects.filter(pk=tipo).first() or tipo))
    if estado in dict(Atencion.ESTADOS):
        consulta = consulta.filter(estado=estado)
        filtros.append(('Estado', dict(Atencion.ESTADOS)[estado]))
    else:
        estado = ''
    if request.delegacion_activa:
        filtros.insert(0, ('Delegación', request.delegacion_activa))
    return consulta, texto, tipo, estado, filtros


@permiso_requerido('atenciones', 'ver')
def lista(request):
    consulta, texto, tipo, estado, _ = _filtrar(request)
    pagina = Paginator(consulta, settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
    return render(request, 'atenciones/lista.html', {
        'pagina': pagina, 'texto': texto, 'tipo': tipo, 'estado': estado, 'estados': Atencion.ESTADOS,
        'total_general': _consulta(request).count(),
        'abiertas': _consulta(request).filter(estado=Atencion.ABIERTA).count(),
        'tipos': TipoAtencion.objects.order_by('nombre'),
        'puede_crear': request.user.tiene_permiso('atenciones', 'crear'),
    })


@permiso_requerido('atenciones', 'ver')
def exportar(request):
    consulta, _texto, _tipo, _estado, filtros = _filtrar(request)
    filas = [[a.folio, a.creada, a.delegacion.codigo, a.delegacion.nombre, a.solicitante.rut, a.solicitante.nombre,
              a.tipo.nombre, a.subatencion.nombre, a.descripcion, a.responsable.nombre, a.get_estado_display(),
              a.cerrada, a.cerrada_por.nombre if a.cerrada_por else '']
             for a in consulta.select_related('cerrada_por')]
    registrar(request, 'EXPORTACION', 'atenciones', detalle=f'{len(filas)} registros')
    return respuesta_excel('atenciones', 'Atenciones ciudadanas',
                           ['Folio', 'Fecha de registro', 'Código delegación', 'Delegación', 'RUT', 'Solicitante',
                            'Tipo', 'Sub atención', 'Descripción', 'Responsable', 'Estado', 'Fecha de cierre',
                            'Cerrada por'], filas, filtros, request.user)


@permiso_requerido('atenciones', 'crear')
def nueva(request):
    if not request.delegacion_activa:
        messages.error(request, 'Su cuenta no tiene una delegación autorizada. Contacte al administrador.')
        return redirect('inicio')

    if request.method == 'POST':
        form = AtencionForm(request.POST)
        token = request.POST.get('token_envio', '')
        previa = Atencion.objects.filter(token_envio=token, responsable=request.user).first() if token else None
        if previa:
            # Segundo envío del mismo formulario: no se duplica
            messages.info(request, f'La atención {previa.folio} ya estaba registrada. No se creó un duplicado.')
            return redirect('atenciones_ver', pk=previa.pk)
        if form.is_valid():
            d = form.cleaned_data
            try:
                with transaction.atomic():
                    solicitante, creado = Solicitante.objects.get_or_create(
                        rut=d['rut'], defaults={'nombre': d['nombre'], 'telefono': d['telefono']})
                    if not creado and d['telefono'] and not solicitante.telefono:
                        solicitante.telefono = d['telefono']
                        solicitante.save(update_fields=['telefono'])
                    atencion = Atencion.objects.create(
                        solicitante=solicitante, tipo=d['tipo'], subatencion=d['subatencion'],
                        descripcion=d['descripcion'],
                        # Delegación y responsable salen del contexto autorizado, no del formulario
                        delegacion=request.delegacion_activa, responsable=request.user,
                        token_envio=d['token_envio'])
            except IntegrityError:
                previa = Atencion.objects.filter(token_envio=d['token_envio']).first()
                if previa:
                    return redirect('atenciones_ver', pk=previa.pk)
                messages.error(request, 'No se pudo guardar la atención. Intente nuevamente.')
            else:
                registrar(request, 'ALTA', 'atenciones', atencion.pk,
                          f'{atencion.folio} · {atencion.tipo} / {atencion.subatencion}')
                messages.success(request, f'Atención registrada con el folio {atencion.folio}.')
                destino = reverse('atenciones_ver', args=[atencion.pk]) + '?nueva=1'
                if request.POST.get('siguiente') == 'compromiso':
                    destino += '#enviar-compromiso'
                return redirect(destino)
        else:
            messages.error(request, 'No se guardó. Revise los campos marcados en el formulario.')
    else:
        form = AtencionForm(initial={'token_envio': uuid.uuid4()})

    return render(request, 'atenciones/nueva.html', {'form': form})


def _atencion_autorizada(request, pk):
    """La atención, o la respuesta de error si no existe o es de una delegación no autorizada."""
    atencion = Atencion.objects.select_related('solicitante', 'tipo', 'subatencion', 'responsable', 'delegacion',
                                               'cerrada_por').filter(pk=pk).first()
    if atencion is None:
        raise Http404
    if atencion.delegacion not in request.delegaciones_autorizadas:
        return None, denegar(request, f'atención {pk} de otra delegación')
    return atencion, None


@permiso_requerido('atenciones', 'ver')
def ver(request, pk):
    atencion, error = _atencion_autorizada(request, pk)
    if error:
        return error
    puede_seguir = request.user.tiene_permiso('atenciones', 'editar')
    from gestion.forms import EnviarCompromisoForm
    from gestion.models import Actividad
    compromiso = Actividad.objects.filter(atencion=atencion).select_related('funcionario').first()
    puede_enviar = (compromiso is None and atencion.abierta and request.user.tiene_permiso('actividades', 'crear')
                    and atencion.delegacion == request.delegacion_activa)
    return render(request, 'atenciones/ver.html', {
        'compromiso': compromiso,
        'form_compromiso': EnviarCompromisoForm(delegacion=atencion.delegacion) if puede_enviar else None,
        'atencion': atencion, 'nueva': request.GET.get('nueva') == '1',
        'otra_delegacion': atencion.delegacion != request.delegacion_activa,
        'seguimientos': atencion.seguimientos.select_related('usuario'),
        'form': SeguimientoForm(atencion) if puede_seguir else None,
    })


@require_POST
@permiso_requerido('atenciones', 'editar')
def seguimiento(request, pk):
    """Registra una nota de seguimiento, el cierre o la reapertura de la atención."""
    with transaction.atomic():
        # Se bloquea la fila: dos personas no pueden cerrar y reabrir al mismo tiempo
        bloqueada = Atencion.objects.select_for_update().filter(pk=pk).first()
        if bloqueada is None:
            raise Http404
        atencion, error = _atencion_autorizada(request, pk)
        if error:
            return error
        form = SeguimientoForm(atencion, request.POST)
        if not form.is_valid():
            for errores in form.errors.values():
                for mensaje in errores:
                    messages.error(request, mensaje)
            return redirect(reverse('atenciones_ver', args=[pk]) + '#seguimiento')
        accion, comentario = form.cleaned_data['accion'], form.cleaned_data['comentario']
        SeguimientoAtencion.objects.create(atencion=atencion, tipo=accion, comentario=comentario,
                                           usuario=request.user)
        if accion == SeguimientoAtencion.CIERRE:
            atencion.estado, atencion.cerrada, atencion.cerrada_por = Atencion.CERRADA, timezone.now(), request.user
        elif accion == SeguimientoAtencion.REAPERTURA:
            atencion.estado, atencion.cerrada, atencion.cerrada_por = Atencion.ABIERTA, None, None
        atencion.save(update_fields=['estado', 'cerrada', 'cerrada_por'])
    textos = {SeguimientoAtencion.NOTA: ('MODIFICACION', 'Seguimiento', 'Seguimiento registrado.'),
              SeguimientoAtencion.CIERRE: ('CAMBIO_ESTADO', 'Cerrada', f'Atención {atencion.folio} cerrada.'),
              SeguimientoAtencion.REAPERTURA: ('CAMBIO_ESTADO', 'Reabierta', f'Atención {atencion.folio} reabierta.')}
    evento, etiqueta, mensaje = textos[accion]
    registrar(request, evento, 'atenciones', atencion.pk, f'{atencion.folio} · {etiqueta}: {comentario[:150]}')
    messages.success(request, mensaje)
    return redirect(reverse('atenciones_ver', args=[pk]) + '#seguimiento')


# ---------------------------------------------------------------------------
# Servicios para el formulario (lista dependiente y búsqueda de solicitante)
# ---------------------------------------------------------------------------
@permiso_requerido('atenciones', 'crear')
def api_subatenciones(request):
    tipo = request.GET.get('tipo', '')
    if not tipo.isdigit():
        return JsonResponse({'error': 'Tipo de atención no válido.'}, status=400)
    subs = SubAtencion.objects.filter(tipo_id=int(tipo), activo=True, tipo__activo=True).order_by('nombre')
    return JsonResponse({'subatenciones': [{'id': s.pk, 'codigo': s.codigo, 'nombre': s.nombre} for s in subs]})


@permiso_requerido('atenciones', 'crear')
def api_solicitante(request):
    """Busca un vecino por RUT. Solo informa si existe y sus datos de contacto."""
    rut = limpiar_rut(request.GET.get('rut', ''))
    if len(rut) < 8:
        return JsonResponse({'encontrado': False})
    try:
        validar_rut(rut)
    except ValidationError:
        return JsonResponse({'encontrado': False, 'valido': False})
    formateado = formatear_rut(rut)
    solicitante = Solicitante.objects.filter(rut=formateado).first()
    if not solicitante:
        return JsonResponse({'encontrado': False, 'valido': True, 'rut': formateado})
    return JsonResponse({'encontrado': True, 'valido': True, 'rut': formateado, 'nombre': solicitante.nombre,
                         'telefono': solicitante.telefono, 'atenciones': solicitante.atenciones.count()})

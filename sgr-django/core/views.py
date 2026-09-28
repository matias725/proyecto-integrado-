"""
Vistas del SGR. Cada vista corresponde a un caso de uso del informe.

Patrón usado en todos los formularios (POST, redirección, GET):
  - si el formulario es válido, se guarda, se avisa y se redirige;
  - si no, se vuelve a mostrar la misma página con los errores de cada campo.
"""

import csv
from datetime import datetime

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import calculos, datos, permisos
from .context_processors import periodo_seleccionado
from .forms import (
    ETIQUETAS_COMPROMISO, TIPOS_INFORME, AccesoForm, ActividadForm, AtencionSocialForm,
    CompromisoForm, DelegacionForm, EstadoCompromisoForm, EvidenciaForm, FiltroActividadesForm,
    FiltroAuditoriaForm, InformeForm, MetaFormSet, PeriodoForm, UsuarioForm, ValidacionForm,
)
from .permisos import en_ambito, requiere_permiso, tiene_rol, usuario_actual

A = datos.almacen

CUENTAS_DEMO = [
    ('bcastillo', 'Funcionario'),
    ('arojas', 'Verificador y delegado'),
    ('emunoz', 'Coordinador'),
    ('faguirre', 'Administrador'),
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _nombres_delegaciones(usuario):
    return [d['nombre'] for d in en_ambito(usuario, A['delegaciones'], 'nombre')]


def _numero(valor):
    """Guarda 60.00 como 60 y 12.5 como 12.5."""
    return int(valor) if valor == int(valor) else float(valor)


def _generar_codigo():
    """CU-19: código correlativo, único e inmutable."""
    anio = calculos.hoy().year
    prefijo = f'EV-{anio}-'
    usados = [int(a['codigo'][len(prefijo):]) for a in A['actividades'] if a['codigo'].startswith(prefijo)]
    return f'{prefijo}{max(usados, default=0) + 1:06d}'


def _respuesta_csv(nombre, filas):
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    respuesta.write('﻿')  # para que Excel reconozca los acentos
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerows(filas)
    return respuesta


# ---------------------------------------------------------------------------
# CU-01 · Acceso
# ---------------------------------------------------------------------------
def acceso(request):
    if usuario_actual(request):
        return redirect('tablero')

    form = AccesoForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        request.session.cycle_key()
        request.session['usuario'] = {
            'usuario': form.cleaned_data['usuario'].strip().lower(),
            **form.cuenta,
        }
        request.session.pop('periodo_id', None)
        messages.success(request, f"Sesión iniciada como {form.cuenta['nombre']}.")
        return redirect('tablero')

    return render(request, 'acceso/login.html', {'form': form, 'cuentas': CUENTAS_DEMO})


@require_POST
def salir(request):
    request.session.flush()
    return redirect('acceso')


@require_POST
@requiere_permiso('tablero')
def cambiar_periodo(request):
    periodo = datos.buscar('periodos', id=int(request.POST.get('periodo', 0) or 0))
    if periodo:
        request.session['periodo_id'] = periodo['id']
        if periodo['estado'] == 'CERRADO':
            messages.info(request, f"{periodo['nombre']} está cerrado: sus datos se muestran solo para consulta.")
    siguiente = request.POST.get('siguiente', '')
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        siguiente = reverse('tablero')
    return redirect(siguiente)


# ---------------------------------------------------------------------------
# CU-13 · Tablero
# ---------------------------------------------------------------------------
@requiere_permiso('tablero')
def tablero(request):
    usuario = usuario_actual(request)
    periodo = periodo_seleccionado(request)
    hoy = calculos.hoy()

    # Funcionarios cuya ficha puede ver este usuario
    con_metas = {m['cargo'] for m in A['metas'] if m['periodo'] == periodo['id']}
    candidatos = [u for u in en_ambito(usuario, A['usuarios']) if u['cargo'] in con_metas]
    if not tiene_rol(usuario, 'Delegado', 'Coordinador', 'Administrador'):
        candidatos = [u for u in candidatos if u['nombre'] == usuario['nombre']]
    elegido = request.GET.get('funcionario') or usuario['nombre']
    ficha = next((u for u in candidatos if u['nombre'] == elegido), candidatos[0] if candidatos else None)
    indicadores = calculos.indicadores(ficha['cargo'], periodo) if ficha else None

    actividades = [a for a in en_ambito(usuario, A['actividades'])
                   if periodo['inicio'] <= a['fecha'] <= periodo['termino']]
    compromisos = en_ambito(usuario, A['compromisos'])
    esperado = calculos.meta_esperada_al_dia(periodo)

    delegaciones = []
    for d in en_ambito(usuario, A['delegaciones'], 'nombre'):
        color = calculos.semaforo(d['cumplimiento'], esperado, periodo)
        delegaciones.append({**d, 'color': color, 'texto': calculos.TEXTO_SEMAFORO[color]})

    return render(request, 'tablero/tablero.html', {
        'periodo': periodo,
        'ficha': ficha,
        'candidatos': candidatos,
        'indicadores': indicadores,
        'esperado': esperado,
        'dias_transcurridos': calculos.dias_transcurridos(periodo),
        'total_actividades': len(actividades),
        'validadas': sum(a['estado'] == 'VALIDADA' for a in actividades),
        'pendientes': sum(a['evidencia'] == 'PENDIENTE' for a in en_ambito(usuario, A['actividades'])),
        'vencidos': sum(c['estado'] != 'REALIZADO' and c['fecha'] < hoy for c in compromisos),
        'delegaciones': delegaciones,
    })


# ---------------------------------------------------------------------------
# CU-07 y CU-17 · Actividades
# ---------------------------------------------------------------------------
@requiere_permiso('actividades')
def actividades(request):
    usuario = usuario_actual(request)
    visibles = en_ambito(usuario, A['actividades'])
    filtro = FiltroActividadesForm(request.GET or None, delegaciones=_nombres_delegaciones(usuario))

    filas = visibles
    if filtro.is_valid():
        f = filtro.cleaned_data
        texto = f['texto'].strip().lower()
        filas = [
            a for a in visibles
            if (not f['delegacion'] or a['delegacion'] == f['delegacion'])
            and (not f['item'] or a['item'] == f['item'])
            and (not f['estado'] or a['estado'] == f['estado'])
            and (not texto or texto in a['codigo'].lower() or texto in a['descripcion'].lower())
        ]

    return render(request, 'actividades/lista.html', {
        'filtro': filtro,
        'filas': sorted(filas, key=lambda a: a['fecha'], reverse=True),
        'total': len(visibles),
        'puede_registrar': permisos.puede(usuario, 'actividad_nueva'),
    })


@requiere_permiso('actividad_nueva')
def actividad_nueva(request):
    usuario = usuario_actual(request)
    form = ActividadForm(request.POST if request.method == 'POST' else None, initial={'fecha': calculos.hoy()})

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        actividad = {
            'id': datos.siguiente_id('actividades'),
            'codigo': _generar_codigo(),
            'fecha': d['fecha'],
            'funcionario': usuario['nombre'],
            'delegacion': usuario['delegacion'],
            'descripcion': d['descripcion'],
            'accion': d['accion'],
            'contacto': d['contacto'],
            'telefono': d['telefono'],
            'item': d['item'],
            'tipo': d['tipo'],
            'agenda': d['agenda'],
            'estado': 'REGISTRADA',
            'evidencia': 'SIN_EVIDENCIA',
        }
        A['actividades'].append(actividad)
        datos.registrar_auditoria(usuario['nombre'], 'ALTA', 'actividad', actividad['id'], None, actividad['codigo'])
        return redirect('actividad_registrada', actividad['id'])

    return render(request, 'actividades/nueva.html', {'form': form})


@requiere_permiso('actividades')
def actividad_registrada(request, id):
    actividad = datos.buscar('actividades', id=id)
    if not actividad or actividad not in en_ambito(usuario_actual(request), A['actividades']):
        raise Http404
    return render(request, 'actividades/registrada.html', {'actividad': actividad})


# ---------------------------------------------------------------------------
# CU-09 · Evidencias
# ---------------------------------------------------------------------------
@requiere_permiso('evidencias')
def evidencias(request):
    usuario = usuario_actual(request)
    visibles = en_ambito(usuario, A['actividades'])
    puede_adjuntar = tiene_rol(usuario, 'Funcionario', 'Administrador')

    # Solo se ofrecen las actividades propias (CU-09, excepción E3). Como la
    # lista de opciones se arma en el servidor, un código ajeno se rechaza.
    propias = [
        a for a in visibles
        if a['evidencia'] != 'APROBADA'
        and (a['funcionario'] == usuario['nombre'] or tiene_rol(usuario, 'Administrador'))
    ]
    form = EvidenciaForm(request.POST if request.method == 'POST' else None, request.FILES or None, actividades=propias)

    if request.method == 'POST':
        if not puede_adjuntar:
            datos.registrar_auditoria(usuario['nombre'], 'ACCESO_DENEGADO', 'evidencia', None, '—', 'adjuntar')
            messages.error(request, 'Su rol permite revisar evidencias, pero no adjuntarlas.')
            return redirect('evidencias')
        if form.is_valid():
            actividad = datos.buscar('actividades', codigo=form.cleaned_data['actividad'])
            anterior = actividad['evidencia']
            actividad['evidencia'] = 'PENDIENTE'
            datos.registrar_auditoria(usuario['nombre'], 'ALTA', 'evidencia', actividad['id'], anterior, 'PENDIENTE')
            messages.success(request, f"Evidencia adjuntada a {actividad['codigo']} y enviada a revisión.")
            return redirect('evidencias')

    return render(request, 'evidencias/lista.html', {
        'filas': sorted(visibles, key=lambda a: a['fecha'], reverse=True),
        'form': form,
        'puede_adjuntar': puede_adjuntar and bool(propias),
    })


# ---------------------------------------------------------------------------
# CU-10 y CU-20 · Validación
# ---------------------------------------------------------------------------
def _sumar_avance(actividad):
    """RN-009: solo la aprobación suma, y suma una vez al ítem correspondiente."""
    funcionario = datos.buscar('usuarios', nombre=actividad['funcionario'])
    periodo = next((p for p in A['periodos'] if p['estado'] == 'ABIERTO'
                    and p['inicio'] <= actividad['fecha'] <= p['termino']), None)
    if not funcionario or not periodo:
        return None
    meta = datos.buscar('metas', cargo=funcionario['cargo'], periodo=periodo['id'], item=actividad['item'])
    if meta:
        meta['avance'] += 1
    return meta


@requiere_permiso('validacion')
def validacion(request):
    usuario = usuario_actual(request)
    pendientes = [a for a in en_ambito(usuario, A['actividades']) if a['evidencia'] == 'PENDIENTE']
    form = ValidacionForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and form.is_valid():
        actividad = datos.buscar('actividades', codigo=form.cleaned_data['codigo'])
        resultado = form.cleaned_data['resultado']

        if not actividad or actividad not in pendientes:
            form.add_error(None, 'La evidencia ya no está pendiente o está fuera de su ámbito.')
        elif actividad['funcionario'] == usuario['nombre']:
            # Segregación de funciones: nadie valida su propio trabajo.
            datos.registrar_auditoria(usuario['nombre'], 'ACCESO_DENEGADO', 'evidencia',
                                      actividad['id'], '—', 'autovalidación')
            form.add_error(None, 'No puede validar una evidencia registrada por usted. '
                                 'El intento quedó registrado en la auditoría.')
        else:
            anterior = actividad['evidencia']
            if resultado == 'APROBADA':
                actividad.update(estado='VALIDADA', evidencia='APROBADA')
                meta = _sumar_avance(actividad)
                aviso = 'Evidencia aprobada.'
                if meta:
                    aviso += f" El avance de «{meta['item']}» subió a {meta['avance']}."
            elif resultado == 'RECHAZADA':
                actividad.update(estado='RECHAZADA', evidencia='RECHAZADA')
                aviso = 'Evidencia rechazada. La actividad no suma al avance.'
            else:
                actividad.update(estado='REGISTRADA', evidencia='EN_CORRECCION')
                aviso = 'Se solicitó corrección al funcionario.'
            datos.registrar_auditoria(usuario['nombre'], 'VALIDACION', 'evidencia', actividad['id'],
                                      anterior, actividad['evidencia'])
            messages.success(request, aviso)
            return redirect('validacion')

    en_revision = datos.buscar('actividades', codigo=form.data.get('codigo')) if form.is_bound else None
    return render(request, 'validacion/bandeja.html', {
        'pendientes': pendientes,
        'form': form,
        'en_revision': en_revision,
    })


# ---------------------------------------------------------------------------
# CU-11 y CU-12 · Agenda colectiva
# ---------------------------------------------------------------------------
@requiere_permiso('agenda')
def agenda(request):
    usuario = usuario_actual(request)
    hoy = calculos.hoy()
    responsables = [u['nombre'] for u in en_ambito(usuario, A['usuarios']) if u['estado'] == 'ACTIVO']
    form = CompromisoForm(request.POST if request.method == 'POST' else None, responsables=responsables)

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        responsable = datos.buscar('usuarios', nombre=d['responsable'])
        compromiso = {
            'id': datos.siguiente_id('compromisos'),
            'solicitante': d['solicitante'],
            'territorio': d['territorio'],
            'delegacion': responsable['delegacion'],
            'descripcion': d['descripcion'],
            'responsable': d['responsable'],
            'fecha': d['fecha'],
            'fecha_cierre': None,
            'estado': 'INGRESADO',
            'historial': [{'fecha': datetime.now().replace(microsecond=0), 'usuario': usuario['nombre'],
                           'anterior': None, 'nuevo': 'INGRESADO', 'observacion': 'Registro del compromiso'}],
        }
        A['compromisos'].append(compromiso)
        datos.registrar_auditoria(usuario['nombre'], 'ALTA', 'compromiso', compromiso['id'], None, 'INGRESADO')
        messages.success(request, 'Compromiso registrado en la agenda.')
        return redirect('agenda')

    filas = [
        {**c, 'vencido': c['estado'] != 'REALIZADO' and c['fecha'] < hoy}
        for c in sorted(en_ambito(usuario, A['compromisos']), key=lambda c: c['fecha'])
    ]
    return render(request, 'agenda/lista.html', {
        'filas': filas,
        'form': form,
        'resumen': {
            'pendientes': sum(f['estado'] in ('INGRESADO', 'PENDIENTE') for f in filas),
            'en_proceso': sum(f['estado'] == 'EN_PROCESO' for f in filas),
            'realizados': sum(f['estado'] == 'REALIZADO' for f in filas),
            'vencidos': sum(f['vencido'] for f in filas),
        },
    })


@requiere_permiso('agenda')
def compromiso_estado(request, id):
    usuario = usuario_actual(request)
    compromiso = datos.buscar('compromisos', id=id)
    if not compromiso or compromiso not in en_ambito(usuario, A['compromisos']):
        raise Http404

    form = None
    if compromiso['estado'] != 'REALIZADO':
        form = EstadoCompromisoForm(request.POST if request.method == 'POST' else None, compromiso=compromiso)
        if request.method == 'POST' and form.is_valid():
            anterior, nuevo = compromiso['estado'], form.cleaned_data['estado']
            compromiso['estado'] = nuevo
            if nuevo == 'REALIZADO':
                compromiso['fecha_cierre'] = calculos.hoy()
            compromiso['historial'].append({
                'fecha': datetime.now().replace(microsecond=0),
                'usuario': usuario['nombre'],
                'anterior': anterior,
                'nuevo': nuevo,
                'observacion': form.cleaned_data['observacion'],
            })
            datos.registrar_auditoria(usuario['nombre'], 'CAMBIO_ESTADO', 'compromiso', compromiso['id'],
                                      anterior, nuevo)
            messages.success(request, f'Estado actualizado a «{ETIQUETAS_COMPROMISO[nuevo]}» '
                                      'y registrado en el historial.')
            return redirect('agenda')

    return render(request, 'agenda/estado.html', {
        'compromiso': compromiso,
        'form': form,
        'vencido': compromiso['estado'] != 'REALIZADO' and compromiso['fecha'] < calculos.hoy(),
        'historial': list(reversed(compromiso['historial'])),
    })


# ---------------------------------------------------------------------------
# CU-08 · Atención social
# ---------------------------------------------------------------------------
@requiere_permiso('atencion_social')
def atencion_social(request):
    usuario = usuario_actual(request)
    form = AtencionSocialForm(request.POST if request.method == 'POST' else None, initial={'fecha': calculos.hoy()})

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        caso = form.caso
        limite = permisos.ambito(usuario)
        if caso and limite and caso['delegacion'] != limite:
            form.add_error('rut', f"La persona ya tiene un caso en la delegación {caso['delegacion']}. "
                                  'No se duplica la identificación sin autorización.')
        else:
            if caso is None:
                caso = {
                    'id': datos.siguiente_id('casos_sociales'), 'rut': d['rut'], 'nombre': d['nombre'],
                    'telefono': '—', 'delegacion': usuario['delegacion'], 'apertura': d['fecha'],
                    'estado': 'ABIERTO', 'gestiones': [],
                }
                A['casos_sociales'].append(caso)
            caso['gestiones'].append({
                'numero': len(caso['gestiones']) + 1, 'fecha': d['fecha'],
                'tipo': d['tipo'], 'resultado': d['resultado'],
            })
            datos.registrar_auditoria(usuario['nombre'], 'ALTA', 'gestión social', caso['id'], None,
                                      f"gestión {len(caso['gestiones'])} de 3")
            messages.success(request, f"Atención registrada como gestión {len(caso['gestiones'])} de 3 del caso.")
            return redirect('atencion_social')

    return render(request, 'atencion_social/casos.html', {
        'casos': en_ambito(usuario, A['casos_sociales']),
        'form': form,
    })


# ---------------------------------------------------------------------------
# CU-02 · Delegaciones
# ---------------------------------------------------------------------------
@requiere_permiso('delegaciones')
def delegaciones(request):
    usuario = usuario_actual(request)
    form = DelegacionForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        delegacion = {
            'id': datos.siguiente_id('delegaciones'), 'nombre': d['nombre'], 'ambito': d['ambito'],
            'encargado': 'Por asignar', 'funcionarios': 0, 'estado': 'ACTIVA',
            'correo': d['correo'], 'cumplimiento': 0,
        }
        A['delegaciones'].append(delegacion)
        datos.registrar_auditoria(usuario['nombre'], 'ALTA', 'delegación', delegacion['id'], None, d['nombre'])
        messages.success(request, f"Delegación {d['nombre']} creada.")
        return redirect('delegaciones')

    return render(request, 'configuracion/delegaciones.html', {'filas': A['delegaciones'], 'form': form})


@require_POST
@requiere_permiso('delegaciones')
def delegacion_estado(request, id):
    usuario = usuario_actual(request)
    delegacion = datos.buscar('delegaciones', id=id)
    if not delegacion:
        raise Http404

    if delegacion['estado'] == 'ACTIVA':
        if delegacion['funcionarios'] > 0:
            messages.error(request, f"{delegacion['nombre']} tiene {delegacion['funcionarios']} funcionarios "
                                    'activos. Reasígnelos antes de desactivarla.')
            return redirect('delegaciones')
        delegacion['estado'] = 'INACTIVA'
        messages.success(request, f"Delegación {delegacion['nombre']} desactivada.")
    else:
        delegacion['estado'] = 'ACTIVA'
        messages.success(request, f"Delegación {delegacion['nombre']} reactivada.")

    anterior = 'INACTIVA' if delegacion['estado'] == 'ACTIVA' else 'ACTIVA'
    datos.registrar_auditoria(usuario['nombre'], 'CAMBIO_ESTADO', 'delegación', id, anterior, delegacion['estado'])
    return redirect('delegaciones')


# ---------------------------------------------------------------------------
# CU-03 · Usuarios y roles
# ---------------------------------------------------------------------------
@requiere_permiso('usuarios')
def usuarios(request):
    usuario = usuario_actual(request)
    form = UsuarioForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        nuevo = {
            'id': datos.siguiente_id('usuarios'), 'rut': d['rut'], 'nombre': d['nombre'],
            'correo': d['correo'], 'cargo': d['cargo'], 'delegacion': d['delegacion'],
            'roles': d['roles'], 'estado': 'ACTIVO',
        }
        A['usuarios'].append(nuevo)
        datos.buscar('delegaciones', nombre=d['delegacion'])['funcionarios'] += 1
        datos.registrar_auditoria(usuario['nombre'], 'ALTA', 'usuario', nuevo['id'], None,
                                  f"{d['nombre']} ({', '.join(d['roles'])})")
        messages.success(request, f"Usuario {d['nombre']} creado con {len(d['roles'])} rol(es).")
        return redirect('usuarios')

    return render(request, 'configuracion/usuarios.html', {'filas': A['usuarios'], 'form': form})


# ---------------------------------------------------------------------------
# CU-05 · Períodos
# ---------------------------------------------------------------------------
@requiere_permiso('periodos')
def periodos(request):
    usuario = usuario_actual(request)
    form = PeriodoForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        periodo = {
            'id': datos.siguiente_id('periodos'), 'nombre': d['nombre'], 'inicio': d['inicio'],
            'termino': d['termino'], 'dias': d['dias'], 'estado': 'ABIERTO',
            'umbral_verde': d['umbral_verde'], 'umbral_ambar': d['umbral_ambar'],
            'umbral_colectivo': 80, 'tope': d['tope'],
        }
        traslape = [p['nombre'] for p in A['periodos'] if p['estado'] == 'ABIERTO'
                    and p['inicio'] <= periodo['termino'] and periodo['inicio'] <= p['termino']]
        A['periodos'].append(periodo)
        datos.registrar_auditoria(usuario['nombre'], 'ALTA', 'período', periodo['id'], None, d['nombre'])
        messages.success(request, f"Período {d['nombre']} creado con {d['dias']} días computables.")
        if traslape:
            messages.warning(request, f"Se traslapa con {', '.join(traslape)}, que sigue abierto.")
        return redirect('periodos')

    return render(request, 'configuracion/periodos.html', {
        'filas': sorted(A['periodos'], key=lambda p: p['inicio'], reverse=True),
        'form': form,
        'es_administrador': tiene_rol(usuario_actual(request), 'Administrador'),
    })


@require_POST
@requiere_permiso('periodos')
def periodo_estado(request, id, accion):
    usuario = usuario_actual(request)
    periodo = datos.buscar('periodos', id=id)
    if not periodo or accion not in ('cerrar', 'reabrir'):
        raise Http404

    if accion == 'cerrar' and periodo['estado'] == 'ABIERTO':
        periodo['estado'] = 'CERRADO'
        datos.registrar_auditoria(usuario['nombre'], 'CAMBIO_ESTADO', 'período', id, 'ABIERTO', 'CERRADO')
        messages.success(request, f"{periodo['nombre']} cerrado. Sus resultados quedan congelados.")
    elif accion == 'reabrir' and periodo['estado'] == 'CERRADO':
        # RN-013: la reapertura exige autorización y queda auditada.
        if not tiene_rol(usuario, 'Administrador'):
            datos.registrar_auditoria(usuario['nombre'], 'ACCESO_DENEGADO', 'período', id, '—', 'reabrir')
            messages.error(request, 'La reapertura de un período requiere autorización del administrador.')
        else:
            periodo['estado'] = 'ABIERTO'
            datos.registrar_auditoria(usuario['nombre'], 'CAMBIO_ESTADO', 'período', id, 'CERRADO', 'ABIERTO')
            messages.warning(request, f"{periodo['nombre']} reabierto. El cambio quedó en la auditoría.")
    return redirect('periodos')


# ---------------------------------------------------------------------------
# CU-06 · Metas y ponderaciones
# ---------------------------------------------------------------------------
@requiere_permiso('metas')
def metas(request):
    usuario = usuario_actual(request)
    periodo = periodo_seleccionado(request)
    cargo = request.POST.get('cargo') or request.GET.get('cargo') or 'Gestor Social'
    if cargo not in A['cargos']:
        cargo = 'Gestor Social'

    actuales = [m for m in A['metas'] if m['cargo'] == cargo and m['periodo'] == periodo['id']]
    iniciales = [{'item': m['item'], 'objetivo': m['objetivo'], 'ponderador': m['ponderador']} for m in actuales]
    bloqueado = periodo['estado'] == 'CERRADO'

    if request.method == 'POST':
        if bloqueado:
            messages.error(request, 'El período está cerrado: sus metas no pueden modificarse (RN-013).')
            return redirect(f"{reverse('metas')}?cargo={cargo}")

        formset = MetaFormSet(request.POST, initial=iniciales, prefix='metas')
        if formset.is_valid():
            previas = {m['item']: m for m in actuales}
            siguiente = datos.siguiente_id('metas')
            nuevas = []
            for form in formset.vigentes:
                d = form.cleaned_data
                previa = previas.get(d['item'])
                objetivo, ponderador = _numero(d['objetivo']), _numero(d['ponderador'])
                cambio = not previa or (previa['objetivo'], previa['ponderador']) != (objetivo, ponderador)
                nuevas.append({
                    'id': previa['id'] if previa else siguiente + len(nuevas),
                    'cargo': cargo, 'periodo': periodo['id'], 'item': d['item'],
                    'objetivo': objetivo, 'ponderador': ponderador,
                    'avance': previa['avance'] if previa else 0,
                    # RF-038: cada cambio genera una versión nueva
                    'version': (previa['version'] + 1 if cambio else previa['version']) if previa else 1,
                })
            A['metas'] = [m for m in A['metas'] if not (m['cargo'] == cargo and m['periodo'] == periodo['id'])]
            A['metas'].extend(nuevas)

            resumen = lambda metas: ', '.join(f"{m['item']} {m['ponderador']} %" for m in metas) or '—'  # noqa: E731
            datos.registrar_auditoria(usuario['nombre'], 'CAMBIO_PARAMETRO', f'metas · {cargo}', periodo['id'],
                                      resumen(actuales), resumen(nuevas))
            messages.success(request, f'Configuración de {cargo} guardada como versión nueva.')
            return redirect(f"{reverse('metas')}?cargo={cargo}")
    else:
        formset = MetaFormSet(initial=iniciales, prefix='metas')
        if bloqueado:
            for form in formset:
                for campo in form.fields.values():
                    campo.disabled = True

    return render(request, 'configuracion/metas.html', {
        'formset': formset,
        'cargo': cargo,
        'cargos': A['cargos'],
        'periodo': periodo,
        'bloqueado': bloqueado,
        'suma_inicial': sum(m['ponderador'] for m in actuales),
    })


# ---------------------------------------------------------------------------
# CU-14 · Informes
# ---------------------------------------------------------------------------
def _armar_informe(filtros, usuario, periodo):
    desde, hasta, filtro = filtros['desde'], filtros['hasta'], filtros['delegacion']
    en_rango = [a for a in en_ambito(usuario, A['actividades']) if desde <= a['fecha'] <= hasta]
    esperado = calculos.meta_esperada_al_dia(periodo)
    clases = {'verde': 'ok', 'ambar': 'pendiente', 'rojo': 'error'}

    if filtros['tipo'] == 'delegacion':
        cabecera = ['Delegación', 'Funcionarios', 'Actividades', 'Cumplimiento', 'Semáforo']
        filas = []
        for d in en_ambito(usuario, A['delegaciones'], 'nombre'):
            if filtro and d['nombre'] != filtro:
                continue
            color = calculos.semaforo(d['cumplimiento'], esperado, periodo)
            filas.append({
                'celdas': [d['nombre'], d['funcionarios'],
                           sum(a['delegacion'] == d['nombre'] for a in en_rango),
                           f"{d['cumplimiento']:.1f} %".replace('.', ',')],
                'insignia': (clases[color], calculos.TEXTO_SEMAFORO[color]),
            })
    elif filtros['tipo'] == 'funcionario':
        cabecera = ['Funcionario', 'Cargo', 'Delegación', 'Actividades', 'Validadas']
        filas = []
        for u in en_ambito(usuario, A['usuarios']):
            if filtro and u['delegacion'] != filtro:
                continue
            suyas = [a for a in en_rango if a['funcionario'] == u['nombre']]
            filas.append({'celdas': [u['nombre'], u['cargo'], u['delegacion'], len(suyas),
                                     sum(a['estado'] == 'VALIDADA' for a in suyas)], 'insignia': None})
    else:
        cabecera = ['Solicitante', 'Compromiso', 'Responsable', 'Fecha', 'Estado']
        clases_estado = {'INGRESADO': 'neutro', 'PENDIENTE': 'pendiente', 'EN_PROCESO': 'proceso', 'REALIZADO': 'ok'}
        filas = [
            {'celdas': [c['solicitante'], c['descripcion'], c['responsable'], c['fecha'].strftime('%d-%m-%Y')],
             'insignia': (clases_estado[c['estado']], ETIQUETAS_COMPROMISO[c['estado']])}
            for c in en_ambito(usuario, A['compromisos'])
            if desde <= c['fecha'] <= hasta and (not filtro or c['delegacion'] == filtro)
        ]

    titulo = dict(TIPOS_INFORME)[filtros['tipo']]
    return titulo, cabecera, filas


@requiere_permiso('informes')
def informes(request):
    usuario = usuario_actual(request)
    periodo = periodo_seleccionado(request)
    hoy = calculos.hoy()
    valores = request.GET if 'tipo' in request.GET else {
        'tipo': 'delegacion',
        'desde': periodo['inicio'].isoformat(),
        'hasta': min(hoy, periodo['termino']).isoformat(),
    }
    form = InformeForm(valores, delegaciones=_nombres_delegaciones(usuario))
    titulo, cabecera, filas = '', [], []

    if form.is_valid():
        titulo, cabecera, filas = _armar_informe(form.cleaned_data, usuario, periodo)
        if request.GET.get('exportar') == 'csv':
            f = form.cleaned_data
            datos.registrar_auditoria(usuario['nombre'], 'EXPORTACION', 'informe', None, '—', titulo)
            contenido = [
                [titulo],
                ['Delegación', f['delegacion'] or 'Todas', 'Desde', f['desde'].strftime('%d-%m-%Y'),
                 'Hasta', f['hasta'].strftime('%d-%m-%Y')],
                ['Generado el', datetime.now().strftime('%d-%m-%Y %H:%M'), 'por', usuario['nombre']],
                [],
                cabecera,
                *[fila['celdas'] + ([fila['insignia'][1]] if fila['insignia'] else []) for fila in filas],
            ]
            return _respuesta_csv(f"informe-{f['tipo']}-{hoy:%Y%m%d}.csv", contenido)

    return render(request, 'informes/informes.html', {
        'form': form, 'titulo': titulo, 'cabecera': cabecera, 'filas': filas,
    })


# ---------------------------------------------------------------------------
# CU-16 · Auditoría
# ---------------------------------------------------------------------------
NOMBRES_EVENTO = {
    'ALTA': 'Alta', 'CAMBIO_ESTADO': 'Cambio de estado', 'CAMBIO_PARAMETRO': 'Cambio de parámetro',
    'VALIDACION': 'Validación', 'ACCESO_DENEGADO': 'Acceso denegado', 'EXPORTACION': 'Exportación',
}


@requiere_permiso('auditoria')
def auditoria(request):
    usuario = usuario_actual(request)
    filtro = FiltroAuditoriaForm(request.GET or None)
    eventos = sorted(A['auditoria'], key=lambda e: e['fecha'], reverse=True)
    if filtro.is_valid() and filtro.cleaned_data['evento']:
        eventos = [e for e in eventos if e['evento'] == filtro.cleaned_data['evento']]

    if request.GET.get('exportar') == 'csv':
        datos.registrar_auditoria(usuario['nombre'], 'EXPORTACION', 'auditoría', None, '—', f'{len(eventos)} eventos')
        return _respuesta_csv(f'auditoria-{calculos.hoy():%Y%m%d}.csv', [
            ['Fecha', 'Usuario', 'Evento', 'Entidad', 'Registro', 'Valor anterior', 'Valor nuevo'],
            *[[e['fecha'].strftime('%d-%m-%Y %H:%M'), e['usuario'], NOMBRES_EVENTO.get(e['evento'], e['evento']),
               e['entidad'], e['registro'] or '', e['anterior'], e['nuevo']] for e in eventos],
        ])

    return render(request, 'auditoria/auditoria.html', {
        'filtro': filtro,
        'eventos': [{**e, 'nombre_evento': NOMBRES_EVENTO.get(e['evento'], e['evento'])} for e in eventos],
    })

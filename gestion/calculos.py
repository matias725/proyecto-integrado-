"""
Cálculo de la matriz SGR: avance por ítem, cumplimiento ponderado, semáforo
y resultado de equipo. Equivale a las fórmulas de las hojas por cargo,
SEMAFORO y RESUMEN del Excel trimestral, pero en un solo lugar.

Fórmulas (todas en porcentaje):

    meta ajustada   = meta × (días del período − días de ausencia) / días del período      (regla 9)
    cumplimiento    = avance / meta ajustada × 100, con tope «tope_item» (120 %)             (regla 7)
    ponderado ítem  = cumplimiento × ponderador / 100
    total           = Σ ponderados + felicitaciones × bono − reclamos × descuento, entre 0 y «tope_total»
    esperado al día = días transcurridos / días del período × 100
    semáforo        = verde si total ≥ esperado; naranjo si total ≥ esperado × umbral; rojo en otro caso
    equipo          = promedio del total de los funcionarios con metas en la delegación     (regla 10)
"""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q

from catalogos.models import ItemMedicion

from .models import Actividad, Ausencia, MetaCargo, Observacion, Periodo
from .reglas import MAX_INGRESOS_DIARIOS, hoy

TEXTO_SEMAFORO = {'verde': 'Verde', 'ambar': 'Naranjo', 'rojo': 'Rojo'}


def periodo_vigente():
    return Periodo.objects.filter(estado=Periodo.ABIERTO).first() or Periodo.objects.first()


def dias_transcurridos(periodo, dia=None):
    dia = dia or hoy()
    return max(0, min((dia - periodo.inicio).days + 1, periodo.dias))


def esperado_al_dia(periodo, dia=None):
    return dias_transcurridos(periodo, dia) / periodo.dias * 100 if periodo.dias else 0.0


def semaforo(total, esperado, periodo):
    if total >= esperado:
        return 'verde'
    if total >= esperado * periodo.umbral_naranjo / 100:
        return 'ambar'
    return 'rojo'


def dias_ausencia(periodo, funcionario_ids):
    """Días de ausencia dentro del período, por funcionario (sin contar fuera de él)."""
    resultado = defaultdict(int)
    for a in Ausencia.objects.filter(periodo=periodo, funcionario_id__in=funcionario_ids):
        desde, hasta = max(a.desde, periodo.inicio), min(a.hasta, periodo.termino)
        if hasta >= desde:
            resultado[a.funcionario_id] += (hasta - desde).days + 1
    return resultado


def _avances(periodo, funcionario_ids):
    """Avance por (funcionario, ítem) en una sola consulta agregada (evita N+1)."""
    base = Actividad.objects.filter(periodo=periodo, funcionario_id__in=funcionario_ids)
    conteo = {
        (f['funcionario_id'], f['item_id']): f['n']
        for f in base.filter(puntua=True, estado=Actividad.REALIZADO).exclude(validacion=Actividad.RECHAZADA)
        .values('funcionario_id', 'item_id').annotate(n=Count('id'))
    }
    tubo = {
        f['funcionario_id']: (f['resueltas'], f['total'])
        for f in base.filter(fecha_compromiso__isnull=False).exclude(validacion=Actividad.RECHAZADA)
        .values('funcionario_id').annotate(total=Count('id'),
                                           resueltas=Count('id', filter=Q(estado=Actividad.REALIZADO)))
    }
    return conteo, tubo


def _observaciones(periodo, funcionario_ids):
    datos = defaultdict(lambda: {'felicitaciones': 0, 'reclamos': 0})
    for f in (Observacion.objects.filter(periodo=periodo, funcionario_id__in=funcionario_ids)
              .values('funcionario_id', 'tipo').annotate(n=Count('id'))):
        clave = 'felicitaciones' if f['tipo'] == Observacion.FELICITACION else 'reclamos'
        datos[f['funcionario_id']][clave] = f['n']
    return datos


def indicadores(periodo, funcionarios, dia=None):
    """
    Ficha de cada funcionario (la hoja de su cargo en el Excel).
    `funcionarios` es una lista de usuarios con su cargo cargado.
    """
    funcionarios = [f for f in funcionarios if f.cargo_id]
    ids = [f.pk for f in funcionarios]
    metas = defaultdict(list)
    for m in MetaCargo.objects.filter(periodo=periodo, cargo_id__in={f.cargo_id for f in funcionarios}) \
            .select_related('item').order_by('item__codigo'):
        metas[m.cargo_id].append(m)
    conteo, tubo = _avances(periodo, ids)
    ausencias = dias_ausencia(periodo, ids)
    observaciones = _observaciones(periodo, ids)
    esperado = esperado_al_dia(periodo, dia)

    fichas = []
    for f in funcionarios:
        dias_aus = ausencias.get(f.pk, 0)
        factor = max(periodo.dias - dias_aus, 0) / periodo.dias if periodo.dias else 0
        filas, total = [], 0.0
        for m in metas.get(f.cargo_id, []):
            if m.item.medicion == ItemMedicion.TUBO:
                resueltas, total_tubo = tubo.get(f.pk, (0, 0))
                avance = resueltas / total_tubo * 100 if total_tubo else 0.0
                meta_ajustada = float(m.meta)            # una proporción no se ajusta por ausencias
                detalle_avance = f'{resueltas} de {total_tubo} resueltas'
            else:
                avance = conteo.get((f.pk, m.item_id), 0)
                meta_ajustada = m.meta * factor
                detalle_avance = f'{avance} de {meta_ajustada:.1f}'.replace('.', ',')
            bruto = avance / meta_ajustada * 100 if meta_ajustada > 0 else 0.0
            cumplimiento = min(bruto, periodo.tope_item)
            ponderado = cumplimiento * float(m.ponderador) / 100
            total += ponderado
            filas.append({
                'item': m.item.nombre, 'codigo': m.item.codigo, 'medicion': m.item.medicion,
                'meta': m.meta, 'meta_ajustada': meta_ajustada, 'avance': avance, 'detalle': detalle_avance,
                'ponderador': float(m.ponderador), 'bruto': bruto, 'cumplimiento': cumplimiento,
                'topado': bruto > periodo.tope_item, 'ponderado': ponderado,
                'color': semaforo(cumplimiento, esperado, periodo), 'ancho': min(cumplimiento, 100),
            })
        obs = observaciones[f.pk]
        felicitaciones_validas = min(obs['felicitaciones'], periodo.max_felicitaciones)
        ajuste = felicitaciones_validas * periodo.bono_felicitacion - obs['reclamos'] * periodo.descuento_reclamo
        total_final = max(0.0, min(total + ajuste, periodo.tope_total))
        suma_ponderadores = sum(Decimal(m.ponderador) for m in metas.get(f.cargo_id, []))
        fichas.append({
            'funcionario': f, 'cargo': f.cargo, 'filas': filas, 'gestion': total,
            'felicitaciones': obs['felicitaciones'], 'felicitaciones_validas': felicitaciones_validas,
            'reclamos': obs['reclamos'], 'ajuste': ajuste, 'total': total_final,
            'dias_ausencia': dias_aus, 'dias_efectivos': periodo.dias - dias_aus,
            'color': semaforo(total_final, esperado, periodo) if filas else 'neutro',
            'sin_metas': not filas, 'suma_ponderadores': float(suma_ponderadores),
            'bajo_minimo': bool(filas) and total_final < periodo.cumplimiento_minimo,
        })
    fichas.sort(key=lambda x: (x['sin_metas'], -x['total']))
    return {'fichas': fichas, 'esperado': esperado, 'periodo': periodo,
            'dias_transcurridos': dias_transcurridos(periodo, dia)}


def resultado_equipo(fichas, esperado, periodo):
    """Regla 10: el puntaje se mira como equipo, de forma equilibrada."""
    con_metas = [f for f in fichas if not f['sin_metas']]
    if not con_metas:
        return None
    promedio = sum(f['total'] for f in con_metas) / len(con_metas)
    return {'promedio': promedio, 'color': semaforo(promedio, esperado, periodo), 'integrantes': len(con_metas),
            'bajo_minimo': sum(f['bajo_minimo'] for f in con_metas),
            'dispersion': max(f['total'] for f in con_metas) - min(f['total'] for f in con_metas)}


def alertas_de_registro(periodo, delegacion):
    """
    Regla 6: señales de que se registra «para cumplir» y no lo que se hace.
    Son alertas para el delegado, no bloqueos.
    """
    base = Actividad.objects.filter(periodo=periodo, delegacion=delegacion)
    alertas = []
    for f in (base.values('funcionario__nombre', 'ingresada_el').annotate(n=Count('id'))
              .filter(n__gte=MAX_INGRESOS_DIARIOS).order_by('-ingresada_el')[:10]):
        alertas.append({'tipo': 'Tope diario', 'funcionario': f['funcionario__nombre'],
                        'detalle': f'{f["n"]} ingresos el {f["ingresada_el"]:%d-%m-%Y}: revise si fueron '
                                   'acumulados de días anteriores.'})
    for f in (base.values('funcionario__nombre', 'titulo').annotate(n=Count('id')).filter(n__gte=3)
              .order_by('-n')[:10]):
        alertas.append({'tipo': 'Texto repetido', 'funcionario': f['funcionario__nombre'],
                        'detalle': f'«{f["titulo"][:60]}» registrado {f["n"]} veces.'})
    atrasados = []
    for a in base.only('fecha', 'ingresada_el', 'funcionario__nombre').select_related('funcionario'):
        if (a.ingresada_el - a.fecha).days >= 3:
            atrasados.append(a.funcionario.nombre)
    for nombre in sorted(set(atrasados)):
        n = atrasados.count(nombre)
        if n >= 3:
            alertas.append({'tipo': 'Ingreso tardío', 'funcionario': nombre,
                            'detalle': f'{n} actividades ingresadas 3 o más días después de realizadas.'})
    sin_puntaje = (base.filter(puntua=False).values('funcionario__nombre').annotate(n=Count('id'))
                   .filter(n__gte=5).order_by('-n'))
    for f in sin_puntaje:
        alertas.append({'tipo': 'Sin puntaje', 'funcionario': f['funcionario__nombre'],
                        'detalle': f'{f["n"]} actividades no suman (sin teléfono, gestión previa o del delegado).'})
    return alertas

"""
Carga inicial de la matriz SGR: período vigente con sus metas y datos de
demostración (organizaciones ficticias, actividades, ausencias y felicitaciones).
Es idempotente. Ningún dato corresponde a personas reales.
"""

import random
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.db import transaction

from catalogos.models import Cargo, Delegacion, ItemMedicion

from .models import Actividad, Ausencia, HistorialActividad, MetaCargo, Observacion, Organizacion, Periodo, TipoOrganizacion
from .reglas import MAX_INGRESOS_DIARIOS, aplicar_reglas_de_puntaje, hoy, ultimo_dia_de_ingreso

PDF_DEMO = b'%PDF-1.4\n% Respaldo de demostracion SGR\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def trimestre(dia):
    inicio = date(dia.year, 3 * ((dia.month - 1) // 3) + 1, 1)
    fin_mes = inicio.month + 2
    termino = (date(dia.year + (fin_mes == 12), 1 if fin_mes == 12 else fin_mes + 1, 1) - timedelta(days=1))
    return inicio, termino, f'Trimestre {dia.year}-Q{(dia.month - 1) // 3 + 1}'


@transaction.atomic
def cargar_periodo_vigente(metas):
    """Crea el trimestre en curso (abierto) y el anterior (cerrado), ambos con las metas de la matriz."""
    inicio, termino, nombre = trimestre(hoy())
    anterior_ini, anterior_fin, anterior_nombre = trimestre(inicio - timedelta(days=1))
    if not Periodo.objects.filter(estado=Periodo.ABIERTO).exists():
        Periodo.objects.get_or_create(nombre=nombre, defaults={'inicio': inicio, 'termino': termino,
                                                               'estado': Periodo.ABIERTO})
    Periodo.objects.get_or_create(nombre=anterior_nombre, defaults={
        'inicio': anterior_ini, 'termino': anterior_fin, 'estado': Periodo.CERRADO})
    cargos = {c.codigo: c for c in Cargo.objects.all()}
    items = {i.codigo: i for i in ItemMedicion.objects.all()}
    for periodo in Periodo.objects.filter(nombre__in=[nombre, anterior_nombre]):
        for cargo, item, meta, ponderador in metas:
            MetaCargo.objects.get_or_create(periodo=periodo, cargo=cargos[cargo], item=items[item],
                                            defaults={'meta': meta, 'ponderador': ponderador})


ORGANIZACIONES = [
    ('JUNTA DE VECINOS LAS ROJAS', 'TO01', 'DEL06', 'CAMINO PRINCIPAL S/N, LAS ROJAS', 85, 1201),
    ('JUNTA DE VECINOS EL ROMERO', 'TO01', 'DEL06', 'CALLE LOS AROMOS 12, EL ROMERO', 64, 1202),
    ('CLUB DE ADULTO MAYOR AÑOS DORADOS', 'TO02', 'DEL06', 'SEDE SOCIAL ALGARROBITO', 32, 1203),
    ('CLUB DEPORTIVO EL MILAGRO', 'TO03', 'DEL06', 'MULTICANCHA EL MILAGRO', 48, 1204),
    ('CENTRO DE MADRES LAS VIOLETAS', 'TO04', 'DEL06', 'PASAJE LOS COPIHUES 7, EL ISLÓN', 21, 1205),
    ('COMITÉ DE AGUA POTABLE RURAL EL ROMERO', 'TO08', 'DEL06', 'EL ROMERO S/N', 120, 1206),
    ('AGRUPACIÓN JUVENIL NUEVO HORIZONTE', 'TO06', 'DEL06', 'SEDE JUNTA DE VECINOS LAS ROJAS', 18, 1207),
    ('COMITÉ DE SEGURIDAD VILLA EL VALLE', 'TO07', 'DEL06', 'VILLA EL VALLE, PASAJE 3', 26, 1208),
    ('JUNTA DE VECINOS CENTRO HISTÓRICO', 'TO01', 'DEL01', 'CIENFUEGOS 400', 140, 1209),
    ('CENTRO CULTURAL GABRIELA MISTRAL', 'TO05', 'DEL01', 'BALMACEDA 820', 55, 1210),
    ('JUNTA DE VECINOS LA ANTENA NORTE', 'TO01', 'DEL03', 'AVENIDA 18 DE SEPTIEMBRE 1500', 98, 1211),
    ('CLUB DE ADULTO MAYOR LAS COMPAÑÍAS', 'TO02', 'DEL04', 'ESMERALDA 2400', 44, 1212),
]

# (usuario, ítem, título, interna/externa, organización opcional)
PLANTILLAS = {
    'CAR02': [('IT010', 'Atención social por solicitud de ayuda', 'INT'),
              ('IT011', 'Visita domiciliaria por caso social', 'EXT'),
              ('IT012', 'Entrega de informe social a DIDECO', 'INT'),
              ('IT013', 'Entrega de canasta de alimentos', 'EXT'),
              ('IT010', 'Orientación sobre Registro Social de Hogares', 'INT')],
    'CAR04': [('IT001', 'Atención a dirigente vecinal', 'INT'),
              ('IT006', 'Reunión con junta de vecinos', 'EXT'),
              ('IT008', 'Taller de formulación de proyectos', 'EXT'),
              ('IT001', 'Orientación para renovar directiva', 'INT')],
    'CAR03': [('IT001', 'Atención de público en oficina', 'INT'),
              ('IT002', 'Llamada preventiva de seguimiento', 'INT'),
              ('IT001', 'Atención telefónica por certificado', 'INT'),
              ('IT004', 'Envío de agenda semanal a Comunicaciones', 'INT')],
    'CAR06': [('IT021', 'Reunión semanal del equipo', 'INT'),
              ('IT022', 'Solución de problema de alumbrado de un vecino', 'EXT'),
              ('IT023', 'Informe de avance a Gabinete', 'INT')],
    'CAR07': [('IT016', 'Operativo de limpieza de microbasural', 'EXT'),
              ('IT020', 'Atención de solicitud de desmalezado', 'EXT'),
              ('IT019', 'Evaluación técnica de camino rural', 'EXT'),
              ('IT015', 'Informe semanal de cuadrillas', 'INT')],
    'CAR08': [('IT025', 'Levantamiento de incivilidades en plaza', 'EXT'),
              ('IT029', 'Salida preventiva nocturna', 'EXT'),
              ('IT026', 'Mediación por conflicto entre vecinos', 'EXT'),
              ('IT024', 'Constitución de comité de seguridad', 'EXT')],
}

NOMBRES = ['María Pérez Soto', 'José Soto Fuentes', 'Rosa Araya Castillo', 'Pedro Rojas Vega',
           'Javiera Muñoz Toro', 'Luis Herrera Díaz', 'Carmen Vega Tapia', 'Raúl Díaz Contreras']


def _telefono(azar):
    return f'+56 9 {azar.randint(1000, 9999)} {azar.randint(1000, 9999)}'


@transaction.atomic
def cargar_demo_matriz():
    """Datos de demostración del período abierto, generados respetando las 10 reglas."""
    from cuentas.models import Usuario

    tipos = {t.codigo: t for t in TipoOrganizacion.objects.all()}
    delegaciones = {d.codigo: d for d in Delegacion.objects.all()}
    for nombre, tipo, delegacion, domicilio, socios, registro in ORGANIZACIONES:
        Organizacion.objects.get_or_create(registro_pj=registro, defaults={
            'nombre': nombre, 'tipo': tipos[tipo], 'delegacion': delegaciones[delegacion], 'domicilio': domicilio,
            'socios': socios, 'fecha_constitucion': date(2015, 3, 10), 'verificada': True,
            'observacion': 'Organización ficticia de demostración'})

    periodo = Periodo.objects.filter(estado=Periodo.ABIERTO).first()
    if periodo is None or Actividad.objects.filter(periodo=periodo).exists():
        return
    azar = random.Random(2026)
    dia_fin = min(hoy() - timedelta(days=1), periodo.termino)
    funcionarios = Usuario.objects.filter(is_active=True, cargo__codigo__in=PLANTILLAS).select_related('cargo')
    delegado = {d.codigo: Usuario.objects.filter(delegaciones=d, cargo__es_delegado=True, is_active=True).first()
                for d in delegaciones.values()}
    items = {i.codigo: i for i in ItemMedicion.objects.all()}
    actividades = []
    for funcionario in funcionarios:
        delegacion = funcionario.delegaciones.order_by('codigo').first()
        orgs = list(Organizacion.objects.filter(delegacion=delegacion))
        intensidad = 3 if delegacion.codigo == 'DEL06' else 1
        dia = periodo.inicio
        while dia <= dia_fin:
            if dia.weekday() < 5:
                for _ in range(min(azar.randint(0, 2 * intensidad), MAX_INGRESOS_DIARIOS)):
                    item, titulo, origen = azar.choice(PLANTILLAS[funcionario.cargo.codigo])
                    sorteo = azar.random()
                    pendiente = sorteo < 0.15
                    a = Actividad(
                        periodo=periodo, delegacion=delegacion, funcionario=funcionario,
                        item=items[item], origen=origen, fecha=dia,
                        titulo=titulo, descripcion=f'{titulo}. Se registra la gestión realizada y su resultado.',
                        solicitante_nombre=azar.choice(NOMBRES),
                        # Regla 2: algunas sin teléfono para mostrar que no suman
                        solicitante_telefono='' if 0.15 <= sorteo < 0.2 else _telefono(azar),
                        naturaleza=Actividad.GESTION if 0.2 <= sorteo < 0.25 else Actividad.ACCION,
                        solicitante_es_delegado=0.25 <= sorteo < 0.28,
                        organizacion=azar.choice(orgs) if orgs and origen == 'EXT' else None,
                        territorio=delegacion.nombre,
                        estado=(azar.choice([Actividad.INGRESADO, Actividad.PENDIENTE, Actividad.EN_PROCESO])
                                if pendiente else Actividad.REALIZADO),
                        fecha_compromiso=dia + timedelta(days=azar.randint(5, 20)) if pendiente or sorteo > 0.9
                        else None,
                        fecha_cierre=dia if not pendiente else None,
                        # Regla 4: el ingreso ocurre a más tardar el lunes siguiente
                        ingresada_el=min(dia + timedelta(days=azar.choice([0, 0, 0, 1])), ultimo_dia_de_ingreso(dia),
                                         hoy()),
                    )
                    if a.solicitante_es_delegado:
                        a.solicitante_nombre = 'Delegación'
                    if dia < hoy() - timedelta(days=10) and azar.random() < 0.85:
                        a.validacion = Actividad.RECHAZADA if azar.random() < 0.05 else Actividad.VALIDADA
                        a.validada_por = delegado.get(delegacion.codigo)
                        if a.validacion == Actividad.RECHAZADA:
                            a.motivo_rechazo = 'No corresponde al ítem informado.'
                    aplicar_reglas_de_puntaje(a)
                    actividades.append(a)
            dia += timedelta(days=1)
    # Regla 3: nunca más de 7 ingresos el mismo día por funcionario
    cupo = {}
    validas = []
    for a in actividades:
        clave = (a.funcionario_id, a.ingresada_el)
        if cupo.get(clave, 0) < MAX_INGRESOS_DIARIOS:
            cupo[clave] = cupo.get(clave, 0) + 1
            validas.append(a)
    Actividad.objects.bulk_create(validas, batch_size=500)
    HistorialActividad.objects.bulk_create([
        HistorialActividad(actividad=a, usuario=a.funcionario, estado_nuevo=a.estado, observacion='Ingreso')
        for a in Actividad.objects.filter(periodo=periodo)], batch_size=500)

    rural = delegaciones['DEL06']
    jefa = delegado.get('DEL06')
    if jefa:
        bruno = Usuario.objects.filter(nombre_usuario='bcastillo').first()
        camila = Usuario.objects.filter(nombre_usuario='cvega').first()
        inicio = max(periodo.inicio, min(hoy(), periodo.termino) - timedelta(days=20))
        if camila:
            Ausencia.objects.get_or_create(periodo=periodo, funcionario=camila, tipo=Ausencia.VACACIONES,
                                           desde=inicio, defaults={'hasta': inicio + timedelta(days=4),
                                                                   'registrada_por': jefa,
                                                                   'observacion': 'Feriado legal'})
        if bruno:
            obs = Observacion(periodo=periodo, tipo=Observacion.FELICITACION, funcionario=bruno,
                              fecha=max(periodo.inicio, min(hoy(), periodo.termino) - timedelta(days=3)), medio=Observacion.CORREO,
                              remitente='Junta de Vecinos Las Rojas',
                              descripcion='Felicita la atención en la entrega de ayuda social.',
                              respaldo_nombre='felicitacion.pdf', registrada_por=jefa)
            obs.respaldo.save('felicitacion.pdf', ContentFile(PDF_DEMO), save=False)
            obs.save()
    return rural

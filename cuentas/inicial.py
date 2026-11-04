"""
Carga inicial del SGR: permisos, roles, catálogos y cuentas de demostración.

Es idempotente: puede ejecutarse varias veces sin duplicar registros.
Uso:  python manage.py sgr_inicializar --demo
Todos los datos son ficticios (Guía SGR, condiciones del caso).
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from catalogos.models import Cargo, Delegacion, ItemMedicion, SubAtencion, TipoAtencion
from core.validadores import digito_verificador

from .models import Permiso, Rol, Usuario
from .modulos import todas_las_combinaciones

CLAVE_DEMO = 'Serena#2026'


def _todos():
    return {f'{m}.{a}' for m, a in todas_las_combinaciones()}


def _ver(*modulos):
    return {f'{m}.ver' for m in modulos}


def _crud(*modulos):
    return {f'{m}.{a}' for m in modulos for a in ('ver', 'crear', 'editar', 'eliminar')}


ROLES = [
    {
        'codigo': 'ROL01', 'nombre': 'Superadministrador', 'alcance': Rol.GLOBAL, 'protegido': True,
        'descripcion': 'Administra todo el sistema: catálogos, usuarios, roles y permisos en todas las delegaciones.',
        'permisos': _todos(),
    },
    {
        'codigo': 'ROL02', 'nombre': 'Coordinador', 'alcance': Rol.GLOBAL,
        'descripcion': 'Coordinación de Delegaciones: configura períodos, metas y catálogos, y supervisa la matriz '
                       'SGR de todas las delegaciones.',
        'permisos': _crud('items', 'tipos_atencion', 'sub_atenciones', 'cargos', 'organizaciones')
        | _ver('delegaciones', 'roles', 'usuarios', 'atenciones', 'auditoria', 'tablero', 'actividades',
               'agenda', 'evidencias', 'informes', 'ausencias', 'observaciones', 'atencion_social')
        | {'validacion.ver', 'periodos.ver', 'periodos.crear', 'periodos.editar', 'metas.ver', 'metas.editar'},
    },
    {
        'codigo': 'ROL03', 'nombre': 'Delegado municipal', 'alcance': Rol.DELEGACION,
        'descripcion': 'Dirige una o más delegaciones: valida actividades, registra ausencias, felicitaciones y '
                       'reclamos de su equipo y administra a sus funcionarios.',
        'permisos': {'atenciones.ver', 'atenciones.crear', 'usuarios.ver', 'usuarios.crear', 'usuarios.editar',
                     'actividades.ver', 'actividades.crear', 'evidencias.ver', 'evidencias.crear',
                     'validacion.ver', 'validacion.editar', 'observaciones.ver', 'observaciones.crear',
                     'organizaciones.ver', 'organizaciones.crear', 'organizaciones.editar'}
        | _crud('ausencias')
        | _ver('delegaciones', 'items', 'tipos_atencion', 'sub_atenciones', 'cargos', 'tablero', 'agenda',
               'informes', 'atencion_social', 'metas', 'periodos'),
    },
    {
        'codigo': 'ROL04', 'nombre': 'Funcionario', 'alcance': Rol.DELEGACION,
        'descripcion': 'Atiende a vecinos y vecinas de su delegación y registra su gestión diaria en la matriz SGR.',
        'permisos': {'atenciones.ver', 'atenciones.crear', 'actividades.ver', 'actividades.crear',
                     'evidencias.ver', 'evidencias.crear'}
        | _ver('tablero', 'agenda', 'ausencias', 'observaciones', 'organizaciones', 'atencion_social', 'metas'),
    },
    {
        'codigo': 'ROL05', 'nombre': 'Consultor', 'alcance': Rol.GLOBAL,
        'descripcion': 'Acceso de solo lectura a catálogos, atenciones, indicadores e informes.',
        'permisos': _ver('delegaciones', 'items', 'tipos_atencion', 'sub_atenciones', 'atenciones', 'tablero',
                         'informes', 'organizaciones', 'cargos'),
    },
]

DELEGACIONES = [
    ('DEL01', 'Centro', 'Cienfuegos 226'),
    ('DEL02', 'Avenida del Mar', 'Avenida del Mar 2500'),
    ('DEL03', 'La Antena', 'Avenida 18 de Septiembre s/n'),
    ('DEL04', 'Las Compañías', 'Esmeralda 2422'),
    ('DEL05', 'La Pampa', 'Larraín Alcalde 3505'),
    ('DEL06', 'Rural', "O'Higgins 154"),
]

# Ítems de la matriz SGR trimestral (hojas por cargo). (código, nombre, descripción, medición)
ITEMS = [
    ('IT001', 'Atención de usuario teléfono y presencial', 'Atenciones a vecinos en oficina o por teléfono', 'CONTEO'),
    ('IT002', 'Llamadas preventivas a usuarios', 'Llamado posterior a una atención registrada', 'CONTEO'),
    ('IT003', 'Informe de inventarios', 'Inventario trimestral de la delegación', 'CONTEO'),
    ('IT004', 'Informe a comunicaciones', 'Envío de la agenda de la delegación a Comunicaciones', 'CONTEO'),
    ('IT005', 'Emergencia', 'Apoyo a vecinos durante emergencias declaradas', 'CONTEO'),
    ('IT006', 'Visitas y reuniones con organizaciones', 'Reuniones con juntas de vecinos y organizaciones', 'CONTEO'),
    ('IT007', 'Conformación de organizaciones', 'Constitución o renovación de directivas definitivas', 'CONTEO'),
    ('IT008', 'Gestión de talleres y actividades', 'Talleres realizados con organizaciones', 'CONTEO'),
    ('IT009', 'Soluciones de ingresos al TUBO', 'Porcentaje de solicitudes del TUBO de trabajo resueltas', 'TUBO'),
    ('IT010', 'Atención social a usuario presencial', 'Atención social de casos en la delegación', 'CONTEO'),
    ('IT011', 'Visita a terreno', 'Visitas domiciliarias o en terreno', 'CONTEO'),
    ('IT012', 'Entrega de informe social', 'Informes sociales entregados', 'CONTEO'),
    ('IT013', 'Entrega de beneficio', 'Beneficios sociales entregados', 'CONTEO'),
    ('IT014', 'Informes de personal', 'Informes de personal de las cuadrillas (empleabilidad)', 'CONTEO'),
    ('IT015', 'Informe semanal de trabajo', 'Informe semanal del programa de cuadrillas', 'CONTEO'),
    ('IT016', 'Operativo de la delegación', 'Operativos de limpieza o mejoramiento de la delegación', 'CONTEO'),
    ('IT017', 'Operativo DISERCO', 'Operativos coordinados con Servicios a la Comunidad', 'CONTEO'),
    ('IT018', 'Talleres de educación ambiental', 'Talleres de reciclaje, compostaje, aseo y ornato', 'CONTEO'),
    ('IT019', 'Terreno técnico', 'Análisis técnico en terreno para obras de mejoramiento', 'CONTEO'),
    ('IT020', 'Atención de requerimiento de usuario', 'Requerimientos de servicios comunitarios atendidos', 'CONTEO'),
    ('IT021', 'Reunión semanal con el equipo', 'Reunión semanal de coordinación de la delegación', 'CONTEO'),
    ('IT022', 'Solución de problemas a usuarios', 'Problemas de usuarios particulares resueltos', 'CONTEO'),
    ('IT023', 'Informe a la jefatura', 'Informes solicitados por la jefatura o Gabinete', 'CONTEO'),
    ('IT024', 'Formación de comités de seguridad', 'Comités de seguridad conformados', 'CONTEO'),
    ('IT025', 'Levantamiento de incivilidades', 'Incivilidades levantadas en terreno', 'CONTEO'),
    ('IT026', 'Gestión de mediación', 'Mediaciones vecinales realizadas', 'CONTEO'),
    ('IT027', 'Recuperación de espacios públicos', 'Espacios públicos recuperados', 'CONTEO'),
    ('IT028', 'Infracciones varias', 'Infracciones cursadas o derivadas', 'CONTEO'),
    ('IT029', 'Salidas a terreno de seguridad', 'Patrullajes y salidas preventivas', 'CONTEO'),
]

# Cargos del descriptor de funciones 2026. (código, nombre, función principal, es delegado)
CARGOS = [
    ('CAR01', 'Delegado', 'Representante de la alcaldía en el territorio; puente entre el municipio y los sectores.',
     True),
    ('CAR02', 'Gestor social', 'Atención de casos y acciones comunitarias para personas en situación de '
     'vulnerabilidad.', False),
    ('CAR03', 'Apoyo administrativo', 'Agenda, logística, atención de público, registro de atenciones e inventario.',
     False),
    ('CAR04', 'Territorial de organizaciones comunitarias', 'Registro, formación y asesoría de juntas de vecinos y '
     'organizaciones funcionales (Leyes 19.418 y 20.500).', False),
    ('CAR05', 'Gestor de compras y proyectos', 'Tramita los requerimientos de adquisiciones y el plan anual de '
     'compras.', False),
    ('CAR06', 'Gestión y planificación', 'Alinea objetivos con la operación, informa la matriz SGR y gestiona la '
     'reunión semanal.', False),
    ('CAR07', 'Coordinador de servicios comunitarios', 'Operativos de aseo, ornato y medio ambiente; cuadrillas de '
     'empleabilidad y emergencia.', False),
    ('CAR08', 'Gestor de seguridad', 'Comités de seguridad, incivilidades, mediación y recuperación de espacios.',
     False),
]

# Metas por cargo de la matriz trimestral. (cargo, ítem, meta, ponderador %)
METAS = [
    ('CAR03', 'IT001', 240, 20), ('CAR03', 'IT002', 90, 30), ('CAR03', 'IT003', 1, 25), ('CAR03', 'IT004', 12, 20),
    ('CAR03', 'IT005', 2, 5),
    ('CAR04', 'IT001', 60, 15), ('CAR04', 'IT006', 24, 15), ('CAR04', 'IT007', 1, 25), ('CAR04', 'IT008', 6, 15),
    ('CAR04', 'IT005', 2, 5), ('CAR04', 'IT009', 80, 25),
    ('CAR02', 'IT010', 90, 20), ('CAR02', 'IT011', 12, 20), ('CAR02', 'IT012', 40, 25), ('CAR02', 'IT013', 8, 20),
    ('CAR02', 'IT005', 2, 5), ('CAR02', 'IT009', 80, 10),
    ('CAR07', 'IT014', 3, 10), ('CAR07', 'IT015', 12, 10), ('CAR07', 'IT016', 24, 15), ('CAR07', 'IT017', 12, 10),
    ('CAR07', 'IT018', 12, 10), ('CAR07', 'IT019', 24, 10), ('CAR07', 'IT020', 24, 15), ('CAR07', 'IT005', 2, 5),
    ('CAR07', 'IT009', 80, 15),
    # La hoja PLAN y CON suma 85 %: se completa con «Informe a la jefatura» (descriptor, función 1)
    ('CAR06', 'IT021', 12, 15), ('CAR06', 'IT022', 8, 30), ('CAR06', 'IT023', 12, 15), ('CAR06', 'IT005', 2, 5),
    ('CAR06', 'IT009', 80, 35),
    ('CAR08', 'IT024', 36, 20), ('CAR08', 'IT025', 40, 20), ('CAR08', 'IT026', 50, 10), ('CAR08', 'IT027', 50, 10),
    ('CAR08', 'IT028', 45, 15), ('CAR08', 'IT029', 45, 10), ('CAR08', 'IT009', 80, 15),
]

# Subfamilias de organizaciones (correo de Gestión Delegaciones). (código, nombre, familia)
TIPOS_ORGANIZACION = [
    ('TO01', 'Junta de vecinos', 'TERRITORIAL'),
    ('TO02', 'Club de adulto mayor', 'FUNCIONAL'),
    ('TO03', 'Organización deportiva', 'FUNCIONAL'),
    ('TO04', 'Centro de madres', 'FUNCIONAL'),
    ('TO05', 'Centro u organización cultural', 'FUNCIONAL'),
    ('TO06', 'Agrupación juvenil', 'FUNCIONAL'),
    ('TO07', 'Comité de vecinos, allegados o seguridad', 'FUNCIONAL'),
    ('TO08', 'Comité de vivienda o agua potable', 'FUNCIONAL'),
    ('TO09', 'Centro de padres y apoderados', 'FUNCIONAL'),
    ('TO10', 'Unión comunal', 'FUNCIONAL'),
    ('TO11', 'Otra organización funcional', 'FUNCIONAL'),
]

TIPOS = [
    ('TA001', 'Social', 'Apoyo social y orientación en beneficios', True),
    ('TA002', 'Salud', 'Orientación y derivación en salud', True),
    ('TA003', 'Educación', 'Apoyo escolar y becas', True),
    ('TA004', 'Vivienda', 'Subsidios y regularización de viviendas', True),
    ('TA005', 'Seguridad', 'Prevención y seguridad territorial', True),
    ('TA006', 'Medio ambiente', 'Aseo, áreas verdes y tenencia responsable', True),
    ('TA007', 'Infraestructura', 'Alumbrado, calles y espacios públicos', True),
    ('TA008', 'Organizaciones comunitarias', 'Apoyo a juntas de vecinos y organizaciones', True),
    ('TA009', 'Deporte y recreación', 'Talleres y recintos deportivos', False),
]

SUBATENCIONES = [
    ('SA001', 'Ayuda social', 'TA001', True),
    ('SA002', 'Registro Social de Hogares', 'TA001', True),
    ('SA003', 'Orientación previsional', 'TA001', True),
    ('SA004', 'Orientación en salud', 'TA002', True),
    ('SA005', 'Derivación a CESFAM', 'TA002', True),
    ('SA006', 'Beca municipal', 'TA003', True),
    ('SA007', 'Matrícula escolar', 'TA003', True),
    ('SA008', 'Subsidio habitacional', 'TA004', True),
    ('SA009', 'Regularización de vivienda', 'TA004', True),
    ('SA010', 'Patrullaje preventivo', 'TA005', True),
    ('SA011', 'Denuncia de incivilidades', 'TA005', True),
    ('SA012', 'Retiro de microbasural', 'TA006', True),
    ('SA013', 'Tenencia responsable de mascotas', 'TA006', True),
    ('SA014', 'Poda de árboles', 'TA006', True),
    ('SA015', 'Reparación de luminarias', 'TA007', True),
    ('SA016', 'Bacheo de calles', 'TA007', True),
    ('SA017', 'Mantención de áreas verdes', 'TA007', True),
    ('SA018', 'Personalidad jurídica', 'TA008', True),
    ('SA019', 'Fondos concursables', 'TA008', True),
    ('SA020', 'Uso de sedes comunitarias', 'TA008', True),
    ('SA021', 'Entrega de agua en camión aljibe', 'TA001', False),
]

# (usuario, nombre, rol, delegaciones, activo, cargo)
USUARIOS = [
    ('admin', 'Felipe Aguirre Núñez', 'ROL01', ['DEL04'], True, None),
    ('emunoz', 'Elena Muñoz Tapia', 'ROL02', ['DEL01'], True, None),
    ('arojas', 'Ana Rojas Miranda', 'ROL03', ['DEL06', 'DEL03'], True, 'CAR01'),
    ('bcastillo', 'Bruno Castillo Peña', 'ROL04', ['DEL06'], True, 'CAR02'),
    ('cvega', 'Camila Vega Soto', 'ROL04', ['DEL06'], True, 'CAR04'),
    ('dfuentes', 'Diego Fuentes Lara', 'ROL04', ['DEL01'], False, 'CAR03'),
    ('mtapia', 'Marcela Tapia Cortés', 'ROL03', ['DEL01'], True, 'CAR01'),
    ('jalvarez', 'Jorge Álvarez Rivera', 'ROL04', ['DEL01'], True, 'CAR07'),
    ('pcontreras', 'Paula Contreras Díaz', 'ROL04', ['DEL02'], True, 'CAR02'),
    ('rsilva', 'Rodrigo Silva Morales', 'ROL04', ['DEL03'], True, 'CAR04'),
    ('lgonzalez', 'Luisa González Pizarro', 'ROL04', ['DEL04'], True, 'CAR03'),
    ('fortiz', 'Francisco Ortiz Rojas', 'ROL04', ['DEL05'], True, 'CAR06'),
    ('vcampos', 'Valentina Campos Araya', 'ROL03', ['DEL05', 'DEL02'], True, 'CAR01'),
    ('lectura', 'Cuenta de Consulta', 'ROL05', ['DEL01'], True, None),
    # Equipo completo de la Delegación Rural para la demostración de la matriz
    ('nperez', 'Natalia Pérez Olivares', 'ROL04', ['DEL06'], True, 'CAR03'),
    ('tmorales', 'Tomás Morales Lagos', 'ROL04', ['DEL06'], True, 'CAR06'),
    ('ilagos', 'Ignacio Lagos Ramírez', 'ROL04', ['DEL06'], True, 'CAR07'),
    ('gsoto', 'Gabriela Soto Vergara', 'ROL04', ['DEL06'], True, 'CAR08'),
]


def _rut(cuerpo):
    return f'{cuerpo:,}'.replace(',', '.') + '-' + digito_verificador(str(cuerpo))


SOLICITANTES = [
    (12345678, 'María Pérez Soto', '+56 9 1111 1111'),
    (15432876, 'José Soto Fuentes', '+56 9 2222 2222'),
    (9876543, 'Rosa Araya Castillo', '+56 9 3333 3333'),
    (17654321, 'Pedro Rojas Vega', '+56 9 4444 4444'),
    (20111222, 'Javiera Muñoz Toro', ''),
    (8765432, 'Luis Herrera Díaz', '+56 9 5555 5555'),
]


@transaction.atomic
def cargar_base():
    """Permisos, roles y catálogos. Seguro para producción."""
    permisos = {}
    for modulo, accion in todas_las_combinaciones():
        permiso, _ = Permiso.objects.get_or_create(modulo=modulo, accion=accion)
        permisos[f'{modulo}.{accion}'] = permiso

    for datos in ROLES:
        rol, _ = Rol.objects.update_or_create(codigo=datos['codigo'], defaults={
            'nombre': datos['nombre'], 'descripcion': datos['descripcion'], 'alcance': datos['alcance'],
            'protegido': datos.get('protegido', False), 'activo': True,
        })
        rol.permisos.set([permisos[c] for c in sorted(datos['permisos']) if c in permisos])

    for codigo, nombre, direccion in DELEGACIONES:
        Delegacion.objects.update_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'direccion': direccion, 'comuna': 'La Serena'})
    for codigo, nombre, descripcion, medicion in ITEMS:
        ItemMedicion.objects.update_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'descripcion': descripcion, 'medicion': medicion})
    for codigo, nombre, descripcion, es_delegado in CARGOS:
        Cargo.objects.update_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'descripcion': descripcion, 'es_delegado': es_delegado})
    from gestion.models import TipoOrganizacion
    for codigo, nombre, familia in TIPOS_ORGANIZACION:
        TipoOrganizacion.objects.update_or_create(codigo=codigo, defaults={'nombre': nombre, 'familia': familia})
    from gestion.inicial import cargar_periodo_vigente
    cargar_periodo_vigente(METAS)
    for codigo, nombre, descripcion, activo in TIPOS:
        TipoAtencion.objects.update_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'descripcion': descripcion, 'activo': activo})
    tipos = {t.codigo: t for t in TipoAtencion.objects.all()}
    for codigo, nombre, tipo, activo in SUBATENCIONES:
        SubAtencion.objects.update_or_create(codigo=codigo, defaults={
            'nombre': nombre, 'tipo': tipos[tipo], 'activo': activo})


@transaction.atomic
def cargar_demo(clave=CLAVE_DEMO):
    """Cuentas y atenciones ficticias para demostración y pruebas."""
    from atenciones.models import Atencion, Solicitante

    roles = {r.codigo: r for r in Rol.objects.all()}
    delegaciones = {d.codigo: d for d in Delegacion.objects.all()}
    cargos = {c.codigo: c for c in Cargo.objects.all()}
    for usuario, nombre, rol, codigos, activo, cargo in USUARIOS:
        cuenta = Usuario.objects.filter(nombre_usuario=usuario).first()
        if cuenta is None:
            cuenta = Usuario.objects.create_user(usuario, f'{usuario}@example.test', clave,
                                                 nombre=nombre, rol=roles[rol], is_active=activo)
        cuenta.cargo = cargos.get(cargo)
        cuenta.save(update_fields=['cargo'])
        cuenta.delegaciones.set([delegaciones[c] for c in codigos])

    for cuerpo, nombre, telefono in SOLICITANTES:
        Solicitante.objects.get_or_create(rut=_rut(cuerpo), defaults={'nombre': nombre, 'telefono': telefono})

    if not Atencion.objects.exists():
        solicitantes = list(Solicitante.objects.order_by('id'))
        subs = list(SubAtencion.objects.filter(activo=True).select_related('tipo').order_by('codigo'))
        funcionarios = [
            ('bcastillo', 'DEL06'), ('cvega', 'DEL06'), ('arojas', 'DEL03'), ('jalvarez', 'DEL01'),
            ('pcontreras', 'DEL02'), ('lgonzalez', 'DEL04'), ('fortiz', 'DEL05'), ('rsilva', 'DEL03'),
        ]
        descripciones = [
            'Vecina solicita orientación para postular al beneficio y se agenda seguimiento.',
            'Se recibe la solicitud y se deriva a la unidad municipal correspondiente.',
            'Vecino informa el problema en su pasaje; se registra para coordinar la visita técnica.',
            'Se entrega información sobre requisitos y plazos del trámite.',
        ]
        for n in range(30):
            usuario, delegacion = funcionarios[n % len(funcionarios)]
            sub = subs[(n * 7) % len(subs)]
            atencion = Atencion.objects.create(
                solicitante=solicitantes[n % len(solicitantes)], tipo=sub.tipo, subatencion=sub,
                descripcion=descripciones[n % len(descripciones)], delegacion=delegaciones[delegacion],
                responsable=Usuario.objects.get(nombre_usuario=usuario))
            # Fechas repartidas en las últimas semanas para que el listado sea realista
            hace = timedelta(days=(30 - n) * 2, hours=(n * 5) % 9, minutes=(n * 17) % 60)
            Atencion.objects.filter(pk=atencion.pk).update(creada=timezone.now().replace(hour=9, minute=0) - hace)

    from gestion.inicial import cargar_demo_matriz
    cargar_demo_matriz()

"""
Carga inicial del SGR: permisos, roles, catálogos y cuentas de demostración.

Es idempotente: puede ejecutarse varias veces sin duplicar registros.
Uso:  python manage.py sgr_inicializar --demo
Todos los datos son ficticios (Guía SGR, condiciones del caso).
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from catalogos.models import Delegacion, ItemMedicion, SubAtencion, TipoAtencion
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
        'descripcion': 'Supervisa la gestión de todas las delegaciones y mantiene los catálogos de atención y medición.',
        'permisos': _crud('items', 'tipos_atencion', 'sub_atenciones')
        | _ver('delegaciones', 'roles', 'usuarios', 'atenciones', 'auditoria', 'tablero', 'actividades',
               'agenda', 'informes')
        | {'validacion.ver', 'validacion.editar', 'periodos.ver', 'periodos.crear', 'periodos.editar',
           'metas.ver', 'metas.editar'},
    },
    {
        'codigo': 'ROL03', 'nombre': 'Delegado municipal', 'alcance': Rol.DELEGACION,
        'descripcion': 'Dirige una o más delegaciones: registra atenciones y administra a los funcionarios de su equipo.',
        'permisos': {'atenciones.ver', 'atenciones.crear', 'usuarios.ver', 'usuarios.crear', 'usuarios.editar'}
        | _ver('delegaciones', 'items', 'tipos_atencion', 'sub_atenciones', 'tablero', 'actividades',
               'informes')
        | {'validacion.ver', 'validacion.editar', 'agenda.ver', 'agenda.crear', 'agenda.editar',
           'atencion_social.ver', 'atencion_social.crear'},
    },
    {
        'codigo': 'ROL04', 'nombre': 'Funcionario', 'alcance': Rol.DELEGACION,
        'descripcion': 'Atiende a vecinos y vecinas de su delegación y registra su gestión diaria.',
        'permisos': {'atenciones.ver', 'atenciones.crear', 'tablero.ver', 'actividades.ver', 'actividades.crear',
                     'evidencias.ver', 'evidencias.crear', 'agenda.ver', 'agenda.crear', 'agenda.editar',
                     'atencion_social.ver', 'atencion_social.crear'},
    },
    {
        'codigo': 'ROL05', 'nombre': 'Consultor', 'alcance': Rol.GLOBAL,
        'descripcion': 'Acceso de solo lectura a catálogos, atenciones e informes.',
        'permisos': _ver('delegaciones', 'items', 'tipos_atencion', 'sub_atenciones', 'atenciones', 'tablero',
                         'informes'),
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

ITEMS = [
    ('IT001', 'Atenciones en terreno', 'Visitas y atenciones realizadas en el territorio'),
    ('IT002', 'Compromisos cerrados en plazo', 'Compromisos de la agenda cerrados dentro de la fecha'),
    ('IT003', 'Reuniones con organizaciones', 'Reuniones formales con juntas de vecinos y otras organizaciones'),
    ('IT004', 'Casos sociales gestionados', 'Casos del área social con gestión registrada'),
    ('IT005', 'Requerimientos derivados', 'Requerimientos canalizados a unidades municipales'),
    ('IT006', 'Operativos municipales', 'Operativos de limpieza, salud o servicios en el territorio'),
    ('IT007', 'Visitas domiciliarias', 'Visitas a hogares por casos sociales o emergencias'),
    ('IT008', 'Catastros de emergencia', 'Levantamiento de daños tras eventos climáticos'),
    ('IT009', 'Derivaciones a DIDECO', 'Casos derivados a Desarrollo Comunitario'),
    ('IT010', 'Respuestas en plazo', 'Solicitudes respondidas dentro del plazo comprometido'),
    ('IT011', 'Capacitaciones a dirigentes', 'Talleres para dirigentes vecinales'),
    ('IT012', 'Catastro de organizaciones', 'Actualización del registro de organizaciones territoriales'),
    ('IT013', 'Difusión de beneficios', 'Charlas y puntos informativos sobre beneficios municipales'),
    ('IT014', 'Coordinaciones intersectoriales', 'Mesas de trabajo con otros servicios públicos'),
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

# (usuario, nombre, rol, delegaciones, activo)
USUARIOS = [
    ('admin', 'Felipe Aguirre Núñez', 'ROL01', ['DEL04'], True),
    ('emunoz', 'Elena Muñoz Tapia', 'ROL02', ['DEL01'], True),
    ('arojas', 'Ana Rojas Miranda', 'ROL03', ['DEL06', 'DEL03'], True),
    ('bcastillo', 'Bruno Castillo Peña', 'ROL04', ['DEL06'], True),
    ('cvega', 'Camila Vega Soto', 'ROL04', ['DEL06'], True),
    ('dfuentes', 'Diego Fuentes Lara', 'ROL04', ['DEL01'], False),
    ('mtapia', 'Marcela Tapia Cortés', 'ROL03', ['DEL01'], True),
    ('jalvarez', 'Jorge Álvarez Rivera', 'ROL04', ['DEL01'], True),
    ('pcontreras', 'Paula Contreras Díaz', 'ROL04', ['DEL02'], True),
    ('rsilva', 'Rodrigo Silva Morales', 'ROL04', ['DEL03'], True),
    ('lgonzalez', 'Luisa González Pizarro', 'ROL04', ['DEL04'], True),
    ('fortiz', 'Francisco Ortiz Rojas', 'ROL04', ['DEL05'], True),
    ('vcampos', 'Valentina Campos Araya', 'ROL03', ['DEL05', 'DEL02'], True),
    ('lectura', 'Cuenta de Consulta', 'ROL05', ['DEL01'], True),
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
    for codigo, nombre, descripcion in ITEMS:
        ItemMedicion.objects.update_or_create(codigo=codigo, defaults={'nombre': nombre, 'descripcion': descripcion})
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
    for usuario, nombre, rol, codigos, activo in USUARIOS:
        cuenta = Usuario.objects.filter(nombre_usuario=usuario).first()
        if cuenta is None:
            cuenta = Usuario.objects.create_user(usuario, f'{usuario}@example.test', clave,
                                                 nombre=nombre, rol=roles[rol], is_active=activo)
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

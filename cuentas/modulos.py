"""
Catálogo de módulos del sistema y su estado de avance.

Es la fuente única para el menú, los permisos de cada rol y el resumen de
funciones operativas, simuladas y pendientes que exige la pauta.
"""

OPERATIVO = 'operativo'
SIMULADO = 'simulado'

ACCIONES = [
    ('ver', 'Ver'),
    ('crear', 'Crear'),
    ('editar', 'Editar'),
    ('eliminar', 'Eliminar'),
]

# (código, nombre, estado, acciones disponibles, ícono, grupo del menú)
MATRIZ = 'Matriz SGR'
GESTION = 'Gestión municipal'
CONFIG = 'Configuración'
CONTROL = 'Control'
CRUD = ['ver', 'crear', 'editar', 'eliminar']

MODULOS = [
    ('tablero', 'Tablero y semáforo', OPERATIVO, ['ver'], 'bi-speedometer2', MATRIZ),
    ('actividades', 'Actividades y TUBO', OPERATIVO, ['ver', 'crear'], 'bi-journal-text', MATRIZ),
    ('agenda', 'Compromisos (TUBO)', OPERATIVO, ['ver'], 'bi-calendar-week', MATRIZ),
    ('evidencias', 'Evidencias', OPERATIVO, ['ver', 'crear'], 'bi-paperclip', MATRIZ),
    ('validacion', 'Validación', OPERATIVO, ['ver', 'editar'], 'bi-patch-check', MATRIZ),
    ('ausencias', 'Ausencias del equipo', OPERATIVO, ['ver', 'crear', 'eliminar'], 'bi-calendar-x', MATRIZ),
    ('observaciones', 'Felicitaciones y reclamos', OPERATIVO, ['ver', 'crear'], 'bi-award', MATRIZ),
    ('informes', 'Informes', OPERATIVO, ['ver'], 'bi-file-earmark-bar-graph', MATRIZ),
    ('atenciones', 'Atenciones', OPERATIVO, ['ver', 'crear'], 'bi-person-lines-fill', GESTION),
    ('atencion_social', 'Historial por vecino', OPERATIVO, ['ver'], 'bi-heart', GESTION),
    ('organizaciones', 'Organizaciones', OPERATIVO, CRUD, 'bi-people-fill', GESTION),
    ('periodos', 'Períodos', OPERATIVO, ['ver', 'crear', 'editar'], 'bi-calendar3', CONFIG),
    ('metas', 'Metas y ponderaciones', OPERATIVO, ['ver', 'editar'], 'bi-sliders', CONFIG),
    ('cargos', 'Cargos', OPERATIVO, CRUD, 'bi-person-badge', CONFIG),
    ('items', 'Ítems de medición', OPERATIVO, CRUD, 'bi-bullseye', CONFIG),
    ('delegaciones', 'Delegaciones', OPERATIVO, CRUD, 'bi-geo-alt', CONFIG),
    ('tipos_atencion', 'Tipo de Atención', OPERATIVO, CRUD, 'bi-tags', CONFIG),
    ('sub_atenciones', 'Sub Atención', OPERATIVO, CRUD, 'bi-diagram-2', CONFIG),
    ('usuarios', 'Usuarios', OPERATIVO, CRUD, 'bi-people', CONFIG),
    ('roles', 'Roles', OPERATIVO, CRUD, 'bi-shield-lock', CONFIG),
    ('auditoria', 'Auditoría', OPERATIVO, ['ver'], 'bi-clock-history', CONTROL),
    ('correos', 'Correos de prueba', OPERATIVO, ['ver'], 'bi-envelope', CONTROL),
]

# Módulos servidos por el motor de mantenedores (su listado se llama <código>_lista)
MANTENEDORES = {'atenciones', 'delegaciones', 'roles', 'usuarios', 'items', 'tipos_atencion', 'sub_atenciones',
                'cargos', 'organizaciones'}

NOMBRES = {m[0]: m[1] for m in MODULOS}
ESTADOS = {m[0]: m[2] for m in MODULOS}
ORDEN_GRUPOS = [MATRIZ, GESTION, CONFIG, CONTROL]


def todas_las_combinaciones():
    for codigo, _nombre, _estado, acciones, _icono, _grupo in MODULOS:
        for accion in acciones:
            yield codigo, accion

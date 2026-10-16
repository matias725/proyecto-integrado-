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
MODULOS = [
    ('atenciones', 'Atenciones', OPERATIVO, ['ver', 'crear'], 'bi-person-lines-fill', 'Gestión municipal'),
    ('delegaciones', 'Delegaciones', OPERATIVO, ['ver', 'crear', 'editar', 'eliminar'], 'bi-geo-alt', 'Gestión municipal'),
    ('roles', 'Roles', OPERATIVO, ['ver', 'crear', 'editar', 'eliminar'], 'bi-shield-lock', 'Gestión municipal'),
    ('usuarios', 'Usuarios', OPERATIVO, ['ver', 'crear', 'editar', 'eliminar'], 'bi-people', 'Gestión municipal'),
    ('items', 'Ítems y metas', OPERATIVO, ['ver', 'crear', 'editar', 'eliminar'], 'bi-bullseye', 'Gestión municipal'),
    ('tipos_atencion', 'Tipo de Atención', OPERATIVO, ['ver', 'crear', 'editar', 'eliminar'], 'bi-tags', 'Gestión municipal'),
    ('sub_atenciones', 'Sub Atención', OPERATIVO, ['ver', 'crear', 'editar', 'eliminar'], 'bi-diagram-2', 'Gestión municipal'),
    ('auditoria', 'Auditoría', OPERATIVO, ['ver'], 'bi-clock-history', 'Control'),
    ('correos', 'Correos de prueba', OPERATIVO, ['ver'], 'bi-envelope', 'Control'),
    ('tablero', 'Tablero de indicadores', SIMULADO, ['ver'], 'bi-speedometer2', 'Módulos en desarrollo'),
    ('actividades', 'Actividades', SIMULADO, ['ver', 'crear'], 'bi-journal-text', 'Módulos en desarrollo'),
    ('evidencias', 'Evidencias', SIMULADO, ['ver', 'crear'], 'bi-paperclip', 'Módulos en desarrollo'),
    ('validacion', 'Validación', SIMULADO, ['ver', 'editar'], 'bi-patch-check', 'Módulos en desarrollo'),
    ('agenda', 'Agenda colectiva', SIMULADO, ['ver', 'crear', 'editar'], 'bi-calendar-week', 'Módulos en desarrollo'),
    ('atencion_social', 'Atención social', SIMULADO, ['ver', 'crear'], 'bi-heart', 'Módulos en desarrollo'),
    ('periodos', 'Períodos', SIMULADO, ['ver', 'crear', 'editar'], 'bi-calendar3', 'Módulos en desarrollo'),
    ('metas', 'Metas y ponderaciones', SIMULADO, ['ver', 'editar'], 'bi-sliders', 'Módulos en desarrollo'),
    ('informes', 'Informes', SIMULADO, ['ver'], 'bi-file-earmark-bar-graph', 'Módulos en desarrollo'),
]

NOMBRES = {m[0]: m[1] for m in MODULOS}
ESTADOS = {m[0]: m[2] for m in MODULOS}
ORDEN_GRUPOS = ['Gestión municipal', 'Control', 'Módulos en desarrollo']


def todas_las_combinaciones():
    for codigo, _nombre, _estado, acciones, _icono, _grupo in MODULOS:
        for accion in acciones:
            yield codigo, accion

"""
Datos ficticios en memoria para la etapa de templates.

Reemplazan temporalmente a la base de datos: cada lista equivale a una tabla
de sgr_schema.sql. Los cambios hechos desde las pantallas duran mientras el
servidor esté encendido; al reiniciarlo, todo vuelve a este estado inicial.

Ningún dato corresponde a personas reales (Guía SGR, condiciones del caso).
"""

import copy
from datetime import date, datetime

from django.contrib.auth.hashers import check_password, make_password

# ---------------------------------------------------------------------------
# Cuentas de demostración
# La contraseña se guarda como hash (RNF-004), nunca en texto plano.
# ---------------------------------------------------------------------------
CLAVE_DEMO = 'demo1234'
_HASH_DEMO = None


def _hash_demo():
    global _HASH_DEMO
    if _HASH_DEMO is None:
        _HASH_DEMO = make_password(CLAVE_DEMO)
    return _HASH_DEMO


CUENTAS = {
    'bcastillo': {
        'nombre': 'Bruno Castillo Peña',
        'roles': ['Funcionario'],
        'delegacion': 'Rural',
        'cargo': 'Gestor Social',
    },
    'arojas': {
        'nombre': 'Ana Rojas Miranda',
        'roles': ['Delegado', 'Verificador'],
        'delegacion': 'Rural',
        'cargo': 'Delegado',
    },
    'emunoz': {
        'nombre': 'Elena Muñoz Tapia',
        'roles': ['Coordinador'],
        'delegacion': 'Centro',
        'cargo': 'Planificación y Control',
    },
    'faguirre': {
        'nombre': 'Felipe Aguirre Núñez',
        'roles': ['Administrador', 'Funcionario'],
        'delegacion': 'Las Compañías',
        'cargo': 'Apoyo Administrativo',
    },
}


def verificar_cuenta(usuario, clave):
    """Devuelve la cuenta si las credenciales son correctas; si no, None."""
    cuenta = CUENTAS.get((usuario or '').strip().lower())
    if cuenta and check_password(clave or '', _hash_demo()):
        return cuenta
    return None


# ---------------------------------------------------------------------------
# Estado inicial
# ---------------------------------------------------------------------------
INICIAL = {

    'delegaciones': [
        {'id': 1, 'nombre': 'Centro', 'ambito': 'Centro histórico, administrativo y comercial',
         'encargado': 'Elena Muñoz Tapia', 'funcionarios': 8, 'estado': 'ACTIVA',
         'correo': 'centro@laserena.cl', 'cumplimiento': 92.4},
        {'id': 2, 'nombre': 'Avenida del Mar', 'ambito': 'Borde costero, turismo y servicios',
         'encargado': 'Diego Fuentes Lara', 'funcionarios': 6, 'estado': 'ACTIVA',
         'correo': 'avenidadelmar@laserena.cl', 'cumplimiento': 78.1},
        {'id': 3, 'nombre': 'La Antena', 'ambito': 'Sector urbano oriental',
         'encargado': 'Por asignar', 'funcionarios': 5, 'estado': 'ACTIVA',
         'correo': 'antena@laserena.cl', 'cumplimiento': 64.5},
        {'id': 4, 'nombre': 'Las Compañías', 'ambito': 'Sector urbano norte de alta densidad',
         'encargado': 'Felipe Aguirre Núñez', 'funcionarios': 9, 'estado': 'ACTIVA',
         'correo': 'lascompanias@laserena.cl', 'cumplimiento': 88.0},
        {'id': 5, 'nombre': 'La Pampa', 'ambito': 'Sector urbano sur',
         'encargado': 'Por asignar', 'funcionarios': 7, 'estado': 'ACTIVA',
         'correo': 'pampa@laserena.cl', 'cumplimiento': 55.2},
        {'id': 6, 'nombre': 'Rural', 'ambito': 'Localidades y comunidades rurales dispersas',
         'encargado': 'Ana Rojas Miranda', 'funcionarios': 6, 'estado': 'ACTIVA',
         'correo': 'rural@laserena.cl', 'cumplimiento': 71.3},
    ],

    'cargos': [
        'Delegado', 'Territorial Org. Comunitarias', 'Gestor Social', 'Apoyo Administrativo',
        'Supervisor DISERCO', 'Coordinador DISERCO', 'Proyectos y Compras',
        'Planificación y Control', 'Gestor Seguridad',
    ],

    'roles': ['Administrador', 'Coordinador', 'Delegado', 'Funcionario', 'Verificador', 'Consulta'],

    'periodos': [
        {'id': 1, 'nombre': 'Trimestre 2026-Q3', 'inicio': date(2026, 7, 1), 'termino': date(2026, 9, 30),
         'dias': 91, 'estado': 'ABIERTO', 'umbral_verde': 100, 'umbral_ambar': 60,
         'umbral_colectivo': 80, 'tope': 150},
        {'id': 2, 'nombre': 'Trimestre 2026-Q2', 'inicio': date(2026, 4, 1), 'termino': date(2026, 6, 30),
         'dias': 91, 'estado': 'CERRADO', 'umbral_verde': 100, 'umbral_ambar': 60,
         'umbral_colectivo': 80, 'tope': 150},
    ],

    'usuarios': [
        {'id': 1, 'rut': '11.111.111-1', 'nombre': 'Ana Rojas Miranda', 'correo': 'ana.rojas@demo.cl',
         'cargo': 'Delegado', 'delegacion': 'Rural', 'roles': ['Delegado', 'Verificador'], 'estado': 'ACTIVO'},
        {'id': 2, 'rut': '22.222.222-2', 'nombre': 'Bruno Castillo Peña', 'correo': 'bruno.castillo@demo.cl',
         'cargo': 'Gestor Social', 'delegacion': 'Rural', 'roles': ['Funcionario'], 'estado': 'ACTIVO'},
        {'id': 3, 'rut': '33.333.333-3', 'nombre': 'Camila Vega Soto', 'correo': 'camila.vega@demo.cl',
         'cargo': 'Territorial Org. Comunitarias', 'delegacion': 'Rural', 'roles': ['Funcionario'],
         'estado': 'ACTIVO'},
        {'id': 4, 'rut': '44.444.444-4', 'nombre': 'Diego Fuentes Lara', 'correo': 'diego.fuentes@demo.cl',
         'cargo': 'Supervisor DISERCO', 'delegacion': 'Centro', 'roles': ['Funcionario', 'Verificador'],
         'estado': 'ACTIVO'},
        {'id': 5, 'rut': '55.555.555-5', 'nombre': 'Elena Muñoz Tapia', 'correo': 'elena.munoz@demo.cl',
         'cargo': 'Planificación y Control', 'delegacion': 'Centro', 'roles': ['Coordinador'],
         'estado': 'ACTIVO'},
        {'id': 6, 'rut': '66.666.666-6', 'nombre': 'Felipe Aguirre Núñez', 'correo': 'felipe.aguirre@demo.cl',
         'cargo': 'Apoyo Administrativo', 'delegacion': 'Las Compañías',
         'roles': ['Administrador', 'Funcionario'], 'estado': 'ACTIVO'},
    ],

    'items': [
        'Atenciones en terreno',
        'Compromisos cerrados en plazo',
        'Reuniones con organizaciones',
        'Casos sociales gestionados',
        'Requerimientos derivados',
    ],

    'tipos_actividad': [
        {'id': 1, 'nombre': 'Atención de público', 'area': 'Social', 'padre': None},
        {'id': 2, 'nombre': 'Visita a terreno', 'area': 'Territorial', 'padre': None},
        {'id': 3, 'nombre': 'Reunión comunitaria', 'area': 'Territorial', 'padre': None},
        {'id': 4, 'nombre': 'Operativo municipal', 'area': 'Territorial', 'padre': None},
        {'id': 5, 'nombre': 'Orientación de subsidios', 'area': 'Social', 'padre': 1},
        {'id': 6, 'nombre': 'Derivación a DIDECO', 'area': 'Social', 'padre': 1},
        {'id': 7, 'nombre': 'Catastro de emergencia', 'area': 'Territorial', 'padre': 2},
    ],

    # Metas por cargo y período. La suma de ponderadores es 100 % (RN-001).
    'metas': [
        {'id': 1, 'cargo': 'Gestor Social', 'periodo': 1, 'item': 'Atenciones en terreno',
         'objetivo': 60, 'ponderador': 30, 'avance': 18, 'version': 2},
        {'id': 2, 'cargo': 'Gestor Social', 'periodo': 1, 'item': 'Compromisos cerrados en plazo',
         'objetivo': 25, 'ponderador': 20, 'avance': 20, 'version': 1},
        {'id': 3, 'cargo': 'Gestor Social', 'periodo': 1, 'item': 'Casos sociales gestionados',
         'objetivo': 40, 'ponderador': 35, 'avance': 25, 'version': 1},
        {'id': 4, 'cargo': 'Gestor Social', 'periodo': 1, 'item': 'Requerimientos derivados',
         'objetivo': 30, 'ponderador': 15, 'avance': 24, 'version': 1},
        # Período cerrado: sus resultados quedan congelados (RN-013)
        {'id': 5, 'cargo': 'Gestor Social', 'periodo': 2, 'item': 'Atenciones en terreno',
         'objetivo': 60, 'ponderador': 25, 'avance': 57, 'version': 1},
        {'id': 6, 'cargo': 'Gestor Social', 'periodo': 2, 'item': 'Compromisos cerrados en plazo',
         'objetivo': 25, 'ponderador': 25, 'avance': 25, 'version': 1},
        {'id': 7, 'cargo': 'Gestor Social', 'periodo': 2, 'item': 'Casos sociales gestionados',
         'objetivo': 40, 'ponderador': 35, 'avance': 31, 'version': 1},
        {'id': 8, 'cargo': 'Gestor Social', 'periodo': 2, 'item': 'Requerimientos derivados',
         'objetivo': 30, 'ponderador': 15, 'avance': 30, 'version': 1},
        {'id': 9, 'cargo': 'Territorial Org. Comunitarias', 'periodo': 1, 'item': 'Atenciones en terreno',
         'objetivo': 50, 'ponderador': 25, 'avance': 21, 'version': 1},
        {'id': 10, 'cargo': 'Territorial Org. Comunitarias', 'periodo': 1,
         'item': 'Reuniones con organizaciones', 'objetivo': 20, 'ponderador': 40, 'avance': 14, 'version': 1},
        {'id': 11, 'cargo': 'Territorial Org. Comunitarias', 'periodo': 1, 'item': 'Requerimientos derivados',
         'objetivo': 35, 'ponderador': 35, 'avance': 19, 'version': 1},
    ],

    'actividades': [
        {'id': 1, 'codigo': 'EV-2026-000001', 'fecha': date(2026, 9, 1), 'funcionario': 'Bruno Castillo Peña',
         'delegacion': 'Rural', 'descripcion': 'Solicitud de orientación sobre subsidio habitacional',
         'accion': 'Se orienta y se agenda seguimiento', 'item': 'Casos sociales gestionados',
         'tipo': 'Orientación de subsidios', 'estado': 'VALIDADA', 'evidencia': 'APROBADA'},
        {'id': 2, 'codigo': 'EV-2026-000002', 'fecha': date(2026, 9, 2), 'funcionario': 'Bruno Castillo Peña',
         'delegacion': 'Rural', 'descripcion': 'Atención de público en delegación',
         'accion': 'Se registra requerimiento y se deriva', 'item': 'Atenciones en terreno',
         'tipo': 'Atención de público', 'estado': 'REGISTRADA', 'evidencia': 'SIN_EVIDENCIA'},
        {'id': 3, 'codigo': 'EV-2026-000003', 'fecha': date(2026, 9, 3), 'funcionario': 'Camila Vega Soto',
         'delegacion': 'Rural', 'descripcion': 'Reunión con junta de vecinos Las Rojas',
         'accion': 'Se levanta acta y compromiso de luminarias', 'item': 'Reuniones con organizaciones',
         'tipo': 'Reunión comunitaria', 'estado': 'VALIDADA', 'evidencia': 'APROBADA'},
        {'id': 4, 'codigo': 'EV-2026-000004', 'fecha': date(2026, 9, 4), 'funcionario': 'Camila Vega Soto',
         'delegacion': 'Rural', 'descripcion': 'Visita a terreno sector El Romero',
         'accion': 'Catastro de necesidades de conectividad', 'item': 'Atenciones en terreno',
         'tipo': 'Visita a terreno', 'estado': 'RECHAZADA', 'evidencia': 'RECHAZADA'},
        {'id': 5, 'codigo': 'EV-2026-000005', 'fecha': date(2026, 9, 8), 'funcionario': 'Diego Fuentes Lara',
         'delegacion': 'Centro', 'descripcion': 'Operativo de limpieza en calle Cienfuegos',
         'accion': 'Coordinación con aseo y retiro de escombros', 'item': 'Requerimientos derivados',
         'tipo': 'Operativo municipal', 'estado': 'REGISTRADA', 'evidencia': 'PENDIENTE'},
        {'id': 6, 'codigo': 'EV-2026-000006', 'fecha': date(2026, 9, 9), 'funcionario': 'Bruno Castillo Peña',
         'delegacion': 'Rural', 'descripcion': 'Catastro de daños por lluvia en El Islón',
         'accion': 'Levantamiento de viviendas afectadas', 'item': 'Atenciones en terreno',
         'tipo': 'Catastro de emergencia', 'estado': 'REGISTRADA', 'evidencia': 'PENDIENTE'},
        {'id': 7, 'codigo': 'EV-2026-000007', 'fecha': date(2026, 9, 10), 'funcionario': 'Camila Vega Soto',
         'delegacion': 'Rural', 'descripcion': 'Reunión con Comité de Agua Potable Rural',
         'accion': 'Se acuerda operativo de limpieza de canal', 'item': 'Reuniones con organizaciones',
         'tipo': 'Reunión comunitaria', 'estado': 'REGISTRADA', 'evidencia': 'PENDIENTE'},
        {'id': 8, 'codigo': 'EV-2026-000008', 'fecha': date(2026, 9, 11), 'funcionario': 'Ana Rojas Miranda',
         'delegacion': 'Rural', 'descripcion': 'Coordinación con DIDECO por casos sociales',
         'accion': 'Se priorizan tres derivaciones pendientes', 'item': 'Requerimientos derivados',
         'tipo': 'Derivación a DIDECO', 'estado': 'REGISTRADA', 'evidencia': 'PENDIENTE'},
    ],

    'compromisos': [
        {'id': 1, 'solicitante': 'Junta de Vecinos Las Rojas', 'territorio': 'Las Rojas', 'delegacion': 'Rural',
         'descripcion': 'Reposición de luminarias en calle principal', 'responsable': 'Bruno Castillo Peña',
         'fecha': date(2026, 9, 20), 'fecha_cierre': None, 'estado': 'EN_PROCESO',
         'historial': [
             {'fecha': datetime(2026, 9, 3, 10, 15), 'usuario': 'Camila Vega Soto', 'anterior': None,
              'nuevo': 'INGRESADO', 'observacion': 'Compromiso adquirido en reunión con la junta'},
             {'fecha': datetime(2026, 9, 4, 9, 0), 'usuario': 'Bruno Castillo Peña', 'anterior': 'INGRESADO',
              'nuevo': 'PENDIENTE', 'observacion': 'Derivado a Servicios a la Comunidad'},
             {'fecha': datetime(2026, 9, 8, 9, 20), 'usuario': 'Bruno Castillo Peña', 'anterior': 'PENDIENTE',
              'nuevo': 'EN_PROCESO', 'observacion': 'Equipo en terreno'},
         ]},
        {'id': 2, 'solicitante': 'Comité de Agua Potable Rural', 'territorio': 'El Romero', 'delegacion': 'Rural',
         'descripcion': 'Coordinar operativo de limpieza de canal', 'responsable': 'Camila Vega Soto',
         'fecha': date(2026, 9, 5), 'fecha_cierre': None, 'estado': 'PENDIENTE',
         'historial': [
             {'fecha': datetime(2026, 8, 29, 16, 40), 'usuario': 'Camila Vega Soto', 'anterior': None,
              'nuevo': 'INGRESADO', 'observacion': 'Solicitud recibida en terreno'},
             {'fecha': datetime(2026, 8, 30, 11, 5), 'usuario': 'Camila Vega Soto', 'anterior': 'INGRESADO',
              'nuevo': 'PENDIENTE', 'observacion': 'A la espera de maquinaria'},
         ]},
        {'id': 3, 'solicitante': 'Cámara de Comercio', 'territorio': 'Centro', 'delegacion': 'Centro',
         'descripcion': 'Retiro de escombros en calle Cienfuegos', 'responsable': 'Diego Fuentes Lara',
         'fecha': date(2026, 8, 28), 'fecha_cierre': date(2026, 8, 27), 'estado': 'REALIZADO',
         'historial': [
             {'fecha': datetime(2026, 8, 20, 12, 0), 'usuario': 'Diego Fuentes Lara', 'anterior': None,
              'nuevo': 'INGRESADO', 'observacion': 'Solicitud de la cámara'},
             {'fecha': datetime(2026, 8, 27, 17, 30), 'usuario': 'Diego Fuentes Lara', 'anterior': 'EN_PROCESO',
              'nuevo': 'REALIZADO', 'observacion': 'Retiro ejecutado y verificado'},
         ]},
        {'id': 4, 'solicitante': 'Club Deportivo El Milagro', 'territorio': 'El Milagro', 'delegacion': 'Rural',
         'descripcion': 'Mantención de multicancha del sector', 'responsable': 'Bruno Castillo Peña',
         'fecha': date(2026, 9, 1), 'fecha_cierre': None, 'estado': 'PENDIENTE',
         'historial': [
             {'fecha': datetime(2026, 8, 25, 15, 10), 'usuario': 'Bruno Castillo Peña', 'anterior': None,
              'nuevo': 'INGRESADO', 'observacion': 'Solicitud del club'},
             {'fecha': datetime(2026, 8, 26, 9, 45), 'usuario': 'Bruno Castillo Peña', 'anterior': 'INGRESADO',
              'nuevo': 'PENDIENTE', 'observacion': 'Se solicita presupuesto a Proyectos y Compras'},
         ]},
    ],

    'casos_sociales': [
        {'id': 1, 'rut': '99.999.999-9', 'nombre': 'Persona Usuaria Demo', 'telefono': '+56 9 5555 5555',
         'delegacion': 'Rural', 'apertura': date(2026, 7, 10), 'estado': 'ABIERTO',
         'gestiones': [
             {'numero': 1, 'fecha': date(2026, 7, 10), 'tipo': 'Atención de público',
              'resultado': 'Ingreso del caso y evaluación inicial'},
             {'numero': 2, 'fecha': date(2026, 8, 5), 'tipo': 'Orientación de subsidios',
              'resultado': 'Orientación de subsidio y postulación'},
             {'numero': 3, 'fecha': date(2026, 9, 1), 'tipo': 'Derivación a DIDECO',
              'resultado': 'Derivación para apoyo complementario'},
         ]},
        {'id': 2, 'rut': '88.888.888-8', 'nombre': 'Caso Demostración Dos', 'telefono': '+56 9 4444 4444',
         'delegacion': 'Rural', 'apertura': date(2026, 8, 22), 'estado': 'ABIERTO',
         'gestiones': [
             {'numero': 1, 'fecha': date(2026, 8, 22), 'tipo': 'Atención de público',
              'resultado': 'Solicitud de ayuda social'},
         ]},
    ],

    'auditoria': [
        {'fecha': datetime(2026, 9, 9, 11, 42), 'usuario': 'Ana Rojas Miranda', 'evento': 'VALIDACION',
         'entidad': 'evidencia', 'registro': 4, 'anterior': 'PENDIENTE', 'nuevo': 'RECHAZADA'},
        {'fecha': datetime(2026, 9, 8, 16, 5), 'usuario': 'Elena Muñoz Tapia', 'evento': 'CAMBIO_PARAMETRO',
         'entidad': 'meta', 'registro': 1, 'anterior': 'ponderador=25,00', 'nuevo': 'ponderador=30,00'},
        {'fecha': datetime(2026, 9, 8, 9, 20), 'usuario': 'Bruno Castillo Peña', 'evento': 'CAMBIO_ESTADO',
         'entidad': 'compromiso', 'registro': 1, 'anterior': 'PENDIENTE', 'nuevo': 'EN_PROCESO'},
        {'fecha': datetime(2026, 9, 5, 14, 58), 'usuario': 'Felipe Aguirre Núñez', 'evento': 'ALTA',
         'entidad': 'delegación', 'registro': 6, 'anterior': '—', 'nuevo': 'Rural'},
        {'fecha': datetime(2026, 9, 4, 10, 13), 'usuario': 'Camila Vega Soto', 'evento': 'ALTA',
         'entidad': 'actividad', 'registro': 4, 'anterior': '—', 'nuevo': 'EV-2026-000004'},
    ],
}

# Almacén en uso. Se modifica en el lugar para que todas las vistas vean
# siempre el mismo objeto.
almacen = copy.deepcopy(INICIAL)


def reiniciar():
    """Restituye los datos al estado inicial. Lo usan las pruebas."""
    almacen.clear()
    almacen.update(copy.deepcopy(INICIAL))


def siguiente_id(tabla):
    return max((fila['id'] for fila in almacen[tabla]), default=0) + 1


def buscar(tabla, **criterios):
    """Primer registro que cumple todos los criterios, o None."""
    for fila in almacen[tabla]:
        if all(fila.get(campo) == valor for campo, valor in criterios.items()):
            return fila
    return None


def registrar_auditoria(usuario, evento, entidad, registro, anterior, nuevo):
    """RF-036: toda operación crítica deja usuario, fecha, valor anterior y nuevo."""
    almacen['auditoria'].insert(0, {
        'fecha': datetime.now().replace(microsecond=0),
        'usuario': usuario,
        'evento': evento,
        'entidad': entidad,
        'registro': registro,
        'anterior': anterior if anterior not in (None, '') else '—',
        'nuevo': nuevo if nuevo not in (None, '') else '—',
    })

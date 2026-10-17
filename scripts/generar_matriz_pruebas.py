"""
Genera la matriz de pruebas funcionales de la EV2 (docs/pruebas/matriz_pruebas_sgr_ev2.xlsx).

1. Ejecuta las pruebas automatizadas (pruebas/ y, con --ui, pruebas_ui/).
2. Cruza cada caso funcional con las pruebas que lo verifican y marca el estado.
3. Agrega las hojas de pruebas automatizadas, estrés, umbrales y pendientes.

Uso:  python scripts/generar_matriz_pruebas.py [--ui] [--estres docs/pruebas/estres/local]
"""

import argparse
import csv
import os
import sys
import time
import unittest
from datetime import date, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgr.settings')
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

import django  # noqa: E402

django.setup()

from django.test.utils import get_runner  # noqa: E402
from django.conf import settings  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

NOTA_ESTRES = ('Lectura: el cuello de botella es el inicio de sesión simultáneo (cada acceso calcula el hash '
                   'PBKDF2 de la contraseña, ~0,3 s de CPU). Al subir 50-100 usuarios a razón de 10-20 por segundo, '
                   'la CPU llega al 100 % mientras ingresan; una vez dentro, las páginas vuelven a responder en '
                   'decenas de milisegundos. En la corrida local Locust compartía la misma CPU que el servidor; '
                   'en AWS (t3.small) las latencias incluyen ~150 ms de red entre Chile y us-east-1. '
                   'Mejora propuesta: más vCPU o un balanceador con dos instancias para absorber los ingresos simultáneos.')

ALEXIS, MATIAS, CARLOS = 'Alexis Muñoz', 'Matías Zepeda', 'Carlos Araya'
HOY = date.today().strftime('%d-%m-%Y')

# ---------------------------------------------------------------------------
# Casos funcionales (lo que pide el enunciado), cada uno con sus pruebas
# automatizadas de respaldo y su evidencia visual cuando existe.
# (id, requisito, módulo, precondiciones, pasos, esperado, pruebas, evidencia, responsable)
# ---------------------------------------------------------------------------
CASOS = [
    # ----- Acceso -----
    ('CF-01', 'Acceso con usuario o correo', 'Acceso', 'Cuenta activa bcastillo',
     '1. Abrir el sistema. 2. Ingresar «bcastillo» y la contraseña. 3. Repetir con «BCastillo@Example.TEST».',
     'Ingresa al inicio; la cabecera muestra nombre, rol y delegación activa. Correo sin distinguir mayúsculas.',
     ['PA-01', 'PA-02', 'PD-01'], '', ALEXIS),
    ('CF-02', 'Acceso incorrecto', 'Acceso', 'Cuenta activa admin',
     '1. Ingresar «admin» con contraseña errónea. 2. Ingresar un usuario inexistente.',
     'SweetAlert2 de error con el mismo mensaje genérico en ambos casos; no se crea sesión; queda en auditoría.',
     ['PA-03', 'PA-04', 'UI-01'], 'UI-01-acceso-incorrecto.png', ALEXIS),
    ('CF-03', 'Campos vacíos', 'Acceso', 'Ninguna',
     '1. Presionar «Ingresar» sin completar los campos.',
     'Ambos campos se marcan como obligatorios en el navegador y el servidor también los rechaza.',
     ['PA-05', 'UI-02'], 'UI-02-validacion-cliente.png', ALEXIS),
    ('CF-04', 'Cuenta inactiva', 'Acceso', 'Cuenta dfuentes inactiva',
     '1. Ingresar «dfuentes» con su contraseña correcta. 2. Con contraseña errónea.',
     'Con la clave correcta informa «cuenta inactiva»; con la errónea, mensaje genérico. No ingresa.',
     ['PA-06', 'PA-07', 'PA-08'], '', ALEXIS),
    ('CF-05', 'Bloqueo por intentos fallidos', 'Acceso', 'Cuenta activa cvega',
     '1. Fallar la contraseña 5 veces seguidas. 2. Ingresar con la contraseña correcta.',
     'El acceso queda bloqueado temporalmente (10 min) aunque la contraseña sea correcta.',
     ['PA-09'], '', ALEXIS),
    ('CF-06', 'Cerrar sesión', 'Acceso', 'Sesión iniciada',
     '1. Presionar «Salir». 2. Volver atrás o escribir /inicio/.',
     'Vuelve al acceso; las páginas internas exigen iniciar sesión nuevamente.',
     ['PA-10', 'PA-11'], '', ALEXIS),
    ('CF-07', 'Rutas protegidas', 'Acceso', 'Sin sesión',
     '1. Escribir directamente /delegaciones/, /usuarios/, /atenciones/nueva/, /auditoria/.',
     'Redirige al acceso y, tras ingresar, vuelve a la ruta pedida (nunca a un sitio externo).',
     ['PA-12', 'PA-13'], '', ALEXIS),
    # ----- Recuperación -----
    ('CF-08', 'Solicitar código', 'Recuperación', 'Cuenta activa bcastillo',
     '1. «¿Olvidó su contraseña?». 2. Ingresar bcastillo@example.test. 3. Revisar la bandeja de correos de prueba.',
     'Mensaje que no revela si la cuenta existe; llega un correo con un código de 6 dígitos que vence en 10 minutos.',
     ['PR-01', 'PR-02', 'PR-04', 'PR-09', 'PR-21'], '', ALEXIS),
    ('CF-09', 'Validar código correcto e incorrecto', 'Recuperación', 'Código solicitado',
     '1. Ingresar un código incorrecto. 2. Ingresar el código correcto (puede pegarse en las 6 casillas).',
     'El incorrecto informa los intentos restantes; el correcto avanza al paso 3.',
     ['PR-06', 'PR-11', 'UI-12'], 'UI-12-codigo-pegado.png', ALEXIS),
    ('CF-10', 'Código vencido, reutilizado y límite de intentos', 'Recuperación', 'Código solicitado',
     '1. Usar un código después de 10 min. 2. Reusar un código ya utilizado. 3. Fallar 5 veces y luego usar el correcto.',
     'Los tres casos se rechazan con un mensaje claro y piden solicitar un código nuevo.',
     ['PR-07', 'PR-08', 'PR-10'], '', ALEXIS),
    ('CF-11', 'Reenvío de código', 'Recuperación', 'Código solicitado',
     '1. Intentar reenviar antes de 45 s. 2. Reenviar después de 45 s. 3. Usar el código anterior.',
     'El botón espera 45 s con cuenta regresiva; el nuevo código anula el anterior; máximo 5 códigos por hora.',
     ['PR-12', 'PR-13', 'PR-14', 'UI-12'], '', ALEXIS),
    ('CF-12', 'Nueva contraseña', 'Recuperación', 'Código verificado',
     '1. Probar claves que no cumplen requisitos o no coinciden. 2. Guardar una válida. 3. Ingresar con la antigua y con la nueva.',
     'Requisitos visibles y validados; el código queda invalidado; la nueva funciona y la antigua no.',
     ['PR-05', 'PR-17', 'PR-18', 'PR-19', 'PR-20'], '', ALEXIS),
    ('CF-13', 'Pasos fuera de orden', 'Recuperación', 'Sin código',
     '1. Escribir /recuperar/validar/ o /recuperar/nueva/ directamente.',
     'Redirige al paso que corresponde; no se puede cambiar la contraseña sin código verificado.',
     ['PR-15', 'PR-16'], '', ALEXIS),
    # ----- Mantenedores -----
    ('CF-14', 'CRUD de Delegaciones', 'Delegaciones', 'Perfil admin',
     '1. Crear DEL07. 2. Consultar. 3. Editar dirección. 4. Desactivar/activar. 5. Eliminar.',
     'Cada operación confirma con SweetAlert2 y queda en el historial de auditoría.',
     ['PC-01', 'PC-04', 'PC-06'], '', MATIAS),
    ('CF-15', 'CRUD de Roles y permisos', 'Roles', 'Perfil admin',
     '1. Crear un rol con permisos en la matriz. 2. Editar. 3. Desactivar. 4. Eliminar.',
     'El rol y sus permisos se guardan; el rol protegido no se elimina ni desactiva.',
     ['PC-01', 'PI-09', 'PI-10'], '', MATIAS),
    ('CF-16', 'CRUD de Usuarios', 'Usuarios', 'Perfil admin',
     '1. Crear usuario con rol, delegaciones y contraseña. 2. Editar sin cambiar clave. 3. Desactivar. 4. Eliminar.',
     'Correo y usuario únicos; la contraseña cumple requisitos; nadie se desactiva a sí mismo.',
     ['PC-01', 'PI-11', 'PI-12', 'PI-13', 'PI-14', 'PI-15'], '', MATIAS),
    ('CF-17', 'CRUD de Ítems y metas', 'Ítems', 'Perfil admin',
     '1. Crear IT099. 2. Consultar. 3. Editar. 4. Desactivar. 5. Eliminar.', 'Operaciones completas y auditadas.',
     ['PC-01', 'PC-02'], 'UI-04-eliminado.png', MATIAS),
    ('CF-18', 'CRUD de Tipo de Atención', 'Tipo de Atención', 'Perfil admin',
     '1. Crear TA099. 2. Editar. 3. Intentar desactivar un tipo con sub atenciones activas. 4. Intentar eliminarlo.',
     'Alta y edición correctas; desactivar o eliminar un tipo con sub atenciones se rechaza con mensaje de error.',
     ['PC-01', 'PC-05', 'PI-03', 'PI-04', 'UI-05'], 'UI-05-eliminar-con-relaciones.png', MATIAS),
    ('CF-19', 'CRUD de Sub Atención', 'Sub Atención', 'Perfil admin',
     '1. Crear SA099 con tipo activo. 2. Intentar con tipo inactivo. 3. Duplicar nombre en el mismo tipo. 4. Eliminar una usada.',
     'Solo tipos activos; nombre único dentro del tipo; no se elimina si tiene atenciones.',
     ['PC-01', 'PI-05', 'PI-06', 'PI-07', 'PI-08'], '', MATIAS),
    ('CF-20', 'Validaciones de formularios', 'Mantenedores', 'Perfil admin',
     '1. Guardar formularios vacíos. 2. Duplicar código/nombre. 3. Código con formato inválido.',
     'Errores por campo en el navegador y en el servidor; SweetAlert2 de error y nunca de éxito.',
     ['PC-03', 'PC-04', 'PC-05', 'PS-02'], '', MATIAS),
    ('CF-21', 'Confirmar y cancelar eliminación', 'Mantenedores', 'Perfil admin',
     '1. Presionar «Eliminar». 2. Cancelar en el diálogo. 3. Repetir y confirmar.',
     'Cancelar no elimina; confirmar elimina y muestra éxito. Eliminar por GET no está permitido.',
     ['UI-03', 'UI-04', 'PC-02', 'PS-03'], 'UI-03-confirmar-eliminar.png', MATIAS),
    # ----- Listados y Excel -----
    ('CF-22', 'Paginador y total', 'Listados', '14 ítems cargados',
     '1. Abrir Ítems y metas. 2. Navegar páginas. 3. Escribir una página inexistente en la URL.',
     'Muestra «Mostrando X a Y de N registros»; página inválida muestra la última válida sin error.',
     ['PL-01', 'PL-02'], '', MATIAS),
    ('CF-23', 'Búsqueda inteligente', 'Listados', 'Datos de demostración',
     '1. Buscar «aNTEN» en Delegaciones. 2. Buscar por dirección. 3. Buscar dos palabras en Usuarios.',
     'Coincidencia parcial, sin distinguir mayúsculas y en varios campos; estado «sin coincidencias» claro.',
     ['PL-03', 'PL-04', 'PL-05'], '', MATIAS),
    ('CF-24', 'Filtros al paginar', 'Listados', 'Datos de demostración',
     '1. Filtrar por texto y estado. 2. Ir a la página 2.', 'Los filtros se conservan en la URL y en el paginador.',
     ['PL-06', 'PL-07', 'PL-08'], '', MATIAS),
    ('CF-25', 'Exportar a Excel', 'Listados', 'Listado filtrado',
     '1. Filtrar Sub Atención por «salud». 2. «Exportar a Excel». 3. Comparar con el listado.',
     'El .xlsx trae todos los resultados filtrados (no solo la página), filtros aplicados y total; sin contraseñas ni tokens.',
     ['PL-09', 'PL-10', 'PL-11', 'PL-12', 'PL-13', 'UI-13'], '', MATIAS),
    # ----- Ingreso de atención -----
    ('CF-26', 'Registrar atención', 'Ingreso de atención', 'Funcionario bcastillo (DEL06)',
     '1. «Ingresar atención». 2. Completar RUT, nombre, tipo, sub atención y descripción. 3. Guardar.',
     'SweetAlert2 con el folio AT-AAAA-NNNNNN; delegación, responsable y fecha asignados automáticamente.',
     ['PT-01', 'PT-02', 'PT-12'], 'UI-07-folio-confirmado.png', CARLOS),
    ('CF-27', 'Lista dependiente tipo → sub atención', 'Ingreso de atención', 'Tipos con sub atenciones',
     '1. Elegir un tipo y una sub atención. 2. Cambiar el tipo.',
     'Solo aparecen sub atenciones activas del tipo; al cambiar el tipo la sub atención se limpia.',
     ['PT-04', 'PT-05', 'PT-06', 'PT-07', 'PT-08', 'UI-06'], 'UI-06-lista-dependiente.png', CARLOS),
    ('CF-28', 'Prevenir doble envío', 'Ingreso de atención', 'Formulario completo',
     '1. Hacer doble clic en «Guardar atención». 2. Reenviar el mismo formulario.',
     'Se crea una sola atención; el segundo envío informa que ya estaba registrada.',
     ['PT-03', 'UI-07'], 'UI-07-folio-confirmado.png', CARLOS),
    ('CF-29', 'Cancelar ingreso', 'Ingreso de atención', 'Formulario con datos',
     '1. Escribir datos. 2. «Cancelar» y confirmar descartar.', 'Pide confirmación y no crea registros.',
     ['PT-13', 'UI-08'], 'UI-08-descartar-cambios.png', CARLOS),
    ('CF-30', 'Validaciones de la atención', 'Ingreso de atención', 'Formulario',
     '1. Guardar vacío. 2. RUT con dígito verificador incorrecto. 3. Descripción corta.',
     'Errores por campo; no se guarda.', ['PT-09', 'PT-10', 'PT-11'], 'UI-02-validacion-cliente.png', CARLOS),
    # ----- Perfiles y delegación -----
    ('CF-31', 'Menú por perfil', 'Roles y permisos', 'Cuentas admin, emunoz, arojas, bcastillo',
     '1. Ingresar con cada perfil y revisar el menú lateral.',
     'Cada perfil ve solo sus módulos; los simulados se marcan «Simulado».',
     ['PP-01', 'PP-02', 'PP-03', 'PP-04', 'PP-05', 'UI-11'], 'UI-11-menu-bcastillo.png', ALEXIS),
    ('CF-32', 'Rechazo al alterar rutas', 'Roles y permisos', 'Funcionario bcastillo',
     '1. Escribir /roles/, /usuarios/nuevo/, /auditoria/. 2. Enviar un POST de eliminar sin permiso.',
     'Pantalla 403 «Acceso denegado», sin cambios en los datos y con registro en auditoría.',
     ['PP-07', 'PP-08', 'PP-09', 'PP-10', 'PD-08', 'PD-09'], '', ALEXIS),
    ('CF-33', 'Escalada de privilegios', 'Usuarios', 'Delegada arojas',
     '1. Crear un usuario con rol Superadministrador. 2. Asignar una delegación ajena. 3. Editar un usuario de otra delegación por URL.',
     'Todo se rechaza en el servidor; las delegaciones fuera de su alcance se conservan al editar.',
     ['PP-11', 'PP-12', 'PP-13', 'PP-14', 'PP-15', 'PP-16'], '', ALEXIS),
    ('CF-34', 'Contexto con una delegación', 'Cabecera', 'Funcionario bcastillo',
     '1. Ingresar y revisar la cabecera.', 'Muestra DEL06 · Delegación Rural con candado: contexto fijo, sin selector.',
     ['PD-01', 'PD-02'], 'UI-07-folio-confirmado.png', ALEXIS),
    ('CF-35', 'Cambio de delegación activa', 'Cabecera', 'Delegada arojas (DEL03, DEL06)',
     '1. Elegir la otra delegación en el selector. 2. Confirmar. 3. Revisar listado y Excel.',
     'Solo ofrece las autorizadas; al confirmar cambian cabecera, listados, filtros y exportación.',
     ['PD-03', 'PD-04', 'UI-10'], 'UI-10-contexto-cambiado.png', ALEXIS),
    ('CF-36', 'Advertencia de cambios sin guardar', 'Cabecera', 'Formulario con datos',
     '1. Escribir en un formulario. 2. Cambiar la delegación activa.',
     'SweetAlert2 advierte que se perderán los cambios; al cancelar se mantiene la delegación.',
     ['UI-09'], 'UI-09-cambio-contexto.png', ALEXIS),
    ('CF-37', 'Contexto forzado', 'Cabecera', 'Delegada arojas',
     '1. Enviar al servidor una delegación no autorizada. 2. Alterar la sesión.',
     'Se rechaza con 403 y auditoría; el servidor vuelve a una delegación válida.',
     ['PD-05', 'PD-06', 'PD-07'], '', ALEXIS),
    # ----- Transversales -----
    ('CF-38', 'Mensajes con SweetAlert2', 'Interfaz', 'Cualquier perfil',
     '1. Guardar un registro. 2. Provocar un error. 3. Cancelar una acción.',
     'Éxito, error, advertencia y confirmación con SweetAlert2 institucional; nunca éxito si la operación falló.',
     ['PS-01', 'PS-02', 'PS-04', 'PS-05', 'UI-04', 'UI-05'], 'UI-04-eliminado.png', CARLOS),
    ('CF-39', 'Auditoría', 'Auditoría', 'Perfil admin',
     '1. Realizar operaciones. 2. Revisar Auditoría y filtrar por evento.',
     'Registro de solo lectura, sin contraseñas, filtrable y exportable.',
     ['PU-01', 'PU-02'], '', CARLOS),
    ('CF-40', 'Robustez y seguridad básica', 'Sistema', 'Ninguna',
     '1. Consultar /salud/. 2. Abrir rutas inexistentes. 3. Enviar formularios sin token CSRF.',
     'Salud 200; 404 claros; envíos sin token se rechazan sin guardar; cabeceras de seguridad presentes.',
     ['PX-01', 'PX-02', 'PX-03', 'PX-04', 'PX-06'], '', CARLOS),
    ('CF-41', 'Módulos simulados navegables', 'Módulos en desarrollo', 'Perfil admin y bcastillo',
     '1. Abrir tablero, actividades, evidencias, validación, agenda, atención social, períodos, metas e informes.',
     'Todas las pantallas cargan, se identifican como simuladas y respetan los permisos del rol.',
     ['PX-05', 'PP-10'], '', CARLOS),
    ('CF-42', 'Diseño adaptable', 'Interfaz', 'Teléfono (390 px)',
     '1. Ingresar desde un teléfono. 2. Abrir el menú.',
     'Sin desplazamiento horizontal; menú desplegable; selector de delegación visible.',
     ['UI-14'], 'UI-14-movil.png', CARLOS),
]

GRUPOS = {
    'PA': 'Acceso', 'PR': 'Recuperación', 'PC': 'Mantenedores', 'PI': 'Integridad', 'PL': 'Listados y Excel',
    'PP': 'Perfiles y permisos', 'PD': 'Contexto de delegación', 'PT': 'Ingreso de atención',
    'PS': 'SweetAlert2', 'PU': 'Auditoría', 'PX': 'Sistema', 'UI': 'Interfaz (navegador)',
}


# ---------------------------------------------------------------------------
# Ejecución de las pruebas automatizadas
# ---------------------------------------------------------------------------
class Registro(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.resultados = {}
        self._inicio = {}

    def _id(self, test):
        doc = (test.shortDescription() or test.id()).split('·')
        return doc[0].strip(), (doc[1].strip() if len(doc) > 1 else ''), test.id()

    def startTest(self, test):
        self._inicio[test.id()] = time.perf_counter()
        super().startTest(test)

    def _guardar(self, test, estado, detalle=''):
        cid, desc, ruta = self._id(test)
        previo = self.resultados.get(cid)
        if previo and previo[2] != 'Aprobada' and estado == 'Aprobada':
            return  # un subTest fallido prevalece
        dur = time.perf_counter() - self._inicio.get(test.id(), time.perf_counter())
        self.resultados[cid] = (desc, ruta, estado, detalle[:300], round(dur, 2))

    def addSuccess(self, test):
        super().addSuccess(test)
        self._guardar(test, 'Aprobada')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._guardar(test, 'Fallida', str(err[1]))

    def addError(self, test, err):
        super().addError(test, err)
        self._guardar(test, 'Error', str(err[1]))

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._guardar(test, 'Fallida', f'{subtest._subDescription()}: {err[1]}')


def ejecutar(etiquetas):
    Runner = get_runner(settings)

    class RunnerConRegistro(Runner):
        def get_resultclass(self):
            return Registro

        def run_suite(self, suite, **kwargs):
            self.ultimo = super().run_suite(suite, **kwargs)
            return self.ultimo

    runner = RunnerConRegistro(verbosity=1)
    runner.run_tests(etiquetas)
    return runner.ultimo.resultados


# ---------------------------------------------------------------------------
# Resultados de estrés
# ---------------------------------------------------------------------------
def leer_estres(carpeta):
    carpeta = Path(carpeta)
    etapas = []
    monitor = []
    if (carpeta / 'monitor.csv').exists():
        monitor = list(csv.DictReader(open(carpeta / 'monitor.csv', encoding='utf-8')))
    for usuarios in (10, 25, 50, 100):
        stats = carpeta / f'c{usuarios}_stats.csv'
        if not stats.exists():
            continue
        filas = list(csv.DictReader(open(stats, encoding='utf-8')))
        total = next(f for f in filas if f['Name'] == 'Aggregated')
        historial = list(csv.DictReader(open(carpeta / f'c{usuarios}_stats_history.csv', encoding='utf-8')))
        agregados = [h for h in historial if h['Name'] == 'Aggregated']
        t0, t1 = int(agregados[0]['Timestamp']), int(agregados[-1]['Timestamp'])
        etapas.append({'usuarios': usuarios, 'total': total, 'filas': filas, 'inicio': t0, 'fin': t1})
    return etapas, monitor


def recursos(monitor, inicio_monitor, t0, t1):
    if not monitor or inicio_monitor is None:
        return None
    ventana = [m for m in monitor if t0 <= inicio_monitor + int(m['segundo']) <= t1]
    if not ventana:
        return None
    cpu = [float(m['cpu_total_pct']) for m in ventana]
    mem = [float(m['memoria_usada_mb']) for m in ventana]
    return {'cpu_prom': sum(cpu) / len(cpu), 'cpu_max': max(cpu), 'mem_max': max(mem),
            'gunicorn_mem': max(float(m['gunicorn_mem_mb']) for m in ventana),
            'mysqld_mem': max(float(m['mysqld_mem_mb']) for m in ventana)}


def recuperacion(carpeta, etapas):
    """Mide cuánto tarda la mediana en volver a ≤ 100 ms tras el pico de la etapa mayor."""
    if not etapas:
        return 'Sin datos', 'Pendiente'
    mayor = etapas[-1]
    historial = [h for h in csv.DictReader(open(Path(carpeta) / f"c{mayor['usuarios']}_stats_history.csv",
                                                encoding='utf-8')) if h['Name'] == 'Aggregated' and h['50%'] != 'N/A']
    medianas = [(int(h['Timestamp']) - mayor['inicio'], int(float(h['50%']))) for h in historial]
    t_pico, pico = max(medianas, key=lambda x: x[1])
    normal = next(((t, m) for t, m in medianas if t > t_pico and m <= 100), None)
    salud = Path(carpeta) / 'salud.txt'
    salud_txt = (' · ' + salud.read_text(encoding='utf-8').strip().replace('\n', ' · ')) if salud.exists() else ''
    if normal is None:
        return f'Con {mayor["usuarios"]} usuarios la mediana no volvió a ≤ 100 ms durante la etapa.{salud_txt}', 'No cumple'
    texto = (f'Con {mayor["usuarios"]} usuarios la mediana subió a {pico} ms durante el ingreso masivo (s {t_pico}) '
             f'y volvió a {normal[1]} ms en el segundo {normal[0]} ({normal[0] - t_pico} s después), sin errores.'
             f'{salud_txt}')
    return texto, 'Cumple' if normal[0] - t_pico <= 30 else 'Parcial'


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
ROJO = '920000'
FINO = Side(style='thin', color='D9D9D9')
BORDE = Border(left=FINO, right=FINO, top=FINO, bottom=FINO)
COLORES = {'Aprobada': 'E6F4EA', 'Aprobado': 'E6F4EA', 'Cumple': 'E6F4EA', 'Fallida': 'FDE7E9',
           'Error': 'FDE7E9', 'No cumple': 'FDE7E9', 'Pendiente': 'FFF4E5', 'Parcial': 'FFF4E5',
           'Sin ejecutar': 'FFF4E5'}


def hoja_tabla(libro, titulo, subtitulo, encabezados, filas, anchos, columna_estado=None, nota=''):
    h = libro.create_sheet(titulo[:31])
    h['A1'] = titulo
    h['A1'].font = Font(bold=True, size=14, color=ROJO)
    h['A2'] = subtitulo
    h['A2'].font = Font(italic=True, color='5C554E')
    if nota:
        h['A3'] = nota
        h['A3'].alignment = Alignment(wrap_text=True, vertical='top')
        h.merge_cells(start_row=3, start_column=1, end_row=3, end_column=len(encabezados))
        h.row_dimensions[3].height = 48
    fila0 = 4
    for c, e in enumerate(encabezados, 1):
        celda = h.cell(row=fila0, column=c, value=e)
        celda.font = Font(bold=True, color='FFFFFF')
        celda.fill = PatternFill('solid', fgColor=ROJO)
        celda.alignment = Alignment(vertical='center', wrap_text=True)
        celda.border = BORDE
    for r, fila in enumerate(filas, fila0 + 1):
        for c, v in enumerate(fila, 1):
            celda = h.cell(row=r, column=c, value=v)
            celda.alignment = Alignment(vertical='top', wrap_text=True)
            celda.border = BORDE
            if columna_estado and c == columna_estado and v in COLORES:
                celda.fill = PatternFill('solid', fgColor=COLORES[v])
                celda.font = Font(bold=True)
    for c, a in enumerate(anchos, 1):
        h.column_dimensions[get_column_letter(c)].width = a
    h.freeze_panes = h.cell(row=fila0 + 1, column=1)
    if filas:
        h.auto_filter.ref = f'A{fila0}:{get_column_letter(len(encabezados))}{fila0 + len(filas)}'
    return h


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', action='store_true', help='incluir pruebas de interfaz (navegador)')
    parser.add_argument('--estres', default=str(BASE / 'docs/pruebas/estres/local'))
    parser.add_argument('--entorno-estres', default='Local: 2 vCPU, 8 GB RAM, Ubuntu 24.04, '
                        'Gunicorn 5 procesos × 2 hilos, MySQL 8.0 (Locust en la misma máquina)')
    parser.add_argument('--salida', default=str(BASE / 'docs/pruebas/matriz_pruebas_sgr_ev2.xlsx'))
    args = parser.parse_args()

    etiquetas = ['pruebas'] + (['pruebas_ui'] if args.ui else [])
    resultados = ejecutar(etiquetas)
    motor = settings.DATABASES['default']['ENGINE'].rsplit('.', 1)[-1]

    libro = Workbook()
    libro.remove(libro.active)

    # ----- Hoja 1: matriz funcional -----
    filas = []
    for cid, req, mod, pre, pasos, esperado, pruebas, evid, resp in CASOS:
        estados = [resultados.get(p, (None, None, 'Sin ejecutar'))[2] for p in pruebas]
        if all(e == 'Aprobada' for e in estados):
            estado, obtenido = 'Aprobado', 'Conforme a lo esperado. Verificado por las pruebas automatizadas ' + ', '.join(pruebas) + '.'
        elif any(e in ('Fallida', 'Error') for e in estados):
            fallas = [p for p, e in zip(pruebas, estados) if e in ('Fallida', 'Error')]
            estado, obtenido = 'Fallida', 'No conforme en: ' + ', '.join(fallas) + ' (ver hoja «Pruebas automatizadas»).'
        else:
            pend = [p for p, e in zip(pruebas, estados) if e == 'Sin ejecutar']
            estado = 'Parcial'
            obtenido = ('Conforme en las pruebas ejecutadas; pendiente de ejecutar: ' + ', '.join(pend)
                        + ' (pruebas de interfaz: python manage.py test pruebas_ui).')
        evidencia = ' · '.join(filter(None, ['Pruebas: ' + ', '.join(pruebas),
                                             f'Captura: docs/pruebas/evidencias/{evid}' if evid else '']))
        filas.append([cid, req, mod, pre, pasos, esperado, obtenido, estado, evidencia, resp, HOY])
    aprobados = sum(1 for f in filas if f[7] == 'Aprobado')
    hoja_tabla(libro, 'Matriz funcional',
               f'SGR La Serena · EV2 · {len(filas)} casos · {aprobados} aprobados · base de datos de prueba: {motor} · '
               f'generado {datetime.now():%d-%m-%Y %H:%M}',
               ['ID', 'Requisito', 'Módulo', 'Precondiciones', 'Pasos', 'Resultado esperado', 'Resultado obtenido',
                'Estado', 'Evidencia', 'Responsable', 'Fecha'],
               filas, [8, 26, 16, 24, 48, 44, 40, 11, 34, 15, 11], columna_estado=8)

    # ----- Hoja 2: pruebas automatizadas -----
    filas = []
    for cid in sorted(resultados, key=lambda c: (c[:2], c)):
        desc, ruta, estado, detalle, dur = resultados[cid]
        archivo = ruta.split('.')[0] + '/' + ruta.split('.')[1] + '.py'
        filas.append([cid, GRUPOS.get(cid[:2], ''), desc, archivo, ruta.rsplit('.', 1)[-1], estado, dur, detalle])
    ok = sum(1 for f in filas if f[5] == 'Aprobada')
    hoja_tabla(libro, 'Pruebas automatizadas',
               f'{len(filas)} pruebas · {ok} aprobadas · comando: python manage.py test {" ".join(etiquetas)}',
               ['ID', 'Grupo', 'Descripción', 'Archivo', 'Método', 'Resultado', 'Duración (s)', 'Detalle de la falla'],
               filas, [8, 20, 60, 30, 46, 12, 12, 40], columna_estado=6)

    # ----- Hoja 3: umbrales -----
    UMBRALES = [
        ('Tasa de errores', '< 1 % de las solicitudes', 'errores'),
        ('Latencia p95 de páginas (listados, búsqueda, detalle, formularios)', '≤ 800 ms', 'p95_paginas'),
        ('Latencia p95 de inicio de sesión (incluye hash de contraseña)', '≤ 1500 ms', 'p95_login'),
        ('Latencia p95 de exportación a Excel', '≤ 2000 ms', 'p95_excel'),
        ('Latencia promedio global', '≤ 400 ms', 'promedio'),
        ('Uso de CPU sostenido del servidor', '≤ 85 %', 'cpu'),
        ('Recuperación tras la carga', 'Salud 200 y latencia normal antes de 30 s', 'recuperacion'),
    ]
    etapas, monitor = leer_estres(args.estres)
    inicio_monitor = None
    if monitor and etapas:
        # el monitor se inició justo antes de la primera etapa
        if 'epoch' in monitor[0]:
            inicio_monitor = int(float(monitor[0]['epoch'])) - int(monitor[0]['segundo'])
        else:  # versión anterior del monitor: se deduce de la última escritura
            ruta = Path(args.estres) / 'monitor.csv'
            inicio_monitor = int(ruta.stat().st_mtime) - int(monitor[-1]['segundo'])

    def p95(etapa, prefijos):
        valores = [int(f['95%']) for f in etapa['filas'] if f['Name'] != 'Aggregated'
                   and f['Name'][:2] in prefijos and int(f['Request Count'])]
        return max(valores) if valores else None

    filas_estres, eval_umbral = [], {}
    for e in etapas:
        t = e['total']
        n, fallas = int(t['Request Count']), int(t['Failure Count'])
        rec = recursos(monitor, inicio_monitor, e['inicio'], e['fin'])
        pp = p95(e, {'03', '04', '05', '06', '07', '09', '10', '11', '12'})
        pl = p95(e, {'02'})
        px = p95(e, {'08'})
        filas_estres.append([
            'Locust 2.x', args.entorno_estres,
            'Base MySQL con 6 delegaciones, 14 usuarios, 21 sub atenciones y atenciones crecientes',
            'Acceso, inicio, listado/búsqueda/paginación/detalle de atenciones, búsqueda de sub atenciones, '
            'Excel, formulario + lista dependiente + registro de atención',
            e['usuarios'], round((e['fin'] - e['inicio'])), n, round(float(t['Requests/s']), 1),
            round(float(t['Average Response Time'])), int(t['95%']), f'{fallas} ({fallas / n * 100:.2f} %)' if n else '0',
            pp, pl, px,
            f"{rec['cpu_prom']:.0f} % / {rec['cpu_max']:.0f} %" if rec else 'sin datos',
            f"{rec['mem_max']:.0f} MB (Gunicorn {rec['gunicorn_mem']:.0f} MB · MySQL {rec['mysqld_mem']:.0f} MB)" if rec else 'sin datos',
        ])
        eval_umbral.setdefault('errores', []).append((e['usuarios'], fallas / n * 100 if n else 0, 1.0))
        eval_umbral.setdefault('p95_paginas', []).append((e['usuarios'], pp, 800))
        eval_umbral.setdefault('p95_login', []).append((e['usuarios'], pl, 1500))
        eval_umbral.setdefault('p95_excel', []).append((e['usuarios'], px, 2000))
        eval_umbral.setdefault('promedio', []).append((e['usuarios'], float(t['Average Response Time']), 400))
        if rec:
            eval_umbral.setdefault('cpu', []).append((e['usuarios'], rec['cpu_prom'], 85))

    hoja_tabla(libro, 'Estrés',
               'Carga progresiva (10 → 25 → 50 → 100 usuarios). Cada usuario espera 1-3 s entre acciones. '
               'Resultados completos en docs/pruebas/estres/ (carpetas local/ y aws/).',
               ['Herramienta', 'Entorno', 'Volumen de datos', 'Escenarios', 'Usuarios concurrentes', 'Duración (s)',
                'Solicitudes', 'Solicitudes/s', 'Latencia promedio (ms)', 'Latencia p95 (ms)', 'Errores',
                'p95 páginas (ms)', 'p95 acceso (ms)', 'p95 Excel (ms)', 'CPU promedio / máx.', 'Memoria máx.'],
               filas_estres, [12, 30, 26, 40, 12, 10, 11, 11, 12, 11, 12, 11, 11, 11, 14, 30],
               nota=NOTA_ESTRES if etapas else '')


    filas_u = []
    for nombre, umbral, clave in UMBRALES:
        if clave == 'recuperacion':
            texto, estado = recuperacion(args.estres, etapas)
            filas_u.append([nombre, umbral, texto, estado])
            continue
        datos = eval_umbral.get(clave, [])
        if not datos:
            filas_u.append([nombre, umbral, 'Sin datos', 'Pendiente'])
            continue
        texto = ' · '.join(f'{u} usuarios: {v:.1f}' if isinstance(v, float) else f'{u} usuarios: {v}'
                           for u, v, _ in datos)
        cumple = all(v is not None and v <= lim for _, v, lim in datos)
        hasta = [u for u, v, lim in datos if v is not None and v <= lim]
        estado = 'Cumple' if cumple else ('Parcial' if hasta else 'No cumple')
        if estado == 'Parcial':
            texto += f' (cumple hasta {max(hasta)} usuarios)'
        filas_u.append([nombre, umbral, texto, estado])
    hoja_tabla(libro, 'Umbrales', 'Umbrales definidos antes de ejecutar la prueba y su resultado por etapa.',
               ['Indicador', 'Umbral aceptado', 'Resultado medido', 'Evaluación'], filas_u, [52, 28, 70, 12],
               columna_estado=4)

    # ----- Hoja 5: pendientes -----
    PENDIENTES = [
        ('Prueba de estrés en AWS', 'Pendiente',
         'Requiere la instancia publicada. Se ejecuta con bash pruebas_estres/ejecutar.sh http://IP-ELÁSTICA 90 '
         'desde un equipo externo y se agrega a la hoja «Estrés».', CARLOS),
        ('Envío de correo real (SMTP)', 'Simulado',
         'La recuperación se demuestra con la «Bandeja de correos de prueba» para no depender de credenciales SMTP. '
         'Basta configurar SGR_CORREO_BACKEND y SGR_SMTP_* (por ejemplo Amazon SES) para enviar correos reales.', ALEXIS),
        ('HTTPS con certificado', 'Pendiente',
         'Depende de contar con un dominio. La configuración está lista (SGR_HTTPS=1: cookies seguras, redirección y HSTS).',
         CARLOS),
        ('Módulos tablero, actividades, evidencias, validación, agenda, atención social, períodos, metas e informes',
         'Simulado', 'Fuera del alcance de la EV2 (que exige CRUD, acceso y recuperación). Son navegables, con datos '
         'de demostración y sujetos a los permisos reales del rol.', MATIAS),
        ('Logo oficial', 'Pendiente', 'Se muestra automáticamente al copiar el archivo oficial en '
         'static/img/logo-municipalidad.png (no se reproduce sin autorización).', MATIAS),
        ('Pruebas en navegadores distintos de Chromium', 'Pendiente',
         'Las pruebas de interfaz usan Chromium. Firefox y Safari se revisan manualmente en la presentación.', CARLOS),
    ]
    hoja_tabla(libro, 'Pendientes y simulados', 'Lo que no se probó o se simula, y por qué.',
               ['Elemento', 'Estado', 'Justificación', 'Responsable'], [list(p) for p in PENDIENTES],
               [44, 12, 90, 16], columna_estado=2)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    libro.save(args.salida)
    print(f'\nMatriz guardada en {args.salida} · {ok}/{len(resultados)} pruebas aprobadas')


if __name__ == '__main__':
    main()

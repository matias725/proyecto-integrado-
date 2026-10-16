"""
Pruebas de estrés del SGR con Locust.

Simula funcionarios que inician sesión, consultan listados con búsqueda,
abren registros, exportan a Excel y registran atenciones.

Uso (ver ejecutar.sh para la carga progresiva):
    locust -f pruebas_estres/locustfile.py --host http://IP-O-DOMINIO \
           --headless -u 25 -r 5 -t 2m --csv resultados/c25

Variables opcionales:
    SGR_CLAVE_DEMO   contraseña de las cuentas de evaluación (por defecto Serena#2026)
    SGR_ESCRIBIR=0   desactiva el registro de atenciones (solo lectura)
"""

import itertools
import os
import random
import re
import uuid

from locust import HttpUser, between, task

CLAVE = os.environ.get('SGR_CLAVE_DEMO', 'Serena#2026')
ESCRIBIR = os.environ.get('SGR_ESCRIBIR', '1') == '1'

# Cuentas operativas de evaluación (funcionarios y delegados de distintas delegaciones)
CUENTAS = itertools.cycle(['bcastillo', 'cvega', 'jalvarez', 'pcontreras', 'rsilva', 'lgonzalez', 'fortiz',
                           'arojas', 'vcampos', 'mtapia'])
BUSQUEDAS = ['ayuda', 'social', 'beca', 'salud', 'agua', 'registro', 'luminaria', 'AT-2026', '12.', 'orient']
RUTS = ['11.111.111-1', '12.345.678-5', '9.876.543-3', '15.555.555-6', '18.222.333-6', '7.654.321-6']


class Funcionario(HttpUser):
    wait_time = between(1, 3)  # pausa de "lectura" entre acciones

    def on_start(self):
        self.client.get('/', name='01 acceso (formulario)')
        token = self.client.cookies.get('csrftoken')
        usuario = next(CUENTAS)
        with self.client.post('/', {'identificador': usuario, 'clave': CLAVE, 'csrfmiddlewaretoken': token},
                              headers={'Referer': self.host + '/'}, name='02 acceso (enviar)',
                              allow_redirects=False, catch_response=True) as r:
            if r.status_code != 302:
                r.failure(f'Acceso rechazado para {usuario} ({r.status_code})')
        self.tipos = []

    def csrf(self):
        return self.client.cookies.get('csrftoken')

    @task(4)
    def inicio(self):
        self.client.get('/inicio/', name='03 inicio')

    @task(6)
    def listado_atenciones(self):
        self.client.get('/atenciones/', name='04 atenciones · listado')

    @task(5)
    def busqueda_atenciones(self):
        self.client.get('/atenciones/', params={'q': random.choice(BUSQUEDAS)}, name='05 atenciones · búsqueda')

    @task(2)
    def paginar(self):
        self.client.get('/atenciones/', params={'pagina': random.randint(1, 3)}, name='06 atenciones · página')

    @task(2)
    def detalle(self):
        r = self.client.get('/atenciones/', name='04 atenciones · listado')
        enlaces = re.findall(r'href="(/atenciones/\d+/)"', r.text)
        if enlaces:
            self.client.get(random.choice(enlaces), name='07 atenciones · detalle')

    @task(1)
    def exportar(self):
        with self.client.get('/atenciones/exportar/', name='08 atenciones · exportar Excel',
                             catch_response=True) as r:
            if 'spreadsheetml' not in r.headers.get('Content-Type', ''):
                r.failure('La exportación no devolvió un Excel')

    @task(2)
    def catalogos(self):
        # Tipos y sub atenciones visibles para el perfil (algunos perfiles reciben 403 por diseño)
        with self.client.get('/sub-atenciones/', params={'q': random.choice(BUSQUEDAS)},
                             name='09 sub atenciones · búsqueda', catch_response=True) as r:
            if r.status_code == 403:
                r.success()

    @task(2)
    def registrar_atencion(self):
        if not ESCRIBIR:
            return
        formulario = self.client.get('/atenciones/nueva/', name='10 atención · formulario')
        if formulario.status_code != 200:
            return
        if not self.tipos:
            self.tipos = re.findall(r'<option value="(\d+)"', formulario.text.split('id="id_tipo"')[1].split('</select>')[0])
        if not self.tipos:
            return
        tipo = random.choice(self.tipos)
        subs = self.client.get('/api/subatenciones/', params={'tipo': tipo}, name='11 atención · sub atenciones').json()
        if not subs.get('subatenciones'):
            return
        datos = {
            'csrfmiddlewaretoken': self.csrf(), 'token_envio': str(uuid.uuid4()),
            'rut': random.choice(RUTS), 'nombre': 'Vecino de prueba de carga', 'telefono': '',
            'tipo': tipo, 'subatencion': random.choice(subs['subatenciones'])['id'],
            'descripcion': 'Atención registrada por la prueba de estrés del SGR.',
        }
        with self.client.post('/atenciones/nueva/', datos, headers={'Referer': self.host + '/atenciones/nueva/'},
                              name='12 atención · guardar', allow_redirects=False, catch_response=True) as r:
            if r.status_code != 302:
                r.failure(f'No se registró la atención ({r.status_code})')

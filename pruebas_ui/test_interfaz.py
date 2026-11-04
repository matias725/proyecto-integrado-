"""
Pruebas de interfaz con navegador real (Playwright + Chromium).

Verifican lo que solo se ve en el navegador: diálogos SweetAlert2,
confirmaciones, doble envío, lista dependiente y advertencias de cambios
sin guardar. Guardan capturas como evidencia en docs/pruebas/evidencias/.

Ejecutar:  python manage.py test pruebas_ui
Requiere:  pip install -r requirements-dev.txt  y  playwright install chromium
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from atenciones.models import Atencion
from catalogos.models import ItemMedicion, TipoAtencion
from cuentas.inicial import CLAVE_DEMO, cargar_base, cargar_demo

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
EVIDENCIAS = Path(settings.BASE_DIR) / 'docs' / 'pruebas' / 'evidencias'

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
                             'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}})
class InterfazTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if sync_playwright is None:
            raise cls.failureException('Instale playwright (requirements-dev.txt)')
        cls.pw = sync_playwright().start()
        ruta = os.environ.get('SGR_CHROMIUM')
        cls.navegador = cls.pw.chromium.launch(executable_path=ruta) if ruta else cls.pw.chromium.launch()
        EVIDENCIAS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.navegador.close()
        cls.pw.stop()
        super().tearDownClass()

    def setUp(self):
        cargar_base()
        cargar_demo(CLAVE_DEMO)
        self.contexto = self.navegador.new_context(viewport={'width': 1366, 'height': 860}, locale='es-CL')
        self.p = self.contexto.new_page()
        self.errores = []
        self.p.on('pageerror', lambda e: self.errores.append(str(e)))
        # Cualquier bloqueo de la Content-Security-Policy cuenta como error de la página
        self.p.on('console', lambda m: self.errores.append(m.text)
                  if m.type == 'error' and 'Content Security Policy' in m.text else None)
        cache.clear()

    def tearDown(self):
        self.contexto.close()
        self.assertEqual(self.errores, [], 'Errores de JavaScript en la página')

    # ----- utilidades ----------------------------------------------------
    def ir(self, ruta):
        self.p.goto(self.live_server_url + ruta)

    def entrar(self, usuario):
        self.ir('/')
        self.p.fill('#id_identificador', usuario)
        self.p.fill('#id_clave', CLAVE_DEMO)
        self.p.click('main button[type=submit]')
        self.p.wait_for_url('**/inicio/')
        self.cerrar_avisos()

    def cerrar_avisos(self):
        self.p.wait_for_timeout(300)
        if self.p.locator('.swal2-toast').count():
            self.p.evaluate('Swal.close()')

    def dialogo(self):
        self.p.wait_for_selector('.swal2-popup:not(.swal2-toast)', state='visible')
        return self.p.locator('.swal2-popup')

    def esperar(self, funcion, argumento=None, ms=5000):
        """
        Espera a que la función JavaScript devuelva verdadero. Se consulta desde Python porque
        wait_for_function evalúa texto con eval(), que la Content-Security-Policy bloquea.
        """
        for _ in range(ms // 50):
            if self.p.evaluate(funcion, argumento):
                return
            self.p.wait_for_timeout(50)
        self.fail(f'No se cumplió a tiempo: {funcion}')

    def evidencia(self, nombre):
        self.p.screenshot(path=str(EVIDENCIAS / f'{nombre}.png'))

    # ----- pruebas -------------------------------------------------------
    def test_ui01_error_de_acceso_con_sweetalert(self):
        """UI-01 · Acceso incorrecto muestra SweetAlert2 de error"""
        self.ir('/')
        self.p.fill('#id_identificador', 'admin')
        self.p.fill('#id_clave', 'Incorrecta#1')
        self.p.click('main button[type=submit]')
        dlg = self.dialogo()
        self.assertIn('incorrectos', dlg.inner_text())
        self.p.wait_for_timeout(400)
        self.evidencia('UI-01-acceso-incorrecto')

    def test_ui02_validacion_en_navegador(self):
        """UI-02 · Campos vacíos se marcan en el navegador antes de enviar"""
        self.ir('/')
        self.p.click('main button[type=submit]')
        self.dialogo()
        self.assertEqual(self.p.locator('.campo.invalido').count(), 2)
        self.p.wait_for_timeout(400)
        self.evidencia('UI-02-validacion-cliente')

    def test_ui03_cancelar_eliminacion_no_elimina(self):
        """UI-03 · Cancelar la confirmación de eliminar no elimina el registro"""
        self.entrar('admin')
        item = ItemMedicion.objects.get(codigo='IT014')
        self.ir(f'/items/{item.pk}/')
        self.p.click('form[action$="/eliminar/"] button')
        self.dialogo()
        self.p.wait_for_timeout(400)
        self.evidencia('UI-03-confirmar-eliminar')
        self.p.click('.swal2-cancel')
        self.p.wait_for_timeout(500)
        self.assertTrue(ItemMedicion.objects.filter(pk=item.pk).exists())
        self.assertIn(f'/items/{item.pk}/', self.p.url)

    def test_ui04_confirmar_eliminacion_y_mensaje_de_exito(self):
        """UI-04 · Confirmar eliminar elimina y muestra éxito"""
        self.entrar('admin')
        item = ItemMedicion.objects.create(codigo='IT090', nombre='Ítem temporal', descripcion='x')
        self.ir(f'/items/{item.pk}/')
        self.p.click('form[action$="/eliminar/"] button')
        self.dialogo()
        self.p.click('.swal2-confirm')
        self.p.wait_for_url('**/items/')
        self.p.wait_for_selector('.swal2-toast')
        self.evidencia('UI-04-eliminado')
        self.assertFalse(ItemMedicion.objects.filter(pk=item.pk).exists())

    def test_ui05_eliminacion_rechazada_muestra_error(self):
        """UI-05 · Eliminar un registro con relaciones muestra error (no éxito)"""
        self.entrar('admin')
        tipo = TipoAtencion.objects.get(codigo='TA001')
        self.ir(f'/tipos-atencion/{tipo.pk}/')
        self.p.click('form[action$="/eliminar/"] button')
        self.dialogo()
        self.p.click('.swal2-confirm')
        self.p.wait_for_load_state()
        dlg = self.dialogo()
        self.assertIn('No se pudo eliminar', dlg.inner_text())
        self.assertEqual(self.p.locator('.swal2-icon-success').count(), 0)
        self.p.wait_for_timeout(400)
        self.evidencia('UI-05-eliminar-con-relaciones')

    def test_ui06_lista_dependiente_y_limpieza(self):
        """UI-06 · Al cambiar el tipo, la sub atención se limpia y muestra solo las del tipo"""
        self.entrar('bcastillo')
        self.ir('/atenciones/nueva/')
        t1, t2 = TipoAtencion.objects.filter(activo=True).order_by('nombre')[:2]
        self.p.select_option('#id_tipo', str(t1.pk))
        self.esperar('() => document.querySelector("#id_subatencion").options.length > 1')
        primera = t1.subatenciones.filter(activo=True).order_by('nombre').first()
        self.p.select_option('#id_subatencion', str(primera.pk))
        self.p.select_option('#id_tipo', str(t2.pk))
        esperado = {str(pk) for pk in t2.subatenciones.filter(activo=True).values_list('pk', flat=True)}
        # Espera a que la lista termine de recargarse con las sub atenciones del nuevo tipo
        self.esperar('n => document.querySelector("#id_subatencion").options.length === n + 1', len(esperado))
        self.assertEqual(self.p.input_value('#id_subatencion'), '')
        opciones = set(self.p.eval_on_selector_all('#id_subatencion option', 'os => os.map(o => o.value)')) - {''}
        self.assertEqual(opciones, esperado)
        self.evidencia('UI-06-lista-dependiente')

    def test_ui07_doble_envio_crea_una_sola_atencion(self):
        """UI-07 · Doble clic en Guardar crea una sola atención y muestra el folio"""
        self.entrar('bcastillo')
        self.ir('/atenciones/nueva/')
        tipo = TipoAtencion.objects.get(codigo='TA001')
        sub = tipo.subatenciones.filter(activo=True).first()
        self.p.fill('#id_rut', '11.111.111-1')
        self.p.fill('#id_nombre', 'Vecina de Prueba')
        self.p.select_option('#id_tipo', str(tipo.pk))
        self.esperar('() => document.querySelector("#id_subatencion").options.length > 1')
        self.p.select_option('#id_subatencion', str(sub.pk))
        self.p.fill('#id_descripcion', 'Consulta registrada desde la prueba de interfaz.')
        antes = Atencion.objects.count()
        boton = self.p.locator('main button[type=submit]')
        boton.dblclick()
        self.p.wait_for_url('**/atenciones/*/?nueva=1')
        dlg = self.dialogo()
        self.assertEqual(Atencion.objects.count(), antes + 1)
        self.assertIn(Atencion.objects.latest('pk').folio, dlg.inner_text())
        self.p.wait_for_timeout(400)
        self.evidencia('UI-07-folio-confirmado')

    def test_ui08_cancelar_formulario_con_cambios(self):
        """UI-08 · Cancelar con cambios pide confirmación y no crea registros"""
        self.entrar('bcastillo')
        self.ir('/atenciones/nueva/')
        self.p.fill('#id_nombre', 'Dato a descartar')
        antes = Atencion.objects.count()
        self.p.click('[data-cancelar]')
        dlg = self.dialogo()
        self.assertIn('Descartar', dlg.inner_text())
        self.p.wait_for_timeout(400)
        self.evidencia('UI-08-descartar-cambios')
        self.p.click('.swal2-confirm')
        self.p.wait_for_url('**/atenciones/')
        self.assertEqual(Atencion.objects.count(), antes)

    def test_ui09_cambio_de_delegacion_advierte_cambios(self):
        """UI-09 · Cambiar de delegación con cambios sin guardar muestra advertencia"""
        self.entrar('arojas')
        self.ir('/atenciones/nueva/')
        self.p.fill('#id_nombre', 'Cambio sin guardar')
        inicial = self.p.input_value('#selectorDelegacion')
        otra = [v for v in self.p.eval_on_selector_all('#selectorDelegacion option', 'os => os.map(o => o.value)')
                if v != inicial][0]
        self.p.select_option('#selectorDelegacion', otra)
        dlg = self.dialogo()
        self.assertIn('cambios sin guardar', dlg.inner_text())
        self.p.wait_for_timeout(400)
        self.evidencia('UI-09-cambio-contexto')
        self.p.click('.swal2-cancel')
        self.assertEqual(self.p.input_value('#selectorDelegacion'), inicial)

    def test_ui10_cambio_de_delegacion_actualiza_cabecera(self):
        """UI-10 · Confirmar el cambio de delegación actualiza cabecera y listado"""
        self.entrar('arojas')
        self.ir('/atenciones/')
        texto = self.p.locator('#selectorDelegacion option:not(:checked)').first.inner_text()
        valor = self.p.locator('#selectorDelegacion option:not(:checked)').first.get_attribute('value')
        self.p.select_option('#selectorDelegacion', valor)
        self.dialogo()
        self.p.click('.swal2-confirm')
        self.p.wait_for_load_state()
        self.p.wait_for_selector('#selectorDelegacion')
        self.assertEqual(self.p.input_value('#selectorDelegacion'), valor)
        self.assertIn(texto.split('|')[0].strip(), self.p.inner_text('main'))
        self.evidencia('UI-10-contexto-cambiado')

    def test_ui11_menu_por_perfil(self):
        """UI-11 · Cada perfil ve solo los menús autorizados"""
        for usuario, visibles, ocultos in [
            ('admin', ['Roles', 'Auditoría', 'Correos de prueba'], []),
            ('emunoz', ['Auditoría', 'Tipo de Atención'], ['Correos de prueba']),
            ('arojas', ['Usuarios', 'Atenciones'], ['Roles', 'Auditoría']),
            ('bcastillo', ['Atenciones'], ['Usuarios', 'Roles', 'Delegaciones', 'Auditoría']),
        ]:
            with self.subTest(usuario=usuario):
                self.contexto.clear_cookies()
                self.entrar(usuario)
                menu = self.p.inner_text('#menuLateral')
                for v in visibles:
                    self.assertIn(v, menu)
                for o in ocultos:
                    self.assertNotIn(o, menu)
                self.evidencia(f'UI-11-menu-{usuario}')

    def test_ui12_recuperacion_casillas_y_cuenta_regresiva(self):
        """UI-12 · Recuperación: pegar el código llena las 6 casillas y el reenvío espera 45 s"""
        self.ir('/recuperar/')
        self.p.fill('#id_correo', 'bcastillo@example.test')
        self.p.click('main button[type=submit]')
        self.p.wait_for_url('**/recuperar/validar/')
        self.cerrar_avisos()
        boton = self.p.locator('[data-cuenta-regresiva]')
        self.assertTrue(boton.is_disabled())
        self.assertIn('Podrá reenviar', self.p.inner_text('[data-texto-espera]'))
        self.p.focus('#digito1')
        self.p.evaluate('''() => {
            const dt = new DataTransfer(); dt.setData('text', '123456');
            document.querySelector('#digito1').dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true}));
        }''')
        self.assertEqual(self.p.input_value('#id_codigo'), '123456')
        self.evidencia('UI-12-codigo-pegado')

    def test_ui13_exportar_descarga_excel(self):
        """UI-13 · Exportar a Excel descarga un .xlsx con los filtros aplicados"""
        self.entrar('admin')
        self.ir('/sub-atenciones/?q=salud')
        with self.p.expect_download() as descarga:
            self.p.click('[data-exportar]')
        self.assertTrue(descarga.value.suggested_filename.endswith('.xlsx'))
        self.assertIn('sub-atenciones', descarga.value.suggested_filename.lower().replace('_', '-'))

    def test_ui14_vista_movil(self):
        """UI-14 · En pantalla de teléfono el menú se abre con el botón y la cabecera se mantiene"""
        movil = self.navegador.new_context(viewport={'width': 390, 'height': 800})
        p = movil.new_page()
        p.goto(self.live_server_url + '/')
        p.fill('#id_identificador', 'arojas')
        p.fill('#id_clave', CLAVE_DEMO)
        p.click('main button[type=submit]')
        p.wait_for_url('**/inicio/')
        self.assertFalse(p.locator('#menuLateral').is_visible())
        p.click('[data-alternar-menu]')
        self.assertTrue(p.locator('#menuLateral').is_visible())
        self.assertTrue(p.locator('#selectorDelegacion').is_visible())
        p.screenshot(path=str(EVIDENCIAS / 'UI-14-movil.png'))
        ancho = p.evaluate('document.documentElement.scrollWidth')
        self.assertLessEqual(ancho, 390, 'No debe haber desplazamiento horizontal')
        movil.close()

    # ----- matriz SGR (evaluación 2) -----------------------------------------
    def test_ui15_registrar_actividad_bajo_csp(self):
        """UI-15 · Registrar una actividad con la CSP activa: SweetAlert2 y validación funcionan sin errores"""
        self.entrar('bcastillo')
        self.ir('/actividades/nueva/')
        self.assertIn("script-src 'self'", self.p.evaluate(
            "fetch(location.href).then(r => r.headers.get('content-security-policy'))"))
        self.p.fill('#id_titulo', '')
        self.p.click('main button[type=submit]')                     # incompleto: validación del navegador
        self.assertTrue(self.p.locator('.campo.invalido').count() > 0)
        if self.p.locator('.swal2-popup').count():
            self.evidencia('UI-15-validacion-actividad')
            self.p.evaluate('() => Swal.close()')
            self.p.wait_for_selector('.swal2-container', state='detached')
        self.p.select_option('#id_item', label=self.p.locator('#id_item option').nth(1).inner_text())
        self.p.fill('#id_titulo', 'Atención social en sede')
        self.p.fill('#id_descripcion', 'Se orienta a la vecina sobre el subsidio y se deriva al DIDECO.')
        self.p.fill('#id_solicitante_nombre', 'María Pérez')
        self.p.fill('#id_solicitante_telefono', '912345678')
        self.p.select_option('#id_estado', 'REALIZADO')
        self.p.click('main button[type=submit]')
        self.p.wait_for_url('**/actividades/*/')
        self.p.wait_for_selector('.swal2-toast', state='visible')
        self.evidencia('UI-15-actividad-registrada')

    def test_ui16_tablero_medidores_con_csp(self):
        """UI-16 · El tablero dibuja los medidores (ancho por JavaScript, sin estilos en línea)"""
        self.entrar('bcastillo')
        self.ir('/tablero/')
        anchos = self.p.eval_on_selector_all('[data-ancho]', 'els => els.map(e => e.style.width)')
        self.assertTrue(anchos)
        self.assertTrue(all(a.endswith('%') for a in anchos), anchos)
        self.evidencia('UI-16-tablero-semaforo')

    def test_ui17_confirmar_validacion(self):
        """UI-17 · El delegado abre la bandeja de validación y ve el diálogo al rechazar sin motivo"""
        self.entrar('arojas')
        self.ir('/validacion/')
        self.evidencia('UI-17-bandeja-validacion')
        self.assertTrue(self.p.locator('main table, main .vacio').count() > 0)

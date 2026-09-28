"""
Pruebas del SGR.  Ejecutar con:  python manage.py test

No usan base de datos (SimpleTestCase): cada prueba parte de los datos
ficticios iniciales gracias a datos.reiniciar().
"""

import io
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse

from . import calculos, datos
from .validadores import digito_verificador, formatear_rut


class BaseSGR(SimpleTestCase):
    def setUp(self):
        datos.reiniciar()

    def entrar(self, cuenta):
        respuesta = self.client.post(reverse('acceso'), {'usuario': cuenta, 'clave': datos.CLAVE_DEMO})
        self.assertRedirects(respuesta, reverse('tablero'), fetch_redirect_response=False)


# ---------------------------------------------------------------------------
# Reglas de cálculo
# ---------------------------------------------------------------------------
class CalculosTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.periodo = calculos.periodo_abierto()

    def test_rn004_cumplimiento(self):
        self.assertAlmostEqual(calculos.cumplimiento(18, 60), 30.0)

    def test_rn002_meta_cero_no_divide(self):
        self.assertEqual(calculos.cumplimiento(10, 0), 0)

    def test_rn005_aplica_tope(self):
        self.assertEqual(calculos.ponderado(200, 30, 150), 45)

    def test_rn007_meta_esperada_coincide_con_script_sql(self):
        # 74 de 91 días al 12-09-2026
        self.assertEqual(calculos.dias_transcurridos(self.periodo), 74)
        self.assertAlmostEqual(calculos.meta_esperada_al_dia(self.periodo), 81.32, places=2)

    def test_rn007_periodo_terminado_espera_cien(self):
        cerrado = datos.buscar('periodos', id=2)
        self.assertEqual(calculos.meta_esperada_al_dia(cerrado), 100)

    def test_rn008_semaforo(self):
        self.assertEqual(calculos.semaforo(85, 81.32, self.periodo), 'verde')
        self.assertEqual(calculos.semaforo(60, 81.32, self.periodo), 'ambar')
        self.assertEqual(calculos.semaforo(30, 81.32, self.periodo), 'rojo')


class RutTests(SimpleTestCase):
    def test_digito_verificador(self):
        self.assertEqual(digito_verificador('12345678'), '5')
        self.assertEqual(digito_verificador('99999999'), '9')

    def test_formato(self):
        self.assertEqual(formatear_rut('123456785'), '12.345.678-5')


# ---------------------------------------------------------------------------
# Acceso y permisos
# ---------------------------------------------------------------------------
class AccesoTests(BaseSGR):
    def test_credenciales_incorrectas_con_mensaje_generico(self):
        respuesta = self.client.post(reverse('acceso'), {'usuario': 'bcastillo', 'clave': 'otra'})
        self.assertContains(respuesta, 'Usuario o contraseña incorrectos')

    def test_sin_sesion_redirige_al_acceso(self):
        self.assertRedirects(self.client.get(reverse('tablero')), reverse('acceso'))

    def test_administrador_abre_todas_las_pantallas(self):
        self.entrar('faguirre')
        for nombre in ['tablero', 'actividades', 'actividad_nueva', 'evidencias', 'validacion', 'agenda',
                       'atencion_social', 'delegaciones', 'usuarios', 'periodos', 'metas', 'informes',
                       'auditoria']:
            with self.subTest(pantalla=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_cada_rol_abre_su_menu(self):
        for cuenta in ['bcastillo', 'arojas', 'emunoz']:
            self.client.cookies.clear()
            self.entrar(cuenta)
            respuesta = self.client.get(reverse('tablero'))
            for grupo in respuesta.context['menu']:
                for enlace in grupo['enlaces']:
                    with self.subTest(cuenta=cuenta, pantalla=enlace['url']):
                        self.assertEqual(self.client.get(reverse(enlace['url'])).status_code, 200)

    def test_funcionario_no_entra_a_configuracion_y_queda_auditado(self):
        self.entrar('bcastillo')
        respuesta = self.client.get(reverse('delegaciones'))
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(datos.almacen['auditoria'][0]['evento'], 'ACCESO_DENEGADO')

    def test_menu_del_funcionario_oculta_configuracion(self):
        self.entrar('bcastillo')
        respuesta = self.client.get(reverse('tablero'))
        secciones = {e['id'] for g in respuesta.context['menu'] for e in g['enlaces']}
        self.assertNotIn('usuarios', secciones)
        self.assertIn('actividades', secciones)

    def test_funcionario_solo_ve_su_delegacion(self):
        self.entrar('bcastillo')
        respuesta = self.client.get(reverse('actividades'))
        delegaciones = {a['delegacion'] for a in respuesta.context['filas']}
        self.assertEqual(delegaciones, {'Rural'})


# ---------------------------------------------------------------------------
# Formularios
# ---------------------------------------------------------------------------
class ActividadTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.entrar('bcastillo')
        self.validos = {
            'fecha': '2026-09-10', 'item': 'Atenciones en terreno', 'tipo': 'Visita a terreno',
            'descripcion': 'Catastro de necesidades del sector', 'accion': 'Se levanta catastro y se deriva',
        }

    def test_vacia_muestra_errores(self):
        respuesta = self.client.post(reverse('actividad_nueva'), {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].errors)

    def test_fecha_fuera_del_periodo(self):
        respuesta = self.client.post(reverse('actividad_nueva'), {**self.validos, 'fecha': '2026-05-01'})
        self.assertIn('fecha', respuesta.context['form'].errors)

    def test_fecha_futura(self):
        respuesta = self.client.post(reverse('actividad_nueva'), {**self.validos, 'fecha': '2026-09-20'})
        self.assertIn('fecha', respuesta.context['form'].errors)

    def test_valida_genera_codigo_correlativo(self):
        respuesta = self.client.post(reverse('actividad_nueva'), self.validos)
        nueva = datos.almacen['actividades'][-1]
        self.assertRedirects(respuesta, reverse('actividad_registrada', args=[nueva['id']]))
        self.assertEqual(nueva['codigo'], 'EV-2026-000009')
        self.assertEqual(nueva['estado'], 'REGISTRADA')


class EvidenciaTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.entrar('bcastillo')

    def enviar(self, nombre, contenido, tipo):
        archivo = SimpleUploadedFile(nombre, contenido, content_type=tipo)
        return self.client.post(reverse('evidencias'), {'actividad': 'EV-2026-000002', 'archivo': archivo})

    def test_acepta_png_real(self):
        respuesta = self.enviar('foto.png', b'\x89PNG\r\n\x1a\n' + b'0' * 100, 'image/png')
        self.assertRedirects(respuesta, reverse('evidencias'))
        self.assertEqual(datos.buscar('actividades', codigo='EV-2026-000002')['evidencia'], 'PENDIENTE')

    def test_rechaza_formato(self):
        respuesta = self.enviar('notas.txt', b'hola', 'text/plain')
        self.assertIn('archivo', respuesta.context['form'].errors)

    def test_rechaza_archivo_disfrazado(self):
        respuesta = self.enviar('foto.jpg', b'MZ ejecutable renombrado', 'image/jpeg')
        self.assertIn('no corresponde', str(respuesta.context['form'].errors['archivo']))

    def test_no_ofrece_actividad_ajena(self):
        archivo = SimpleUploadedFile('f.png', b'\x89PNG' + b'0' * 20, content_type='image/png')
        respuesta = self.client.post(reverse('evidencias'), {'actividad': 'EV-2026-000004', 'archivo': archivo})
        self.assertIn('actividad', respuesta.context['form'].errors)


class ValidacionTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.entrar('arojas')

    def test_aprobar_suma_avance(self):
        antes = datos.buscar('metas', id=1)['avance']
        self.client.post(reverse('validacion'), {'codigo': 'EV-2026-000006', 'resultado': 'APROBADA'})
        self.assertEqual(datos.buscar('metas', id=1)['avance'], antes + 1)
        self.assertEqual(datos.buscar('actividades', codigo='EV-2026-000006')['estado'], 'VALIDADA')

    def test_rechazo_exige_observacion(self):
        respuesta = self.client.post(reverse('validacion'), {'codigo': 'EV-2026-000006', 'resultado': 'RECHAZADA'})
        self.assertIn('observacion', respuesta.context['form'].errors)

    def test_no_permite_autovalidacion(self):
        respuesta = self.client.post(reverse('validacion'), {'codigo': 'EV-2026-000008', 'resultado': 'APROBADA'})
        self.assertContains(respuesta, 'No puede validar una evidencia registrada por usted')
        self.assertEqual(datos.buscar('actividades', codigo='EV-2026-000008')['evidencia'], 'PENDIENTE')


class AgendaTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.entrar('bcastillo')

    def test_transicion_permitida_guarda_historial(self):
        self.client.post(reverse('compromiso_estado', args=[1]),
                         {'estado': 'REALIZADO', 'observacion': 'Luminarias repuestas'})
        compromiso = datos.buscar('compromisos', id=1)
        self.assertEqual(compromiso['estado'], 'REALIZADO')
        self.assertEqual(compromiso['historial'][-1]['anterior'], 'EN_PROCESO')

    def test_transicion_no_permitida(self):
        respuesta = self.client.post(reverse('compromiso_estado', args=[1]),
                                     {'estado': 'INGRESADO', 'observacion': 'Volver atrás'})
        self.assertIn('estado', respuesta.context['form'].errors)


class AtencionSocialTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.entrar('bcastillo')
        self.base = {'nombre': 'Persona de prueba', 'tipo': 'Atención de público',
                     'fecha': '2026-09-10', 'resultado': 'Solicitud de orientación'}

    def test_cuarta_gestion_rechazada(self):
        respuesta = self.client.post(reverse('atencion_social'), {**self.base, 'rut': '99.999.999-9'})
        self.assertIn('tres gestiones', str(respuesta.context['form'].errors['rut']))

    def test_rut_invalido(self):
        respuesta = self.client.post(reverse('atencion_social'), {**self.base, 'rut': '12.345.678-9'})
        self.assertIn('rut', respuesta.context['form'].errors)

    def test_segunda_gestion_en_caso_existente(self):
        self.client.post(reverse('atencion_social'), {**self.base, 'rut': '88888888-8'})
        self.assertEqual(len(datos.buscar('casos_sociales', id=2)['gestiones']), 2)


class ConfiguracionTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.entrar('faguirre')

    def test_delegacion_duplicada(self):
        respuesta = self.client.post(reverse('delegaciones'),
                                     {'nombre': 'centro', 'ambito': 'Ámbito de prueba', 'correo': 'a@b.cl'})
        self.assertIn('nombre', respuesta.context['form'].errors)

    def test_no_desactiva_delegacion_con_funcionarios(self):
        self.client.post(reverse('delegacion_estado', args=[1]))
        self.assertEqual(datos.buscar('delegaciones', id=1)['estado'], 'ACTIVA')

    def test_usuario_duplicado_y_sin_rol(self):
        respuesta = self.client.post(reverse('usuarios'), {
            'rut': '11.111.111-1', 'nombre': 'Nombre De Prueba', 'correo': 'ana.rojas@demo.cl',
            'cargo': 'Gestor Social', 'delegacion': 'Rural'})
        errores = respuesta.context['form'].errors
        self.assertIn('rut', errores)
        self.assertIn('correo', errores)
        self.assertIn('roles', errores)

    def test_periodo_termino_anterior(self):
        respuesta = self.client.post(reverse('periodos'), {
            'nombre': 'Trimestre 2026-Q4', 'inicio': '2026-10-01', 'termino': '2026-09-01',
            'umbral_verde': 100, 'umbral_ambar': 60, 'tope': 150})
        self.assertIn('termino', respuesta.context['form'].errors)

    def test_coordinador_no_reabre_periodo(self):
        self.client.cookies.clear()
        self.entrar('emunoz')
        self.client.post(reverse('periodo_estado', args=[2, 'reabrir']))
        self.assertEqual(datos.buscar('periodos', id=2)['estado'], 'CERRADO')


class MetasTests(BaseSGR):
    def setUp(self):
        super().setUp()
        self.entrar('emunoz')

    def formset(self, filas):
        cuerpo = {'cargo': 'Gestor Social', 'metas-TOTAL_FORMS': len(filas), 'metas-INITIAL_FORMS': 4,
                  'metas-MIN_NUM_FORMS': 0, 'metas-MAX_NUM_FORMS': 1000}
        for i, (item, objetivo, ponderador) in enumerate(filas):
            cuerpo.update({f'metas-{i}-item': item, f'metas-{i}-objetivo': objetivo,
                           f'metas-{i}-ponderador': ponderador})
        return self.client.post(reverse('metas'), cuerpo)

    def test_suma_distinta_de_cien(self):
        respuesta = self.formset([('Atenciones en terreno', 60, 50), ('Casos sociales gestionados', 40, 30)])
        self.assertIn('Faltan 20,0 puntos', str(respuesta.context['formset'].non_form_errors()))

    def test_meta_cero(self):
        respuesta = self.formset([('Atenciones en terreno', 0, 100)])
        self.assertIn('objetivo', respuesta.context['formset'].forms[0].errors)

    def test_guarda_nueva_version_y_conserva_avance(self):
        self.formset([('Atenciones en terreno', 70, 40), ('Casos sociales gestionados', 40, 60)])
        meta = datos.buscar('metas', cargo='Gestor Social', periodo=1, item='Atenciones en terreno')
        self.assertEqual((meta['objetivo'], meta['ponderador'], meta['avance'], meta['version']), (70, 40, 18, 3))


class InformesTests(BaseSGR):
    def test_exporta_csv(self):
        self.entrar('emunoz')
        respuesta = self.client.get(reverse('informes') + '?exportar=csv')
        self.assertEqual(respuesta['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('Cumplimiento por delegación', respuesta.content.decode('utf-8'))

    def test_rango_invertido(self):
        self.entrar('emunoz')
        respuesta = self.client.get(reverse('informes'),
                                    {'tipo': 'delegacion', 'desde': '2026-09-10', 'hasta': '2026-09-01'})
        self.assertIn('hasta', respuesta.context['form'].errors)

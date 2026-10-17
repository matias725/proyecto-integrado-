"""Pruebas de recuperación de contraseña en tres pasos."""

from datetime import timedelta

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from cuentas.models import CodigoRecuperacion

from .base import PruebaSGR

NUEVA = 'Coquimbo#2027'


class RecuperacionTests(PruebaSGR):

    def solicitar(self, correo='bcastillo@example.test'):
        return self.client.post(reverse('recuperar'), {'correo': correo})

    def validar(self, codigo):
        return self.client.post(reverse('recuperar_validar'), {'codigo': codigo})

    def permitir_reenvio(self):
        """Simula que ya pasaron los 45 s de espera."""
        CodigoRecuperacion.objects.update(creado=timezone.now() - timedelta(seconds=60))
        sesion = self.client.session
        datos = sesion['recuperacion']
        datos['emitido'] -= 60
        sesion['recuperacion'] = datos
        sesion.save()

    # ----- paso 1 --------------------------------------------------------
    def test_solicitud_envia_codigo(self):
        """PR-01 · Solicitar código con correo registrado envía un código de 6 dígitos"""
        r = self.solicitar()
        self.assertRedirects(r, reverse('recuperar_validar'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['bcastillo@example.test'])
        self.assertRegex(self.ultimo_codigo(), r'^\d{6}$')
        cod = CodigoRecuperacion.objects.get()
        self.assertNotEqual(cod.codigo_hash, self.ultimo_codigo(), 'El código debe guardarse con hash')

    def test_correo_inexistente_respuesta_identica(self):
        """PR-02 · Correo no registrado: misma respuesta, sin enviar correo (no revela cuentas)"""
        r1 = self.client.post(reverse('recuperar'), {'correo': 'nadie@example.test'}, follow=True)
        self.assertEqual(len(mail.outbox), 0)
        self.client.session.flush()
        r2 = self.client.post(reverse('recuperar'), {'correo': 'cvega@example.test'}, follow=True)
        self.assertEqual(self.mensajes(r1), self.mensajes(r2))
        self.assertEqual(r1.redirect_chain[-1][0], r2.redirect_chain[-1][0])

    def test_correo_invalido(self):
        """PR-03 · Correo con formato inválido es rechazado en el servidor"""
        r = self.client.post(reverse('recuperar'), {'correo': 'no-es-correo'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertEqual(len(mail.outbox), 0)

    def test_cuenta_inactiva_no_recibe_codigo(self):
        """PR-04 · Una cuenta inactiva no recibe código (respuesta genérica)"""
        r = self.solicitar('dfuentes@example.test')
        self.assertRedirects(r, reverse('recuperar_validar'))
        self.assertEqual(len(mail.outbox), 0)

    # ----- paso 2 --------------------------------------------------------
    def test_flujo_completo_y_clave_antigua_deja_de_funcionar(self):
        """PR-05 · Flujo completo: código válido, nueva contraseña funciona y la antigua no"""
        self.solicitar()
        r = self.validar(self.ultimo_codigo())
        self.assertRedirects(r, reverse('recuperar_nueva'))
        r = self.client.post(reverse('recuperar_nueva'), {'clave': NUEVA, 'confirmacion': NUEVA})
        self.assertRedirects(r, reverse('acceso'))
        r = self.client.post(reverse('acceso'), {'identificador': 'bcastillo', 'clave': self.clave})
        self.assertMensaje(r, 'incorrectos')
        self.entrar('bcastillo', NUEVA)

    def test_codigo_incorrecto_descuenta_intentos(self):
        """PR-06 · Código incorrecto informa intentos restantes"""
        self.solicitar()
        correcto = self.ultimo_codigo()
        malo = '000000' if correcto != '000000' else '111111'
        r = self.validar(malo)
        self.assertMensaje(r, 'Le quedan 4 intento')
        self.assertEqual(CodigoRecuperacion.objects.get().intentos, 1)

    @override_settings(SGR_CODIGO_MAX_INTENTOS=3)
    def test_limite_de_intentos(self):
        """PR-07 · Superado el límite de intentos, ni el código correcto sirve"""
        self.solicitar()
        correcto = self.ultimo_codigo()
        malo = '000000' if correcto != '000000' else '111111'
        for _ in range(3):
            self.validar(malo)
        r = self.validar(correcto)
        self.assertMensaje(r, 'Superó el número de intentos')
        self.assertEqual(r.status_code, 200)

    def test_codigo_vencido(self):
        """PR-08 · Código vencido (más de 10 minutos) es rechazado"""
        self.solicitar()
        codigo = self.ultimo_codigo()
        CodigoRecuperacion.objects.update(expira=timezone.now() - timedelta(seconds=1))
        r = self.validar(codigo)
        self.assertMensaje(r, 'venció')

    def test_vigencia_es_de_diez_minutos(self):
        """PR-09 · El código vence 10 minutos después de emitido"""
        self.solicitar()
        cod = CodigoRecuperacion.objects.get()
        self.assertAlmostEqual((cod.expira - cod.creado).total_seconds(), 600, delta=2)

    def test_codigo_reutilizado(self):
        """PR-10 · Un código ya usado no puede reutilizarse"""
        self.solicitar()
        codigo = self.ultimo_codigo()
        self.validar(codigo)
        self.client.post(reverse('recuperar_nueva'), {'clave': NUEVA, 'confirmacion': NUEVA})
        # Nueva solicitud de sesión con el mismo código antiguo
        sesion = self.client.session
        sesion['recuperacion'] = {'correo': 'b***@example.test', 'codigo_id': CodigoRecuperacion.objects.get().pk,
                                  'emitido': 0, 'intentos': 0, 'verificado': False}
        sesion.save()
        r = self.validar(codigo)
        self.assertMensaje(r, 'ya fue utilizado')

    def test_codigo_formato_invalido(self):
        """PR-11 · El código debe tener exactamente 6 dígitos"""
        self.solicitar()
        for valor in ['12345', '1234567', 'abcdef', '']:
            with self.subTest(valor=valor):
                r = self.validar(valor)
                self.assertMensaje(r, '6 dígitos')

    def test_reenvio_respeta_espera_de_45_segundos(self):
        """PR-12 · No se puede reenviar antes de 45 segundos"""
        self.solicitar()
        r = self.client.post(reverse('recuperar_reenviar'), follow=True)
        self.assertMensaje(r, 'Podrá solicitar un nuevo código')
        self.assertEqual(len(mail.outbox), 1)

    def test_reenvio_anula_codigo_anterior(self):
        """PR-13 · Reenviar emite un código nuevo y anula el anterior"""
        self.solicitar()
        anterior = self.ultimo_codigo()
        self.permitir_reenvio()
        self.client.post(reverse('recuperar_reenviar'))
        self.assertEqual(len(mail.outbox), 2)
        nuevo = self.ultimo_codigo()
        self.assertEqual(CodigoRecuperacion.objects.filter(anulado=True).count(), 1)
        if anterior != nuevo:
            r = self.validar(anterior)
            self.assertEqual(r.status_code, 200, 'El código anterior ya no debe servir')
            self.assertMensaje(r, 'incorrecto')
        r = self.validar(nuevo)
        self.assertRedirects(r, reverse('recuperar_nueva'))

    @override_settings(SGR_CODIGO_MAX_POR_HORA=2)
    def test_limite_de_codigos_por_hora(self):
        """PR-14 · Límite de códigos por hora"""
        self.solicitar()
        self.permitir_reenvio()
        self.client.post(reverse('recuperar_reenviar'))
        self.permitir_reenvio()
        r = self.client.post(reverse('recuperar_reenviar'), follow=True)
        self.assertMensaje(r, 'máximo de códigos por hora')
        self.assertEqual(len(mail.outbox), 2)

    def test_validar_sin_solicitud_previa(self):
        """PR-15 · No se puede saltar al paso 2 o 3 sin solicitar un código"""
        self.assertRedirects(self.client.get(reverse('recuperar_validar')), reverse('recuperar'))
        self.assertRedirects(self.client.get(reverse('recuperar_nueva')), reverse('recuperar'))

    def test_paso3_exige_codigo_verificado(self):
        """PR-16 · El paso 3 exige haber verificado el código"""
        self.solicitar()
        r = self.client.get(reverse('recuperar_nueva'))
        self.assertRedirects(r, reverse('recuperar_validar'))

    # ----- paso 3 --------------------------------------------------------
    def test_requisitos_de_contrasena(self):
        """PR-17 · La nueva contraseña debe cumplir los requisitos"""
        self.solicitar()
        self.validar(self.ultimo_codigo())
        for clave in ['Cor#1a', 'sinmayuscula#1', 'SINMINUSCULA#1', 'SinNumero#', 'SinEspecial1']:
            with self.subTest(clave=clave):
                r = self.client.post(reverse('recuperar_nueva'), {'clave': clave, 'confirmacion': clave})
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.context['form'].errors)

    def test_confirmacion_debe_coincidir(self):
        """PR-18 · La confirmación debe coincidir con la nueva contraseña"""
        self.solicitar()
        self.validar(self.ultimo_codigo())
        r = self.client.post(reverse('recuperar_nueva'), {'clave': NUEVA, 'confirmacion': NUEVA + 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('confirmacion', r.context['form'].errors)

    def test_nueva_igual_a_la_actual(self):
        """PR-19 · La nueva contraseña debe ser distinta de la actual"""
        self.solicitar()
        self.validar(self.ultimo_codigo())
        r = self.client.post(reverse('recuperar_nueva'), {'clave': self.clave, 'confirmacion': self.clave})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)

    def test_codigo_queda_invalidado_al_cambiar(self):
        """PR-20 · Al cambiar la contraseña el código queda usado y la sesión de recuperación se cierra"""
        self.solicitar()
        self.validar(self.ultimo_codigo())
        self.client.post(reverse('recuperar_nueva'), {'clave': NUEVA, 'confirmacion': NUEVA})
        cod = CodigoRecuperacion.objects.get()
        self.assertIsNotNone(cod.usado_en)
        self.assertNotIn('recuperacion', self.client.session)
        self.assertRedirects(self.client.get(reverse('recuperar_nueva')), reverse('recuperar'))

    def test_correo_no_revela_contrasena(self):
        """PR-21 · El correo contiene solo el código, nunca contraseñas"""
        self.solicitar()
        self.assertNotIn(self.clave, mail.outbox[0].body)
        self.assertIn('10 minutos', mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='cuentas.correo.BandejaBackend', SGR_BANDEJA_REENVIAR_SMTP=True,
                       EMAIL_HOST='127.0.0.1', EMAIL_PORT=1, EMAIL_TIMEOUT=2)
    def test_falla_smtp_no_interrumpe_recuperacion(self):
        """PR-22 · Si el servidor SMTP falla, la solicitud continúa y el código queda en la bandeja"""
        from cuentas.models import CorreoSaliente
        with self.assertLogs('sgr', level='ERROR'):
            r = self.solicitar()
        self.assertRedirects(r, reverse('recuperar_validar'))
        self.assertEqual(CorreoSaliente.objects.filter(destinatario='bcastillo@example.test').count(), 1)

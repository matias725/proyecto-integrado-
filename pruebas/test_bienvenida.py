"""
PB · Correo de bienvenida: al crear una cuenta, la persona recibe un enlace de un
solo uso para crear su propia contraseña.
"""

import re
from unittest import mock

from django.core import mail
from django.urls import reverse

from catalogos.models import Delegacion
from cuentas.models import Rol, Usuario

from .base import PruebaSGR

CLAVE = 'Elqui#Valle77'


class BienvenidaTests(PruebaSGR):

    def setUp(self):
        self.entrar('admin')

    def crear(self, **extra):
        datos = {'nombre': 'Paula Rivera', 'nombre_usuario': 'privera', 'correo': 'privera@example.test',
                 'rol': Rol.objects.get(codigo='ROL04').pk, 'delegaciones': [Delegacion.objects.first().pk],
                 'is_active': 'on'}
        datos.update(extra)
        return self.client.post(reverse('usuarios_crear'), datos, follow=True)

    def enlace(self):
        cuerpo = mail.outbox[-1].body
        return re.search(r'https?://\S+/bienvenida/\S+/', cuerpo).group(0).split('testserver', 1)[1]

    def test_crear_sin_clave_envia_bienvenida(self):
        """PB-01 · Crear una cuenta sin contraseña envía un correo de bienvenida a la persona"""
        r = self.crear()
        usuario = Usuario.objects.get(nombre_usuario='privera')
        self.assertFalse(usuario.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['privera@example.test'])
        self.assertIn('privera', mail.outbox[0].body)
        self.assertMensaje(r, 'correo de bienvenida')

    def test_no_puede_ingresar_antes_de_crear_su_clave(self):
        """PB-02 · Sin contraseña inicial, la cuenta no permite ingresar hasta usar el enlace"""
        self.crear()
        self.client.logout()
        r = self.client.post(reverse('acceso'), {'identificador': 'privera', 'clave': ''})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.wsgi_request.user.is_authenticated)

    def test_enlace_crea_clave_y_permite_ingresar(self):
        """PB-03 · El enlace permite crear la contraseña y luego ingresar con ella"""
        self.crear()
        enlace = self.enlace()
        self.client.logout()
        self.assertContains(self.client.get(enlace), 'Bienvenida, Paula Rivera')
        r = self.client.post(enlace, {'clave': CLAVE, 'confirmacion': CLAVE}, follow=True)
        self.assertMensaje(r, 'Contraseña creada')
        self.assertTrue(Usuario.objects.get(nombre_usuario='privera').check_password(CLAVE))
        self.entrar('privera', CLAVE)

    def test_enlace_sirve_una_sola_vez(self):
        """PB-04 · Usado el enlace, no sirve de nuevo"""
        self.crear()
        enlace = self.enlace()
        self.client.logout()
        self.client.post(enlace, {'clave': CLAVE, 'confirmacion': CLAVE})
        r = self.client.post(enlace, {'clave': 'Otra#Clave88', 'confirmacion': 'Otra#Clave88'}, follow=True)
        self.assertMensaje(r, 'no es válido')
        self.assertTrue(Usuario.objects.get(nombre_usuario='privera').check_password(CLAVE))

    def test_enlace_alterado_se_rechaza(self):
        """PB-05 · Un enlace con el token alterado o de otra cuenta se rechaza"""
        self.crear()
        enlace = self.enlace()
        self.client.logout()
        r = self.client.get(enlace[:-3] + 'xx/', follow=True)
        self.assertMensaje(r, 'no es válido')
        r = self.client.get(reverse('bienvenida', args=['MQ', 'token-falso']), follow=True)
        self.assertMensaje(r, 'no es válido')

    def test_clave_debil_no_se_acepta(self):
        """PB-06 · La contraseña creada desde la bienvenida cumple los mismos requisitos"""
        self.crear()
        enlace = self.enlace()
        self.client.logout()
        r = self.client.post(enlace, {'clave': 'abc', 'confirmacion': 'abc'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.get(nombre_usuario='privera').has_usable_password())

    def test_con_clave_inicial_tambien_envia_bienvenida(self):
        """PB-07 · Si el administrador pone una contraseña inicial, igual llega el correo para cambiarla"""
        self.crear(clave=CLAVE, confirmacion=CLAVE)
        self.assertTrue(Usuario.objects.get(nombre_usuario='privera').check_password(CLAVE))
        self.assertEqual(len(mail.outbox), 1)

    def test_falla_del_correo_no_impide_crear(self):
        """PB-08 · Si el correo falla, la cuenta queda creada y se avisa al administrador"""
        with mock.patch('cuentas.bienvenida.send_mail', side_effect=OSError('SMTP caído')):
            r = self.crear()
        self.assertTrue(Usuario.objects.filter(nombre_usuario='privera').exists())
        self.assertMensaje(r, 'no se pudo enviar')

    def test_editar_no_reenvia(self):
        """PB-09 · Editar una cuenta existente no envía otra bienvenida"""
        usuario = self.usuario('bcastillo')
        self.client.post(reverse('usuarios_editar', args=[usuario.pk]), {
            'nombre': usuario.nombre, 'nombre_usuario': usuario.nombre_usuario, 'correo': usuario.correo,
            'rol': usuario.rol_id, 'cargo': usuario.cargo_id or '',
            'delegaciones': list(usuario.delegaciones.values_list('pk', flat=True)), 'is_active': 'on'})
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(Usuario.objects.get(pk=usuario.pk).check_password(self.clave))

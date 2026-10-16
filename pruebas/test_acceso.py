"""Pruebas de acceso al sistema (login, logout y rutas protegidas)."""

from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Auditoria

from .base import PruebaSGR


class AccesoTests(PruebaSGR):

    def test_acceso_correcto_con_usuario(self):
        """PA-01 · Acceso correcto con nombre de usuario y contraseña"""
        r = self.client.post(reverse('acceso'), {'identificador': 'bcastillo', 'clave': self.clave})
        self.assertRedirects(r, reverse('inicio'))
        r = self.client.get(reverse('inicio'))
        self.assertContains(r, 'Bruno Castillo Peña')
        self.assertContains(r, 'Funcionario')
        self.assertTrue(Auditoria.objects.filter(evento='ACCESO', usuario__nombre_usuario='bcastillo').exists())

    def test_acceso_correcto_con_correo_sin_distinguir_mayusculas(self):
        """PA-02 · Acceso correcto con correo (sin distinguir mayúsculas)"""
        r = self.client.post(reverse('acceso'), {'identificador': 'BCastillo@Example.TEST', 'clave': self.clave})
        self.assertRedirects(r, reverse('inicio'))

    def test_clave_incorrecta_mensaje_generico(self):
        """PA-03 · Contraseña incorrecta: mensaje genérico, sin sesión"""
        r = self.client.post(reverse('acceso'), {'identificador': 'bcastillo', 'clave': 'Otra#2026'})
        self.assertEqual(r.status_code, 200)
        self.assertMensaje(r, 'Usuario, correo o contraseña incorrectos')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(Auditoria.objects.filter(evento='ACCESO_FALLIDO').exists())

    def test_usuario_inexistente_mismo_mensaje(self):
        """PA-04 · Usuario inexistente: mismo mensaje que clave incorrecta (no revela cuentas)"""
        r1 = self.client.post(reverse('acceso'), {'identificador': 'noexiste', 'clave': 'Otra#2026'})
        r2 = self.client.post(reverse('acceso'), {'identificador': 'bcastillo', 'clave': 'Otra#2026'})
        self.assertEqual(self.mensajes(r1), self.mensajes(r2))

    def test_campos_vacios(self):
        """PA-05 · Campos vacíos: errores por campo y sin sesión"""
        r = self.client.post(reverse('acceso'), {'identificador': '', 'clave': ''})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors.get('identificador'))
        self.assertTrue(r.context['form'].errors.get('clave'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cuenta_inactiva(self):
        """PA-06 · Cuenta inactiva no puede ingresar"""
        r = self.client.post(reverse('acceso'), {'identificador': 'dfuentes', 'clave': self.clave})
        self.assertEqual(r.status_code, 200)
        self.assertMensaje(r, 'inactiva')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cuenta_inactiva_con_clave_mala_no_revela_estado(self):
        """PA-07 · Cuenta inactiva con contraseña errónea: no revela que existe"""
        r = self.client.post(reverse('acceso'), {'identificador': 'dfuentes', 'clave': 'Otra#2026'})
        self.assertMensaje(r, 'incorrectos')

    def test_rol_inactivo_impide_acceso(self):
        """PA-08 · Usuario con rol desactivado no puede ingresar"""
        rol = self.usuario('lectura').rol
        rol.activo = False
        rol.save()
        r = self.client.post(reverse('acceso'), {'identificador': 'lectura', 'clave': self.clave})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(r.status_code, 200)

    @override_settings(SGR_LOGIN_MAX_INTENTOS=3, SGR_LOGIN_BLOQUEO_MIN=10)
    def test_bloqueo_temporal_tras_intentos_fallidos(self):
        """PA-09 · Bloqueo temporal tras intentos fallidos consecutivos"""
        for _ in range(3):
            self.client.post(reverse('acceso'), {'identificador': 'cvega', 'clave': 'Mala#0000'})
        r = self.client.post(reverse('acceso'), {'identificador': 'cvega', 'clave': self.clave})
        self.assertMensaje(r, 'bloqueado temporalmente')
        self.assertNotIn('_auth_user_id', self.client.session)
        # Vencido el bloqueo vuelve a ingresar
        u = self.usuario('cvega')
        u.bloqueado_hasta = timezone.now() - timedelta(seconds=1)
        u.save()
        self.entrar('cvega')

    def test_cerrar_sesion(self):
        """PA-10 · Cerrar sesión invalida la sesión y vuelve al acceso"""
        self.entrar('bcastillo')
        r = self.client.post(reverse('salir'))
        self.assertRedirects(r, reverse('acceso'))
        r = self.client.get(reverse('inicio'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('acceso'), r['Location'])

    def test_salir_por_get_no_permitido(self):
        """PA-11 · Cerrar sesión exige POST (protección CSRF)"""
        self.entrar('bcastillo')
        r = self.client.get(reverse('salir'))
        self.assertEqual(r.status_code, 405)

    def test_rutas_protegidas_sin_sesion(self):
        """PA-12 · Rutas protegidas redirigen al acceso cuando no hay sesión"""
        for ruta in ['inicio', 'delegaciones_lista', 'roles_lista', 'usuarios_lista', 'items_lista',
                     'tipos_atencion_lista', 'sub_atenciones_lista', 'atenciones_lista', 'atenciones_crear',
                     'auditoria', 'correos', 'delegaciones_exportar', 'tablero']:
            with self.subTest(ruta=ruta):
                r = self.client.get(reverse(ruta))
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r['Location'].startswith(reverse('acceso')))

    def test_redireccion_siguiente_segura(self):
        """PA-13 · Tras ingresar vuelve a la ruta pedida, nunca a un sitio externo"""
        r = self.client.post(reverse('acceso') + '?next=/delegaciones/',
                             {'identificador': 'admin', 'clave': self.clave})
        self.assertRedirects(r, '/delegaciones/')
        self.client.post(reverse('salir'))
        r = self.client.post(reverse('acceso') + '?next=https://malicioso.example/',
                             {'identificador': 'admin', 'clave': self.clave})
        self.assertRedirects(r, reverse('inicio'))

    def test_contrasenas_no_se_guardan_en_texto(self):
        """PA-14 · Las contraseñas se almacenan con hash, nunca en texto plano"""
        u = self.usuario('admin')
        self.assertNotIn(self.clave, u.password)
        self.assertTrue(u.check_password(self.clave))

    def test_usuario_autenticado_en_acceso_va_a_inicio(self):
        """PA-15 · Un usuario con sesión que abre el acceso es llevado al inicio"""
        self.entrar('admin')
        self.assertRedirects(self.client.get(reverse('acceso')), reverse('inicio'))

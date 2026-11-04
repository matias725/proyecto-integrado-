"""
PS · Seguridad transversal: cabeceras, límite por IP y caché de páginas con sesión.
Complementa test_acceso (bloqueo por cuenta) y test_permisos (roles y alcance).
"""

from django.test import override_settings
from django.urls import reverse

from core.seguridad import ip_cliente

from .base import PruebaSGR


class CabecerasTests(PruebaSGR):

    def test_cabeceras_en_pagina_publica(self):
        """PS-01 · La página de acceso envía CSP estricta, Permissions-Policy, nosniff y anti-iframe"""
        r = self.client.get(reverse('acceso'))
        csp = r['Content-Security-Policy']
        for directiva in ("script-src 'self'", "style-src 'self'", "frame-ancestors 'none'", "object-src 'none'"):
            self.assertIn(directiva, csp)
        self.assertNotIn('unsafe-inline', csp)
        self.assertIn('camera=()', r['Permissions-Policy'])
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_paginas_con_sesion_no_se_guardan_en_cache(self):
        """PS-02 · Las páginas con sesión llevan Cache-Control no-store (equipos compartidos)"""
        self.entrar('bcastillo')
        self.assertIn('no-store', self.client.get(reverse('inicio'))['Cache-Control'])

    def test_plantillas_sin_scripts_ni_estilos_en_linea(self):
        """PS-03 · Ninguna pantalla trae <style>, style="…" ni manejadores on…= (requisito de la CSP)"""
        self.entrar('admin')
        for nombre in ('inicio', 'tablero', 'actividades', 'actividad_nueva', 'agenda', 'ausencias', 'informes',
                       'periodos', 'metas', 'organizaciones_lista'):
            html = self.client.get(reverse(nombre)).content.decode()
            for prohibido in ('<style', 'style="', 'onclick=', 'onchange=', 'javascript:'):
                self.assertNotIn(prohibido, html, f'{nombre}: {prohibido}')


@override_settings(SGR_IP_MAX_INTENTOS=3, SGR_IP_VENTANA_MIN=15)
class LimitePorIPTests(PruebaSGR):

    def intento(self, usuario='nadie', **meta):
        return self.client.post(reverse('acceso'), {'identificador': usuario, 'clave': 'mala'}, **meta)

    def test_limite_por_ip_en_acceso(self):
        """PS-04 · Tras 3 intentos desde la misma IP, el 4.º responde 429 aunque cambie la cuenta"""
        for usuario in ('uno', 'dos', 'tres'):
            self.assertEqual(self.intento(usuario).status_code, 200)
        r = self.intento('cuatro')
        self.assertEqual(r.status_code, 429)
        self.assertIn('Retry-After', r)
        self.assertContains(r, 'Demasiados intentos', status_code=429)

    def test_otra_ip_no_se_ve_afectada(self):
        """PS-05 · El límite es por IP: otra dirección sigue pudiendo intentar"""
        for _ in range(3):
            self.intento(REMOTE_ADDR='10.0.0.1')
        self.assertEqual(self.intento(REMOTE_ADDR='10.0.0.1').status_code, 429)
        self.assertEqual(self.intento(REMOTE_ADDR='10.0.0.2').status_code, 200)

    @override_settings(SGR_DETRAS_DE_PROXY=True)
    def test_x_forwarded_for_falso_no_evita_el_limite(self):
        """PS-06 · Inventar X-Forwarded-For no evita el límite: se usa la IP que agrega Nginx"""
        for n in range(3):
            self.intento(HTTP_X_FORWARDED_FOR=f'1.1.1.{n}, 200.1.1.1')
        self.assertEqual(self.intento(HTTP_X_FORWARDED_FOR='9.9.9.9, 200.1.1.1').status_code, 429)

    def test_limite_en_recuperacion(self):
        """PS-07 · La recuperación de clave también tiene límite por IP"""
        for _ in range(3):
            self.client.post(reverse('recuperar'), {'identificador': 'x@example.test'})
        self.assertEqual(self.client.post(reverse('recuperar'), {'identificador': 'y@example.test'}).status_code, 429)

    def test_navegar_no_consume_intentos(self):
        """PS-08 · Solo cuentan los envíos (POST); abrir la página de acceso no consume intentos"""
        for _ in range(10):
            self.assertEqual(self.client.get(reverse('acceso')).status_code, 200)
        self.assertEqual(self.intento().status_code, 200)

    @override_settings(SGR_DETRAS_DE_PROXY=False)
    def test_sin_proxy_se_ignora_x_forwarded_for(self):
        """PS-09 · Sin proxy configurado se usa REMOTE_ADDR y se ignora X-Forwarded-For"""
        r = self.client.get(reverse('acceso'), HTTP_X_FORWARDED_FOR='9.9.9.9', REMOTE_ADDR='10.1.1.1')
        self.assertEqual(ip_cliente(r.wsgi_request), '10.1.1.1')

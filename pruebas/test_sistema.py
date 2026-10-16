"""Pruebas transversales: SweetAlert2, auditoría, salud y páginas de error."""

import json
import re

from django.test import Client
from django.urls import reverse

from catalogos.models import ItemMedicion
from core.models import Auditoria

from .base import PruebaSGR


def mensajes_sweetalert(respuesta):
    """Mensajes que la página entrega a SweetAlert2 (bloque JSON #mensajes-sgr)."""
    hallado = re.search(r'<script id="mensajes-sgr" type="application/json">(.*?)</script>',
                        respuesta.content.decode(), re.S)
    return json.loads(hallado.group(1)) if hallado else []


class SweetAlertTests(PruebaSGR):

    def test_exito_se_entrega_a_sweetalert(self):
        """PS-01 · Una operación exitosa se comunica a SweetAlert2 con nivel «success»"""
        self.entrar('admin')
        item = ItemMedicion.objects.first()
        r = self.client.post(reverse('items_editar', args=[item.pk]), {
            'codigo': item.codigo, 'nombre': item.nombre, 'descripcion': 'Nueva descripción', 'activo': 'on'},
            follow=True)
        niveles = {m['nivel'] for m in mensajes_sweetalert(r)}
        self.assertIn('success', niveles)

    def test_error_no_muestra_exito(self):
        """PS-02 · Si la operación falla se muestra error y nunca un mensaje de éxito"""
        self.entrar('admin')
        r = self.client.post(reverse('items_crear'), {'codigo': '', 'nombre': ''})
        niveles = {m['nivel'] for m in mensajes_sweetalert(r)}
        self.assertIn('error', niveles)
        self.assertNotIn('success', niveles)

    def test_confirmacion_antes_de_eliminar(self):
        """PS-03 · Los formularios de eliminar y desactivar piden confirmación (data-confirmar)"""
        self.entrar('admin')
        r = self.client.get(reverse('items_ver', args=[ItemMedicion.objects.first().pk]))
        self.assertContains(r, 'data-confirmar="¿Eliminar')
        self.assertContains(r, 'data-confirmar="¿Desactivar')

    def test_libreria_cargada_localmente(self):
        """PS-04 · SweetAlert2 se sirve desde el propio sistema (sin depender de un CDN)"""
        self.entrar('admin')
        r = self.client.get(reverse('inicio'))
        self.assertContains(r, 'vendor/sweetalert2/sweetalert2.min.js')

    def test_mensajes_escapados(self):
        """PS-05 · Los mensajes con caracteres especiales no inyectan código"""
        self.entrar('admin')
        r = self.client.post(reverse('items_crear'), {
            'codigo': 'IT050', 'nombre': '<script>alert(1)</script>', 'descripcion': 'x', 'activo': 'on'},
            follow=True)
        self.assertNotIn('<script>alert(1)</script>', r.content.decode())


class AuditoriaTests(PruebaSGR):

    def test_auditoria_no_registra_contrasenas(self):
        """PU-01 · La auditoría nunca guarda contraseñas"""
        self.client.post(reverse('acceso'), {'identificador': 'admin', 'clave': 'Mala#Clave99'})
        self.entrar('admin')
        textos = ' '.join(f'{a.detalle} {a.registro}' for a in Auditoria.objects.all())
        self.assertNotIn('Mala#Clave99', textos)
        self.assertNotIn(self.clave, textos)

    def test_auditoria_solo_lectura_y_filtro(self):
        """PU-02 · La auditoría lista y filtra eventos; no ofrece edición"""
        self.entrar('admin')
        r = self.client.get(reverse('auditoria'), {'evento': 'ACCESO'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(all(e.evento == 'ACCESO' for e in r.context['pagina'].object_list))
        self.assertNotContains(r, 'Eliminar')
        self.assertEqual(self.client.post(reverse('auditoria')).status_code, 405)


class SistemaTests(PruebaSGR):

    def test_salud(self):
        """PX-01 · El punto de salud responde 200 con la base de datos disponible"""
        r = self.client.get(reverse('salud'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['estado'], 'ok')

    def test_pagina_inexistente(self):
        """PX-02 · Una ruta inexistente devuelve 404"""
        self.entrar('admin')
        self.assertEqual(self.client.get('/no-existe/').status_code, 404)

    def test_registro_inexistente(self):
        """PX-03 · Un registro inexistente devuelve 404 (no error 500)"""
        self.entrar('admin')
        self.assertEqual(self.client.get(reverse('items_ver', args=[99999])).status_code, 404)

    def test_cabeceras_de_seguridad(self):
        """PX-04 · Las respuestas incluyen cabeceras de seguridad básicas"""
        r = self.client.get(reverse('acceso'))
        self.assertEqual(r['X-Frame-Options'], 'DENY')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')

    def test_modulos_simulados_navegables(self):
        """PX-05 · Los módulos en desarrollo son navegables y se identifican como simulados"""
        self.entrar('admin')
        for ruta in ['tablero', 'actividades', 'evidencias', 'validacion', 'agenda', 'atencion_social',
                     'periodos', 'metas', 'informes']:
            with self.subTest(ruta=ruta):
                r = self.client.get(reverse(ruta))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, 'Módulo simulado')

    def test_formulario_sin_token_csrf(self):
        """PX-06 · Un envío sin token CSRF se rechaza con una pantalla clara y sin guardar"""
        cliente = Client(enforce_csrf_checks=True)
        r = cliente.post(reverse('acceso'), {'identificador': 'admin', 'clave': self.clave})
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, 'El formulario venció', status_code=403)
        self.assertNotIn('_auth_user_id', cliente.session)

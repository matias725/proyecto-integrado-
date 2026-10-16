"""
Base común de las pruebas automatizadas del SGR.

Cada prueba lleva en la primera línea de su docstring un identificador
(PA-xx, PR-xx, …) que coincide con la matriz de pruebas funcionales
(docs/pruebas/matriz_pruebas_funcionales.xlsx).
"""

import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from cuentas.inicial import CLAVE_DEMO, cargar_base, cargar_demo
from cuentas.models import Usuario

HASH_RAPIDO = ['django.contrib.auth.hashers.MD5PasswordHasher']


@override_settings(PASSWORD_HASHERS=HASH_RAPIDO,
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
                             'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}})
class PruebaSGR(TestCase):
    """Base con permisos, catálogos y cuentas de demostración cargados."""

    clave = CLAVE_DEMO

    @classmethod
    def setUpTestData(cls):
        cargar_base()
        cargar_demo(CLAVE_DEMO)

    # ----- utilidades ----------------------------------------------------
    def entrar(self, usuario, clave=None):
        respuesta = self.client.post(reverse('acceso'), {'identificador': usuario, 'clave': clave or self.clave})
        self.assertEqual(respuesta.status_code, 302, f'No se pudo ingresar como {usuario}')
        self.client.get(respuesta['Location'])  # consume el mensaje de bienvenida
        return respuesta

    def usuario(self, nombre_usuario):
        return Usuario.objects.get(nombre_usuario=nombre_usuario)

    def mensajes(self, respuesta):
        return [str(m) for m in respuesta.context['messages']] if respuesta.context else []

    @staticmethod
    def ultimo_codigo():
        """Código de 6 dígitos del último correo enviado."""
        assert mail.outbox, 'No se envió ningún correo'
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def assertMensaje(self, respuesta, fragmento):
        textos = self.mensajes(respuesta)
        self.assertTrue(any(fragmento.lower() in t.lower() for t in textos),
                        f'No se encontró «{fragmento}» en {textos}')

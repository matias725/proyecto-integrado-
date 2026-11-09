"""
Correo de bienvenida al crear una cuenta.

La persona recibe un enlace de un solo uso para crear su propia contraseña, así el
administrador no necesita conocerla ni enviarla por otro medio.

- El enlace usa el generador de tokens de Django: queda inválido apenas se cambia la
  contraseña o se ingresa al sistema, y vence a las SGR_BIENVENIDA_HORAS (72 por defecto).
- Si el correo falla, la cuenta igual queda creada y la persona puede recuperar su
  contraseña con el flujo de código de 6 dígitos.
"""

import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.models import registrar

registro = logging.getLogger(__name__)


def enlace_bienvenida(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    return request.build_absolute_uri(reverse('bienvenida', args=[uid, token]))


def enviar_bienvenida(request, usuario):
    enlace = enlace_bienvenida(request, usuario)
    horas = settings.PASSWORD_RESET_TIMEOUT // 3600
    try:
        send_mail(
            'Bienvenida al Sistema de Gestión de Resultados · SGR La Serena',
            f'Hola {usuario.nombre}:\n\n'
            f'Se creó su cuenta en el Sistema de Gestión de Resultados de la Municipalidad de La Serena.\n\n'
            f'Usuario: {usuario.nombre_usuario}\n'
            f'Correo: {usuario.correo}\n\n'
            f'Para crear su contraseña, abra este enlace:\n{enlace}\n\n'
            f'El enlace sirve una sola vez y vence en {horas} horas. Si vence, use «¿Olvidó su contraseña?» '
            'en la página de acceso.\n\n'
            'Si usted no esperaba este correo, ignórelo.\n\n'
            'Sistema de Gestión de Resultados · Municipalidad de La Serena',
            None, [usuario.correo], fail_silently=False)
    except Exception:  # SMTP caído o mal configurado: la cuenta ya existe, se informa al administrador
        registro.exception('No se pudo enviar la bienvenida a la cuenta %s', usuario.pk)
        return False
    registrar(request, 'BIENVENIDA', 'cuenta', usuario.pk, 'Correo de bienvenida enviado')
    return True

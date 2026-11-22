"""
Bandeja de correos de prueba.

Guarda cada correo en la base de datos para que el superadministrador pueda
leerlo en el sistema. Permite demostrar la recuperación de contraseña en un
entorno sin servidor de correo. En producción se reemplaza por SMTP
(SGR_CORREO_BACKEND=django.core.mail.backends.smtp.EmailBackend).
"""

import logging
import re

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend


CODIGO = re.compile(r'\b\d{6}\b')
ENLACE_PERSONAL = re.compile(r'https?://\S*/bienvenida/\S*')


def ocultar_secretos(cuerpo):
    """Quita del texto los códigos de recuperación y los enlaces para crear contraseña."""
    cuerpo = ENLACE_PERSONAL.sub('[enlace personal oculto: solo llega al correo de la persona]', cuerpo)
    return CODIGO.sub('●●●●●●', cuerpo)


class BandejaBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        from .models import CorreoSaliente

        enviados = 0
        # Si el correo llega de verdad a la persona (SMTP activo), la copia de la bandeja no guarda
        # códigos ni enlaces: así el administrador no puede usarlos para cambiar una contraseña ajena.
        ocultar = settings.SGR_BANDEJA_REENVIAR_SMTP
        for mensaje in email_messages:
            cuerpo = ocultar_secretos(mensaje.body) if ocultar else mensaje.body
            for destinatario in mensaje.to:
                CorreoSaliente.objects.create(destinatario=destinatario, asunto=mensaje.subject, cuerpo=cuerpo)
            enviados += 1
        if settings.SGR_BANDEJA_REENVIAR_SMTP and email_messages:
            # La copia en la bandeja ya quedó guardada (sin secretos): si el SMTP falla se
            # registra el error y la persona puede pedir un código nuevo.
            try:
                SMTPBackend(fail_silently=False).send_messages(email_messages)
            except Exception:
                logging.getLogger('sgr').exception('No se pudo reenviar el correo por SMTP')
        return enviados

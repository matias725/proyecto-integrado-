"""
Bandeja de correos de prueba.

Guarda cada correo en la base de datos para que el superadministrador pueda
leerlo en el sistema. Permite demostrar la recuperación de contraseña en un
entorno sin servidor de correo. En producción se reemplaza por SMTP
(SGR_CORREO_BACKEND=django.core.mail.backends.smtp.EmailBackend).
"""

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend


class BandejaBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        from .models import CorreoSaliente

        enviados = 0
        for mensaje in email_messages:
            for destinatario in mensaje.to:
                CorreoSaliente.objects.create(destinatario=destinatario, asunto=mensaje.subject, cuerpo=mensaje.body)
            enviados += 1
        if settings.SGR_BANDEJA_REENVIAR_SMTP and email_messages:
            SMTPBackend(fail_silently=self.fail_silently).send_messages(email_messages)
        return enviados

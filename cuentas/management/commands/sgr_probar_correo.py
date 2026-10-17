"""Envía un correo de prueba para comprobar la configuración SMTP.

Uso: python manage.py sgr_probar_correo destinatario@dominio.cl
"""

from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Envía un correo de prueba por SMTP para verificar la configuración.'

    def add_arguments(self, parser):
        parser.add_argument('destinatario')

    def handle(self, *args, **opciones):
        if not settings.EMAIL_HOST:
            raise CommandError('SGR_SMTP_HOST no está configurado en el .env.')
        conexion = get_connection('django.core.mail.backends.smtp.EmailBackend', fail_silently=False)
        try:
            send_mail('Prueba de correo · SGR La Serena',
                      'Si recibe este mensaje, el envío de códigos de recuperación está operativo.',
                      None, [opciones['destinatario']], connection=conexion)
        except Exception as error:
            raise CommandError(f'No se pudo enviar: {error}') from error
        self.stdout.write(self.style.SUCCESS(f'Correo enviado a {opciones["destinatario"]} '
                                             f'mediante {settings.EMAIL_HOST}.'))

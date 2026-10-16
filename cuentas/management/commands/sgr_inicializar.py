from django.core.management.base import BaseCommand

from cuentas.inicial import CLAVE_DEMO, cargar_base, cargar_demo


class Command(BaseCommand):
    help = 'Carga permisos, roles y catálogos del SGR. Con --demo agrega cuentas y atenciones ficticias.'

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true', help='Crear cuentas y atenciones de demostración.')
        parser.add_argument('--clave', default=CLAVE_DEMO, help='Contraseña de las cuentas de demostración.')

    def handle(self, *args, **opciones):
        cargar_base()
        self.stdout.write(self.style.SUCCESS('Permisos, roles y catálogos cargados.'))
        if opciones['demo']:
            cargar_demo(opciones['clave'])
            self.stdout.write(self.style.SUCCESS('Cuentas y atenciones de demostración cargadas.'))

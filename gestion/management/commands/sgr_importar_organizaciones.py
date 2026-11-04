"""Uso: python manage.py sgr_importar_organizaciones ruta/base_jjvv.xlsx [--simular]"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion.importacion import importar


class Command(BaseCommand):
    help = 'Importa la base de juntas de vecinos y organizaciones comunitarias desde Excel.'

    def add_arguments(self, parser):
        parser.add_argument('archivo')
        parser.add_argument('--simular', action='store_true', help='Muestra el resultado sin guardar nada.')

    def handle(self, archivo, simular=False, **opciones):
        try:
            with transaction.atomic():
                r = importar(archivo, simular=simular)
        except FileNotFoundError as error:
            raise CommandError(f'No se encontró el archivo {archivo}.') from error
        self.stdout.write(self.style.SUCCESS(
            f'{"Simulación: " if simular else ""}{r.leidas} filas leídas · {r.creadas} creadas · '
            f'{r.actualizadas} actualizadas · {r.omitidas} omitidas · {r.con_observacion} con observación'))
        self.stdout.write('Por territorio: ' + ', '.join(f'{k} {v}' for k, v in sorted(r.por_territorio.items())))
        self.stdout.write('Por subfamilia: ' + ', '.join(
            f'{k} {v}' for k, v in sorted(r.por_subfamilia.items(), key=lambda x: -x[1])))
        for problema in r.problemas:
            self.stdout.write(self.style.WARNING(problema))

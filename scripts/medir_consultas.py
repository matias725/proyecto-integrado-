"""
Plan de ejecución (EXPLAIN ANALYZE) y tiempo de las consultas críticas de la matriz SGR.

Carga un volumen sintético de actividades (por defecto 60.000, ≈ un año de 6 delegaciones)
y muestra cómo MySQL usa los índices definidos en gestion/models.py.

Uso (contra una base MySQL de pruebas, NUNCA la de producción):
    SGR_DB_MOTOR=mysql python scripts/medir_consultas.py [--volumen 60000] > docs/bd/explain_mysql8.txt
"""

import argparse
import os
import random
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgr.settings')

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from django.db.models import Count  # noqa: E402

from catalogos.models import ItemMedicion  # noqa: E402
from cuentas.models import Usuario  # noqa: E402
from gestion import calculos  # noqa: E402
from gestion.models import Actividad, Periodo  # noqa: E402
from gestion.reglas import hoy  # noqa: E402


def cargar(volumen):
    actual = Actividad.objects.count()
    if actual >= volumen:
        return actual
    periodo = Periodo.objects.get(estado=Periodo.ABIERTO)
    funcionarios = list(Usuario.objects.filter(cargo__isnull=False).prefetch_related('delegaciones'))
    items = list(ItemMedicion.objects.values_list('pk', flat=True))
    azar = random.Random(7)
    lote = []
    for n in range(volumen - actual):
        f = azar.choice(funcionarios)
        delegacion = f.delegaciones.all()[0]
        dia = periodo.inicio + timedelta(days=azar.randrange(periodo.dias))
        lote.append(Actividad(
            periodo=periodo, delegacion=delegacion, funcionario=f, item_id=azar.choice(items), fecha=dia,
            ingresada_el=dia, titulo=f'Carga sintética {n}', descripcion='Volumen para medir índices',
            estado=azar.choice([Actividad.REALIZADO] * 4 + [Actividad.PENDIENTE]), puntua=azar.random() > .15,
            validacion=azar.choice([Actividad.VALIDACION_PENDIENTE, Actividad.VALIDADA]),
            fecha_compromiso=dia + timedelta(days=5) if azar.random() < .2 else None))
        if len(lote) == 5000:
            Actividad.objects.bulk_create(lote)
            lote = []
    Actividad.objects.bulk_create(lote)
    with connection.cursor() as c:
        c.execute('ANALYZE TABLE gestion_actividad')
    return Actividad.objects.count()


def explicar(titulo, consulta):
    sql, params = consulta.query.sql_with_params()
    with connection.cursor() as c:
        inicio = time.perf_counter()
        c.execute(sql, params)
        filas = len(c.fetchall())
        ms = (time.perf_counter() - inicio) * 1000
        c.execute('EXPLAIN ANALYZE ' + sql, params)
        plan = c.fetchone()[0]
    print(f'\n## {titulo}\n')
    print(f'Filas devueltas: {filas} · tiempo: {ms:.1f} ms\n')
    print(plan)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--volumen', type=int, default=60000)
    args = parser.parse_args()
    if connection.vendor != 'mysql':
        sys.exit('Ejecute con SGR_DB_MOTOR=mysql (EXPLAIN ANALYZE es de MySQL 8).')
    total = cargar(args.volumen)
    with connection.cursor() as c:
        c.execute('SELECT VERSION()')
        version = c.fetchone()[0]
    periodo = Periodo.objects.get(estado=Periodo.ABIERTO)
    funcionario = Usuario.objects.get(nombre_usuario='bcastillo')
    rural = funcionario.delegaciones.first()
    print(f'# EXPLAIN ANALYZE · MySQL {version} · {total} actividades')

    explicar('Regla 3 · ingresos del día de un funcionario (índice act_ingresos_diarios)',
             Actividad.objects.filter(funcionario=funcionario, ingresada_el=hoy()).values('id'))
    explicar('Avance por funcionario e ítem del período (índice act_avance_item)',
             Actividad.objects.filter(periodo=periodo, funcionario_id__in=[funcionario.pk], puntua=True,
                                      estado=Actividad.REALIZADO).exclude(validacion=Actividad.RECHAZADA)
             .values('funcionario_id', 'item_id').annotate(n=Count('id')))
    explicar('Listado de actividades de la delegación, más recientes primero (índice act_delegacion_fecha)',
             Actividad.objects.filter(delegacion=rural).values('id', 'fecha', 'titulo')[:25])
    explicar('Bandeja de validación del delegado (índice act_bandeja_validacion)',
             Actividad.objects.filter(delegacion=rural, validacion=Actividad.VALIDACION_PENDIENTE).values('id')[:25])

    equipo = list(Usuario.objects.filter(delegaciones=rural, is_active=True).select_related('cargo'))
    inicio = time.perf_counter()
    resultado = calculos.indicadores(periodo, equipo)
    ms = (time.perf_counter() - inicio) * 1000
    print(f'\n## Cálculo completo de la matriz de la delegación Rural\n')
    print(f'{len(resultado["fichas"])} fichas calculadas en {ms:.1f} ms (consultas agregadas, sin N+1).')


if __name__ == '__main__':
    main()

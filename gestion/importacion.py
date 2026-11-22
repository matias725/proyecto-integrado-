"""
Importación de la base de juntas de vecinos y organizaciones (Excel «sin verificar»).

Columnas esperadas en la primera hoja: ORGANIZACIONES, DOMICILIO LEGAL, TERRIT. DELEG., SOCIOS ACTIVOS,
FECHA CONSTIT., Nº REG. P.J., FECHA INSCRIPC EN REG., REG. DIR. Nº

Normaliza nombres y espacios, asigna la subfamilia por palabras clave, traduce el territorio a la delegación,
y deja una observación en cada fila con datos dudosos. Las organizaciones quedan «sin verificar».
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

from openpyxl import load_workbook

from catalogos.models import Delegacion, Sector

from .models import Organizacion, TipoOrganizacion

TERRITORIOS = {
    'CIAS': 'DEL04', 'COMPANIAS': 'DEL04', 'CENTRO': 'DEL01', 'PAMPA': 'DEL05', 'RURAL': 'DEL06',
    'ANTENA': 'DEL03', 'AV DEL MAR': 'DEL02', 'AVENIDA DEL MAR': 'DEL02',
    # Alfalfares no es una delegación: es un sector de La Antena según la lista «TERRITORIO» del TUBO
    # de la matriz SGR. Hasta la versión ev2-2.1.0 se asignaba a Rural como territorio inferido.
    'ALFALFARES': 'DEL03',
}
SECTOR_EN_TERRITORIO = {'ALFALFARES': 'Alfalfares'}

# (palabras clave, código de subfamilia). Se evalúan en orden: la primera que calza gana.
REGLAS_SUBFAMILIA = [
    (('UNION COMUNAL',), 'TO10'),
    (('JUNTA DE VECINOS', 'JJVV', 'JJ.VV', 'JUNTA VECINAL'), 'TO01'),
    (('ADULTO MAYOR', 'ADULTOS MAYORES', 'TERCERA EDAD', 'ABUELITOS'), 'TO02'),
    (('CENTRO DE MADRES', 'CENTRO DE MADRE'), 'TO04'),
    (('CENTRO DE PADRES', 'APODERADOS'), 'TO09'),
    (('DEPORTIV', 'FUTBOL', 'BASQUETBOL', 'TAEKWON', 'KARATE', 'ATLETISMO', 'CICLISMO', 'RAYUELA', 'TENIS',
      'AJEDREZ', 'BOXEO', 'VOLEIBOL', 'PATIN', 'SURF', 'RUGBY', 'HANDBALL'), 'TO03'),
    (('JUVENIL', 'JOVENES'), 'TO06'),
    (('VIVIENDA', 'HABITACIONAL', 'ALLEGADOS', 'AGUA POTABLE', 'COMITE AGUA', 'APR'), 'TO08'),
    (('SEGURIDAD', 'DELINCUENCIA', 'COMITE', 'VECINAL', 'VECINOS'), 'TO07'),
    (('CULTURAL', 'ARTISTIC', 'FOLCLOR', 'FOLKLOR', 'MUSICA', 'CORO', 'TEATRO', 'DANZA', 'BAILE', 'ORQUESTA',
      'CUECA', 'ACADEMIA', 'PINTURA', 'LITERA'), 'TO05'),
]


def sin_tildes(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def limpiar(texto):
    return re.sub(r'\s+', ' ', str(texto or '')).strip()


def subfamilia(nombre):
    clave = sin_tildes(nombre.upper())
    for palabras, codigo in REGLAS_SUBFAMILIA:
        if any(p in clave for p in palabras):
            return codigo
    return 'TO11'


def sector_por_nombre(nombre, sectores):
    """Sector de la delegación cuyo nombre aparece como palabra completa en el nombre de la organización."""
    clave = f' {sin_tildes(nombre.upper())} '
    candidatos = [s for s in sectores if f' {sin_tildes(s.nombre.upper())} ' in clave]
    return max(candidatos, key=lambda s: len(s.nombre), default=None)


def a_fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = limpiar(valor)
    for formato in ('%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d', '%d-%m-%y', '%d/%m/%y'):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def a_entero(valor):
    if isinstance(valor, (int, float)):
        return int(valor)
    digitos = re.sub(r'\D', '', str(valor or ''))
    return int(digitos) if digitos else None


@dataclass
class Resultado:
    leidas: int = 0
    creadas: int = 0
    actualizadas: int = 0
    omitidas: int = 0
    con_observacion: int = 0
    con_sector: int = 0
    por_subfamilia: dict = field(default_factory=dict)
    por_territorio: dict = field(default_factory=dict)
    problemas: list = field(default_factory=list)


def importar(ruta, simular=False):
    """Importa el Excel. Con simular=True solo informa lo que haría (nada se guarda)."""
    hoja = load_workbook(ruta, read_only=True, data_only=True).worksheets[0]
    tipos = {t.codigo: t for t in TipoOrganizacion.objects.all()}
    delegaciones = {d.codigo: d for d in Delegacion.objects.all()}
    sectores = {}
    for sector in Sector.objects.filter(activo=True).select_related('delegacion'):
        sectores.setdefault(sector.delegacion.codigo, []).append(sector)
    vistos = set()
    r = Resultado()
    for numero, fila in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
        fila = list(fila) + [None] * 8
        nombre = limpiar(fila[0]).upper()
        if not nombre:
            continue
        r.leidas += 1
        notas = []
        registro = a_entero(fila[5])
        if registro is None:
            r.omitidas += 1
            r.problemas.append(f'Fila {numero}: «{nombre}» sin N.º de registro de personalidad jurídica; se omite.')
            continue
        if registro in vistos:
            r.omitidas += 1
            r.problemas.append(f'Fila {numero}: registro PJ {registro} repetido en el archivo; se omite.')
            continue
        vistos.add(registro)
        territorio = sin_tildes(limpiar(fila[2]).upper())
        codigo_del = TERRITORIOS.get(territorio)
        if not territorio:
            notas.append('Sin territorio de delegación')
        elif codigo_del is None:
            notas.append(f'Territorio «{territorio}» no reconocido')
        socios = fila[3]
        socios_int = a_entero(socios) if isinstance(socios, (int, float)) else None
        if socios is not None and socios_int is None:
            notas.append(f'Socios no numérico: «{limpiar(socios)}»')
        elif socios is not None and not isinstance(socios, (int, float)):
            notas.append(f'Socios no numérico: «{limpiar(socios)}»')
        constitucion, inscripcion = a_fecha(fila[4]), a_fecha(fila[6])
        if fila[4] is not None and constitucion is None:
            notas.append(f'Fecha de constitución ilegible: «{limpiar(fila[4])}»')
        if constitucion and inscripcion and inscripcion < constitucion:
            notas.append('Inscripción anterior a la constitución')
        if not limpiar(fila[1]):
            notas.append('Sin domicilio legal')
        tipo = subfamilia(nombre)
        sector, avisos = None, []
        if territorio in SECTOR_EN_TERRITORIO:
            sector = next((x for x in sectores.get(codigo_del, []) if x.nombre == SECTOR_EN_TERRITORIO[territorio]),
                          None)
            avisos.append(f'Territorio «{territorio}»: sector de La Antena según la matriz SGR')
        elif codigo_del:
            sector = sector_por_nombre(nombre, sectores.get(codigo_del, []))
            if sector:
                avisos.append(f'Sector «{sector.nombre}» deducido del nombre')
        if sector:
            r.con_sector += 1
        datos = {
            'nombre': nombre[:200], 'tipo': tipos[tipo], 'delegacion': delegaciones.get(codigo_del),
            'sector': sector,
            'domicilio': limpiar(fila[1])[:200], 'socios': socios_int, 'fecha_constitucion': constitucion,
            'fecha_inscripcion': inscripcion, 'registro_directiva': a_entero(fila[7]),
            'observacion': '; '.join(notas + avisos)[:300], 'verificada': False,
        }
        r.por_subfamilia[tipos[tipo].nombre] = r.por_subfamilia.get(tipos[tipo].nombre, 0) + 1
        clave_del = delegaciones[codigo_del].nombre if codigo_del else 'Sin territorio'
        r.por_territorio[clave_del] = r.por_territorio.get(clave_del, 0) + 1
        if notas:
            r.con_observacion += 1
        if simular:
            r.creadas += 1
            continue
        existente = Organizacion.objects.filter(registro_pj=registro).first()
        if existente and existente.verificada:
            continue                  # no se pisa lo que un funcionario ya verificó
        _, creada = Organizacion.objects.update_or_create(registro_pj=registro, defaults=datos)
        if creada:
            r.creadas += 1
        else:
            r.actualizadas += 1
    return r

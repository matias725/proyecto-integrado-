"""
Pruebas de las observaciones de la revisión de la EV2 (versión ev2-2.2.0).

Prefijos (ver docs/pruebas/plan_de_pruebas_ev2.md):
    PN  pantalla de períodos más detallada (línea de tiempo, parámetros, detalle por delegación)
    PK  compromisos del TUBO: tabla con filtros y exportación
    PG  organizaciones: hasta 3 funcionarios encargados, sector dentro del territorio y catálogo de sectores

La fecha de trabajo es el miércoles 04-11-2026 (SGR_FECHA_HOY), igual que en test_matriz.
"""

import tempfile
from datetime import timedelta
from io import BytesIO

from django.db import IntegrityError, transaction
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from catalogos.models import Delegacion, Sector
from core.models import Auditoria
from gestion.importacion import importar
from gestion.models import Actividad, EncargadoOrganizacion, Organizacion, Periodo, TipoOrganizacion

from .test_matriz import ARCHIVOS, HOY, BaseMatriz


def filas_excel(respuesta):
    hoja = load_workbook(BytesIO(respuesta.content)).active
    return [[c for c in fila] for fila in hoja.iter_rows(values_only=True)]


# ---------------------------------------------------------------------------
# PN · Períodos
# ---------------------------------------------------------------------------
class PeriodosTests(BaseMatriz):

    def test_listado_muestra_periodo_en_curso(self):
        """PN-01 · El listado destaca el período en curso: día 35 de 92, parámetros y tarjetas de todos"""
        self.entrar('emunoz')
        r = self.client.get(reverse('periodos'))
        self.assertEqual(r.context['abierto'], self.periodo)
        self.assertContains(r, 'Día 35 de 92')
        self.assertEqual(len(r.context['parametros']), 6)
        self.assertContains(r, 'Tope por ítem')
        self.assertEqual(len(r.context['periodos']), Periodo.objects.count())
        total = Actividad.objects.filter(periodo=self.periodo).count()
        self.assertEqual(r.context['resumen']['total'], total)

    def test_detalle_cuadra_con_los_datos(self):
        """PN-02 · El detalle suma lo mismo por estado que el total y muestra las 6 delegaciones al coordinador"""
        self.entrar('emunoz')
        r = self.client.get(reverse('periodo_ver', args=[self.periodo.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sum(e['total'] for e in r.context['por_estado']), r.context['total'])
        self.assertEqual(sum(m['total'] for m in r.context['por_mes']), r.context['total'])
        self.assertEqual(len(r.context['por_delegacion']), Delegacion.objects.filter(activo=True).count())
        self.assertTrue(all(m['completa'] for m in r.context['metas_cargo']))
        self.assertAlmostEqual(r.context['esperado'], 35 / 92 * 100)

    def test_delegado_ve_solo_sus_delegaciones(self):
        """PN-03 · En el detalle, el delegado solo ve el resultado de sus delegaciones"""
        self.entrar('arojas')
        r = self.client.get(reverse('periodo_ver', args=[self.periodo.pk]))
        codigos = {d['delegacion'].codigo for d in r.context['por_delegacion']}
        self.assertEqual(codigos, {'DEL03', 'DEL06'})
        visibles = Actividad.objects.filter(periodo=self.periodo, delegacion__codigo__in=codigos).count()
        self.assertEqual(r.context['total'], visibles)

    def test_sin_permiso_no_ve_el_detalle(self):
        """PN-04 · Un funcionario sin permiso de períodos recibe 403 en el detalle"""
        self.entrar('bcastillo')
        self.assertEqual(self.client.get(reverse('periodo_ver', args=[self.periodo.pk])).status_code, 403)

    def test_fases_y_cierre_desde_el_detalle(self):
        """PN-05 · Fases por fecha (finalizado, en curso, por comenzar) y cerrar desde el detalle vuelve al detalle"""
        anterior = Periodo.objects.exclude(pk=self.periodo.pk).get()
        futuro = Periodo.objects.create(nombre='Trimestre 2027-Q1', inicio=self.periodo.termino + timedelta(days=1),
                                        termino=self.periodo.termino + timedelta(days=90), estado=Periodo.CERRADO)
        self.assertEqual((anterior.fase, self.periodo.fase, futuro.fase), ('finalizado', 'en curso', 'por comenzar'))
        self.assertEqual((futuro.dias_transcurridos, anterior.dias_restantes), (0, 0))
        self.entrar('emunoz')
        r = self.client.post(reverse('periodo_estado', args=[self.periodo.pk, 'cerrar']), {'volver': 'detalle'})
        self.assertRedirects(r, reverse('periodo_ver', args=[self.periodo.pk]))
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, Periodo.CERRADO)


# ---------------------------------------------------------------------------
# PK · Compromisos del TUBO: tabla con filtros
# ---------------------------------------------------------------------------
class CompromisosTests(BaseMatriz):

    def compromisos(self, **filtros):
        r = self.client.get(reverse('agenda'), filtros)
        self.assertEqual(r.status_code, 200)
        return r, list(r.context['pagina'].paginator.object_list)

    def test_tabla_por_defecto_ordenada_por_urgencia(self):
        """PK-01 · Por defecto se ve la tabla: solo compromisos, primero lo pendiente por fecha y al final lo realizado"""
        self.entrar('arojas')
        r, filas = self.compromisos()
        self.assertEqual(r.context['vista'], 'tabla')
        esperado = Actividad.objects.filter(periodo=self.periodo, delegacion=self.rural,
                                            fecha_compromiso__isnull=False).count()
        self.assertEqual(len(filas), esperado)
        cerradas = [a.estado == Actividad.REALIZADO for a in filas]
        self.assertEqual(cerradas, sorted(cerradas))                       # pendientes antes que realizadas
        pendientes = [a.fecha_compromiso for a in filas if a.estado != Actividad.REALIZADO]
        self.assertEqual(pendientes, sorted(pendientes))
        self.assertEqual(r.context['total'], esperado)

    def test_filtro_por_plazo(self):
        """PK-02 · Plazo: vencidas, vencen en 7 días y realizadas filtran sin mezclarse"""
        self.entrar('arojas')
        _, vencidas = self.compromisos(plazo='vencidas')
        self.assertTrue(vencidas)
        self.assertTrue(all(a.vencida for a in vencidas))
        _, semana = self.compromisos(plazo='semana')
        self.assertTrue(all(HOY <= a.fecha_compromiso <= HOY + timedelta(days=7) and a.estado != Actividad.REALIZADO
                            for a in semana))
        _, realizadas = self.compromisos(plazo='realizadas')
        self.assertTrue(all(a.estado == Actividad.REALIZADO for a in realizadas))
        r, _ = self.compromisos(plazo='vencidas')
        self.assertEqual(r.context['vencidas'], len(vencidas))

    def test_filtro_por_sector_responsable_estado_y_fechas(self):
        """PK-03 · Filtros combinados: sector (o sin sector), responsable, estado y rango de fechas"""
        self.entrar('arojas')
        sector = Sector.objects.filter(delegacion=self.rural, actividades__fecha_compromiso__isnull=False).first()
        _, filas = self.compromisos(sector=sector.pk)
        self.assertTrue(filas)
        self.assertEqual({a.sector_id for a in filas}, {sector.pk})
        _, sin = self.compromisos(sector='ninguno')
        self.assertTrue(all(a.sector_id is None for a in sin))
        bruno = self.usuario('bcastillo')
        _, filas = self.compromisos(funcionario=bruno.pk, estado=Actividad.PENDIENTE)
        self.assertTrue(all(a.funcionario_id == bruno.pk and a.estado == Actividad.PENDIENTE for a in filas))
        desde, hasta = HOY - timedelta(days=10), HOY
        _, filas = self.compromisos(desde=desde.isoformat(), hasta=hasta.isoformat())
        self.assertTrue(all(desde <= a.fecha_compromiso <= hasta for a in filas))
        _, todas = self.compromisos(desde='no-es-fecha')                  # una fecha inválida se ignora
        self.assertEqual(len(todas), len(self.compromisos()[1]))

    def test_funcionario_solo_ve_lo_suyo(self):
        """PK-04 · El funcionario ve solo sus compromisos aunque pida los de otro responsable en la URL"""
        self.entrar('bcastillo')
        otro = self.usuario('cvega')
        r, filas = self.compromisos(funcionario=otro.pk)
        self.assertTrue(filas)
        self.assertEqual({a.funcionario.nombre_usuario for a in filas}, {'bcastillo'})
        self.assertFalse(r.context['integrantes'])

    def test_busqueda_por_folio_y_tablero(self):
        """PK-05 · Se busca por folio, y la vista tablero reparte el mismo total en sus 4 columnas"""
        self.entrar('arojas')
        objetivo = Actividad.objects.filter(delegacion=self.rural, fecha_compromiso__isnull=False).first()
        _, filas = self.compromisos(q=objetivo.folio)
        self.assertEqual([a.pk for a in filas], [objetivo.pk])
        r = self.client.get(reverse('agenda'), {'vista': 'tablero'})
        self.assertEqual(sum(c['total'] for c in r.context['columnas']), r.context['total'])
        self.assertEqual([c['codigo'] for c in r.context['columnas']], [e for e, _ in Actividad.ESTADOS])

    def test_exportacion_respeta_filtros(self):
        """PK-06 · El Excel trae las mismas filas que la tabla filtrada, con sector y plazo, y queda auditado"""
        self.entrar('arojas')
        _, vencidas = self.compromisos(plazo='vencidas')
        r = self.client.get(reverse('agenda_exportar'), {'plazo': 'vencidas'})
        self.assertEqual(r.status_code, 200)
        filas = filas_excel(r)
        encabezado = next(f for f in filas if f and f[0] == 'Folio')
        self.assertIn('Sector', encabezado)
        self.assertIn('Plazo', encabezado)
        datos = [f for f in filas[filas.index(encabezado) + 1:] if f and f[0]]
        self.assertEqual(len(datos), len(vencidas))
        self.assertTrue(all('atraso' in str(f[encabezado.index('Plazo')]) for f in datos))
        self.assertTrue(Auditoria.objects.filter(evento='EXPORTACION', entidad='agenda').exists())


# ---------------------------------------------------------------------------
# PG · Organizaciones: encargados municipales y sector; catálogo de sectores
# ---------------------------------------------------------------------------
class EncargadosYSectorTests(BaseMatriz):

    def datos_org(self, **cambios):
        sector = Sector.objects.get(delegacion=self.rural, nombre='Las Rojas')
        datos = {
            'nombre': 'Junta de vecinos prueba', 'tipo': TipoOrganizacion.objects.get(codigo='TO01').pk,
            'delegacion': self.rural.pk, 'sector': sector.pk, 'domicilio': 'Calle 1', 'socios': 40,
            'registro_pj': 7701, 'observacion': '', 'activo': 'on',
            'encargado_1': self.usuario('bcastillo').pk, 'encargado_2': self.usuario('cvega').pk,
            'encargado_3': self.usuario('gsoto').pk,
        }
        datos.update(cambios)
        return datos

    def encargados(self, registro=7701):
        return list(EncargadoOrganizacion.objects.filter(organizacion__registro_pj=registro)
                    .order_by('orden').values_list('orden', 'usuario__nombre_usuario'))

    def test_crear_con_tres_encargados(self):
        """PG-01 · Se registra la organización con 3 funcionarios encargados, en orden; la ficha los muestra"""
        self.entrar('arojas')
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org())
        org = Organizacion.objects.get(registro_pj=7701)
        self.assertRedirects(r, reverse('organizaciones_ver', args=[org.pk]))
        self.assertEqual(self.encargados(), [(1, 'bcastillo'), (2, 'cvega'), (3, 'gsoto')])
        self.assertEqual(org.territorio, 'Rural · sector Las Rojas')
        r = self.client.get(reverse('organizaciones_ver', args=[org.pk]))
        self.assertContains(r, 'Encargados municipales')
        self.assertContains(r, self.usuario('cvega').nombre)
        self.assertContains(r, self.usuario('bcastillo').cargo.nombre)
        r = self.client.get(reverse('usuarios_ver', args=[self.usuario('bcastillo').pk]))
        self.assertContains(r, 'Organizaciones a cargo')
        self.assertContains(r, 'JUNTA DE VECINOS PRUEBA')

    def test_reglas_de_los_encargados(self):
        """PG-02 · Solo funcionarios de la delegación, sin repetir; sin delegación no se asignan"""
        self.entrar('arojas')
        ajeno = self.usuario('mtapia')                                  # delegado de Centro
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org(encargado_2=ajeno.pk))
        self.assertIn('encargado_2', r.context['form'].errors)
        r = self.client.post(reverse('organizaciones_crear'),
                             self.datos_org(encargado_3=self.usuario('bcastillo').pk))
        self.assertIn('encargado_3', r.context['form'].errors)
        self.assertFalse(Organizacion.objects.filter(registro_pj=7701).exists())
        self.entrar('emunoz')                                          # global: puede dejar la delegación vacía
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org(delegacion='', sector=''))
        self.assertIn('encargado_1', r.context['form'].errors)
        opciones = r.context['form'].fields['encargado_1'].queryset
        self.assertFalse(opciones.filter(cargo__isnull=True).exists())  # sin cargo no son encargados

    def test_editar_reordena_y_quita(self):
        """PG-03 · Al editar, los puestos quedan correlativos y se pueden quitar todos (hasta 3, no obligatorios)"""
        self.entrar('arojas')
        self.client.post(reverse('organizaciones_crear'), self.datos_org())
        org = Organizacion.objects.get(registro_pj=7701)
        self.client.post(reverse('organizaciones_editar', args=[org.pk]),
                         self.datos_org(encargado_1='', encargado_3=''))
        self.assertEqual(self.encargados(), [(1, 'cvega')])
        self.assertEqual(Organizacion.objects.get(pk=org.pk).encargados_resumen, '1 de 3')
        self.client.post(reverse('organizaciones_editar', args=[org.pk]),
                         self.datos_org(encargado_1='', encargado_2='', encargado_3=''))
        self.assertEqual(self.encargados(), [])
        self.assertEqual(Organizacion.objects.get(pk=org.pk).encargados_resumen, 'Sin asignar')

    def test_sector_debe_ser_de_la_delegacion(self):
        """PG-04 · Un sector de otra delegación se rechaza aunque se envíe a mano"""
        self.entrar('emunoz')
        ajeno = Sector.objects.get(nombre='Toqui')                   # Las Compañías
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org(sector=ajeno.pk))
        self.assertIn('sector', r.context['form'].errors)

    def test_listado_busqueda_y_exportacion(self):
        """PG-05 · El listado muestra encargados y puestos; se busca por encargado, se filtra «a mi cargo» y el
        Excel trae sector y los 3 puestos"""
        self.entrar('arojas')
        self.client.post(reverse('organizaciones_crear'), self.datos_org(registro_pj=7702, nombre='ORG EXCLUSIVA',
                                                                        encargado_2='', encargado_3=''))
        castillo = self.usuario('bcastillo')
        r = self.client.get(reverse('organizaciones_lista'), {'q': 'ORG EXCLUSIVA'})
        self.assertContains(r, '1 de 3')
        self.assertContains(r, castillo.nombre)
        r = self.client.get(reverse('organizaciones_lista'), {'q': castillo.nombre})
        self.assertIn(7702, [f['obj'].registro_pj for f in r.context['filas']])
        filas = filas_excel(self.client.get(reverse('organizaciones_exportar'), {'q': 'ORG EXCLUSIVA'}))
        encabezado = next(f for f in filas if f and f[0] == 'Organización')
        for columna in ('Sector', 'Encargado 1', 'Encargado 2', 'Encargado 3'):
            self.assertIn(columna, encabezado)
        fila = filas[filas.index(encabezado) + 1]
        self.assertEqual(fila[encabezado.index('Sector')], 'Las Rojas')
        self.assertEqual(fila[encabezado.index('Encargado 1')], castillo.nombre)
        self.entrar('bcastillo')
        r = self.client.get(reverse('organizaciones_lista'), {'a_cargo': 'mias'})
        self.assertTrue(r.context['filas'])
        self.assertTrue(all(castillo in f['obj'].lista_encargados for f in r.context['filas']))

    def test_ficha_con_fechas_responde(self):
        """PG-06 · La ficha de una organización con fecha de constitución se muestra (antes fallaba con error 500)"""
        self.entrar('arojas')
        org = Organizacion.objects.filter(delegacion=self.rural, fecha_constitucion__isnull=False).first()
        r = self.client.get(reverse('organizaciones_ver', args=[org.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, org.fecha_constitucion.strftime('%d-%m-%Y'))

    def test_catalogo_de_sectores(self):
        """PG-07 · Sectores: el delegado crea en su delegación; el nombre no se repite en la misma; otra delegación sí"""
        self.entrar('arojas')
        r = self.client.post(reverse('sectores_crear'), {'codigo': 'SEC050', 'nombre': 'Villa Prueba',
                                                         'delegacion': self.rural.pk, 'activo': 'on'})
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('sectores_crear'), {'codigo': 'SEC051', 'nombre': 'villa prueba',
                                                         'delegacion': self.rural.pk, 'activo': 'on'})
        self.assertIn('nombre', r.context['form'].errors)
        centro = Delegacion.objects.get(codigo='DEL01')               # no autorizada para arojas
        r = self.client.post(reverse('sectores_crear'), {'codigo': 'SEC052', 'nombre': 'Otro',
                                                         'delegacion': centro.pk, 'activo': 'on'})
        self.assertIn('delegacion', r.context['form'].errors)
        self.entrar('emunoz')
        r = self.client.post(reverse('sectores_crear'), {'codigo': 'SEC053', 'nombre': 'Villa Prueba',
                                                         'delegacion': centro.pk, 'activo': 'on'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Sector.objects.filter(nombre='Villa Prueba').count(), 2)

    def test_sector_en_uso_no_se_elimina(self):
        """PG-08 · Un sector con organizaciones no se elimina, y el funcionario no administra sectores (403)"""
        self.entrar('emunoz')
        sector = Sector.objects.filter(organizaciones__isnull=False).first()
        self.client.post(reverse('sectores_eliminar', args=[sector.pk]))
        self.assertTrue(Sector.objects.filter(pk=sector.pk).exists())
        self.entrar('bcastillo')
        self.assertEqual(self.client.get(reverse('sectores_lista')).status_code, 403)

    def test_actividad_con_sector(self):
        """PG-09 · La actividad guarda el sector de su territorio, hereda el de la organización y rechaza uno ajeno"""
        self.entrar('ftest')
        islon = Sector.objects.get(delegacion=self.rural, nombre='Islón')
        self.client.post(reverse('actividad_nueva'), self.datos(sector=islon.pk, territorio='Pasaje 3'))
        actividad = Actividad.objects.filter(funcionario=self.nueva).latest('pk')
        self.assertEqual((actividad.sector, actividad.lugar), (islon, 'Rural · sector Islón · Pasaje 3'))
        org = Organizacion.objects.filter(delegacion=self.rural, sector__isnull=False).first()
        self.client.post(reverse('actividad_nueva'), self.datos(organizacion=org.pk, territorio=''))
        self.assertEqual(Actividad.objects.filter(funcionario=self.nueva).latest('pk').sector, org.sector)
        antes = Actividad.objects.filter(funcionario=self.nueva).count()
        r = self.client.post(reverse('actividad_nueva'), self.datos(sector=Sector.objects.get(nombre='Toqui').pk))
        self.assertIn('sector', r.context['form'].errors)
        self.assertEqual(Actividad.objects.filter(funcionario=self.nueva).count(), antes)

    def test_importacion_deduce_sector_por_nombre(self):
        """PG-10 · Al importar la base, el sector se deduce del nombre cuando coincide con uno del territorio"""
        libro = Workbook()
        hoja = libro.active
        hoja.append(['ORGANIZACIONES', 'DOMICILIO', 'TERRIT. DELEG.', 'SOCIOS', 'FECHA', 'REG', 'INSC', 'DIR'])
        hoja.append(['JUNTA DE VECINOS LA FLORIDA ORIENTE', 'CALLE', 'ANTENA', 20, None, 9301, None, None])
        hoja.append(['CLUB DEPORTIVO TOQUI', 'CALLE', 'CIAS', 20, None, 9302, None, None])
        hoja.append(['CLUB DEPORTIVO TOQUI', 'CALLE', 'CENTRO', 20, None, 9303, None, None])
        ruta = tempfile.mktemp(suffix='.xlsx', dir=ARCHIVOS)
        libro.save(ruta)
        r = importar(ruta)
        self.assertEqual(r.con_sector, 2)
        self.assertEqual(Organizacion.objects.get(registro_pj=9301).sector.nombre, 'La Florida')
        self.assertEqual(Organizacion.objects.get(registro_pj=9302).sector.nombre, 'Toqui')
        self.assertIsNone(Organizacion.objects.get(registro_pj=9303).sector)   # Toqui no es de Centro

    def test_base_de_datos_limita_a_tres(self):
        """PG-11 · La base de datos impide un 4.º encargado y repetir a un funcionario en la misma organización"""
        org = Organizacion.objects.filter(delegacion=self.rural).first()
        org.encargos.all().delete()
        for n, usuario in enumerate(('bcastillo', 'cvega', 'gsoto'), start=1):
            EncargadoOrganizacion.objects.create(organizacion=org, usuario=self.usuario(usuario), orden=n)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EncargadoOrganizacion.objects.create(organizacion=org, usuario=self.usuario('nperez'), orden=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EncargadoOrganizacion.objects.create(organizacion=org, usuario=self.usuario('bcastillo'), orden=2)

    def test_sin_la_delegacion_deja_de_ser_encargado(self):
        """PG-12 · Si al funcionario le quitan la delegación, deja de ser encargado de sus organizaciones"""
        org = Organizacion.objects.filter(delegacion=self.rural).first()
        nperez = self.usuario('nperez')
        org.encargos.all().delete()
        EncargadoOrganizacion.objects.create(organizacion=org, usuario=nperez, orden=1)
        self.entrar('admin')
        centro = Delegacion.objects.get(codigo='DEL01')
        self.client.post(reverse('usuarios_editar', args=[nperez.pk]), {
            'nombre': nperez.nombre, 'nombre_usuario': nperez.nombre_usuario, 'correo': nperez.correo,
            'rol': nperez.rol_id, 'cargo': nperez.cargo_id, 'delegaciones': [centro.pk], 'is_active': 'on'})
        self.assertFalse(EncargadoOrganizacion.objects.filter(organizacion=org, usuario=nperez).exists())

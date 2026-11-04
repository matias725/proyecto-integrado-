"""
Pruebas de la matriz SGR y de las 10 reglas del nuevo requerimiento.

Prefijos (ver docs/pruebas/plan_de_pruebas_ev2.md):
    RG  reglas de negocio del requerimiento (incluye casos de borde)
    PM  cálculo de la matriz: metas, topes, semáforo, equipo
    PV  validación, ausencias, felicitaciones y control de acceso por objeto
    PE  evidencias y archivos
    PO  organizaciones e importación de la base JJVV
    PF  rendimiento (consultas por pantalla)

La fecha de trabajo se fija en el miércoles 04-11-2026 (SGR_FECHA_HOY) para que los
bordes de semana y de período sean reproducibles.
"""

import tempfile
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from openpyxl import Workbook

from catalogos.models import Cargo, Delegacion, ItemMedicion
from cuentas.models import Rol, Usuario
from gestion import calculos
from gestion.importacion import importar, subfamilia
from gestion.models import (Actividad, Ausencia, Evidencia, MetaCargo, Observacion, Organizacion, Periodo)
from gestion.reglas import (evaluar_puntaje, fecha_minima_de_ingreso, normalizar_telefono, ultimo_dia_de_ingreso)

from .base import PruebaSGR

HOY = date(2026, 11, 4)            # miércoles
PDF = b'%PDF-1.4\n%prueba\n%%EOF\n'
PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
ARCHIVOS = tempfile.mkdtemp(prefix='sgr-pruebas-')


@override_settings(SGR_FECHA_HOY=HOY, MEDIA_ROOT=ARCHIVOS)
class BaseMatriz(PruebaSGR):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.periodo = Periodo.objects.get(estado=Periodo.ABIERTO)
        cls.rural = Delegacion.objects.get(codigo='DEL06')
        cls.gestor = Cargo.objects.get(codigo='CAR02')
        # Funcionaria sin actividades de demostración: los conteos quedan bajo control de cada prueba
        cls.nueva = Usuario.objects.create_user('ftest', 'ftest@example.test', cls.clave, nombre='Fernanda Test',
                                                rol=Rol.objects.get(codigo='ROL04'), cargo=cls.gestor)
        cls.nueva.delegaciones.set([cls.rural])
        cls.item = ItemMedicion.objects.get(codigo='IT010')   # atención social presencial: meta 90, pondera 20 %

    def entrar(self, usuario, clave=None, delegacion='DEL06'):
        """Cierra la sesión anterior, ingresa y deja activa la delegación Rural si el usuario la tiene."""
        self.client.logout()
        respuesta = super().entrar(usuario, clave)
        destino = Delegacion.objects.get(codigo=delegacion)
        self.client.post(reverse('cambiar_delegacion'), {'delegacion': destino.pk, 'siguiente': '/inicio/'})
        return respuesta

    def datos(self, **cambios):
        datos = {
            'token_envio': str(uuid.uuid4()), 'fecha': HOY.isoformat(), 'item': self.item.pk,
            'naturaleza': Actividad.ACCION, 'origen': Actividad.INTERNA, 'titulo': 'Atención social',
            'descripcion': 'Se atiende a la vecina y se registra su solicitud.', 'solicitante_nombre': 'María Pérez',
            'solicitante_telefono': '912345678', 'territorio': 'Las Rojas', 'estado': Actividad.REALIZADO,
        }
        datos.update(cambios)
        return {k: v for k, v in datos.items() if v is not None}

    def actividad(self, funcionario=None, **campos):
        """Actividad creada directo en la base (para preparar escenarios de cálculo)."""
        valores = dict(periodo=self.periodo, delegacion=self.rural, funcionario=funcionario or self.nueva,
                       item=self.item, fecha=HOY, titulo='Atención', descripcion='Detalle de la atención',
                       solicitante_nombre='Vecina', solicitante_telefono='+56 9 1234 5678',
                       estado=Actividad.REALIZADO, ingresada_el=HOY)
        valores.update(campos)
        a = Actividad(**valores)
        a.puntua, a.motivo_sin_puntaje = evaluar_puntaje(a)
        a.save()
        return a

    def ficha(self, funcionario=None):
        funcionario = funcionario or Usuario.objects.select_related('cargo').get(pk=self.nueva.pk)
        return calculos.indicadores(self.periodo, [funcionario])['fichas'][0]


# ---------------------------------------------------------------------------
# RG · Reglas del nuevo requerimiento
# ---------------------------------------------------------------------------
class ReglasTests(BaseMatriz):

    def setUp(self):
        self.entrar('ftest')

    def test_regla1_delegado_es_otra_gestion(self):
        """RG-01 · Regla 1: si el solicitante es el delegado, se guarda como otra gestión sin puntaje"""
        r = self.client.post(reverse('actividad_nueva'), self.datos(solicitante_es_delegado='on'))
        self.assertEqual(r.status_code, 302)
        a = Actividad.objects.get(funcionario=self.nueva)
        self.assertFalse(a.puntua)
        self.assertIn('regla 1', a.motivo_sin_puntaje)

    def test_regla2_sin_telefono_no_suma(self):
        """RG-02 · Regla 2: sin teléfono del usuario la actividad se registra pero no suma"""
        self.client.post(reverse('actividad_nueva'), self.datos(solicitante_telefono=''))
        a = Actividad.objects.get(funcionario=self.nueva)
        self.assertFalse(a.puntua)
        self.assertIn('regla 2', a.motivo_sin_puntaje)

    def test_regla2_sin_nombre_no_suma(self):
        """RG-03 · Regla 2: sin nombre del usuario no suma"""
        self.client.post(reverse('actividad_nueva'), self.datos(solicitante_nombre=''))
        self.assertFalse(Actividad.objects.get(funcionario=self.nueva).puntua)

    def test_regla2_telefono_invalido_se_rechaza(self):
        """RG-04 · Un teléfono que no es chileno de 9 dígitos se rechaza con mensaje claro"""
        r = self.client.post(reverse('actividad_nueva'), self.datos(solicitante_telefono='12345'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'teléfono chileno de 9 dígitos')
        self.assertFalse(Actividad.objects.filter(funcionario=self.nueva).exists())

    def test_regla2_telefono_se_normaliza(self):
        """RG-05 · Borde: móvil sin prefijo, con +56 y fijo de La Serena se normalizan igual"""
        self.assertEqual(normalizar_telefono('912345678'), '+56 9 1234 5678')
        self.assertEqual(normalizar_telefono('+56 9 1234 5678'), '+56 9 1234 5678')
        self.assertEqual(normalizar_telefono('51 2207884'), '+56 51 2207884')
        self.assertEqual(normalizar_telefono('012345678'), '')
        self.assertEqual(normalizar_telefono('9123'), '')

    def test_regla3_septimo_ingreso_permitido(self):
        """RG-06 · Regla 3 (borde): el 7.º ingreso del día se acepta"""
        for _ in range(6):
            self.actividad()
        r = self.client.post(reverse('actividad_nueva'), self.datos())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Actividad.objects.filter(funcionario=self.nueva, ingresada_el=HOY).count(), 7)

    def test_regla3_octavo_ingreso_rechazado(self):
        """RG-07 · Regla 3 (borde): el 8.º ingreso del día se rechaza y no se guarda"""
        for _ in range(7):
            self.actividad()
        r = self.client.post(reverse('actividad_nueva'), self.datos())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'el máximo diario')
        self.assertEqual(Actividad.objects.filter(funcionario=self.nueva).count(), 7)

    def test_regla3_cupo_es_por_dia_de_ingreso(self):
        """RG-08 · Regla 3: 7 ingresos ayer no impiden ingresar hoy"""
        for _ in range(7):
            self.actividad(ingresada_el=HOY - timedelta(days=1), fecha=HOY - timedelta(days=1))
        r = self.client.post(reverse('actividad_nueva'), self.datos())
        self.assertEqual(r.status_code, 302)

    def test_regla4_semana_actual_se_acepta(self):
        """RG-09 · Regla 4: el lunes de la semana en curso se acepta"""
        r = self.client.post(reverse('actividad_nueva'), self.datos(fecha='2026-11-02'))
        self.assertEqual(r.status_code, 302)

    def test_regla4_semana_anterior_cerrada_desde_martes(self):
        """RG-10 · Regla 4 (borde): el miércoles ya no se ingresa el domingo anterior"""
        r = self.client.post(reverse('actividad_nueva'), self.datos(fecha='2026-11-01'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'ya está cerrada')

    def test_regla4_lunes_aun_acepta_semana_anterior(self):
        """RG-11 · Regla 4 (borde): el lunes 09-11 aún se ingresa el viernes 06-11; el martes 10-11 ya no"""
        self.assertEqual(ultimo_dia_de_ingreso(date(2026, 11, 6)), date(2026, 11, 9))
        self.assertEqual(fecha_minima_de_ingreso(date(2026, 11, 9)), date(2026, 11, 2))
        with override_settings(SGR_FECHA_HOY=date(2026, 11, 9)):
            r = self.client.post(reverse('actividad_nueva'), self.datos(fecha='2026-11-06'))
            self.assertEqual(r.status_code, 302)
        with override_settings(SGR_FECHA_HOY=date(2026, 11, 10)):
            r = self.client.post(reverse('actividad_nueva'), self.datos(fecha='2026-11-06'))
            self.assertContains(r, 'ya está cerrada')

    def test_regla4_fecha_futura_rechazada(self):
        """RG-12 · Una fecha posterior a hoy se rechaza"""
        r = self.client.post(reverse('actividad_nueva'), self.datos(fecha='2026-11-05'))
        self.assertContains(r, 'posterior a hoy')

    def test_regla5_gestion_previa_no_suma(self):
        """RG-13 · Regla 5: una coordinación o correo (gestión previa) no da punto"""
        self.client.post(reverse('actividad_nueva'), self.datos(naturaleza=Actividad.GESTION))
        a = Actividad.objects.get(funcionario=self.nueva)
        self.assertFalse(a.puntua)
        self.assertIn('regla 5', a.motivo_sin_puntaje)

    def test_regla5_punto_al_realizar(self):
        """RG-14 · Regla 5: una solicitud pendiente suma solo cuando pasa a «Realizado»"""
        a = self.actividad(estado=Actividad.PENDIENTE, fecha_compromiso=HOY + timedelta(days=5))
        self.assertEqual(self.ficha()['filas'][0]['avance'], 0)
        r = self.client.post(reverse('actividad_estado', args=[a.pk]),
                             {'estado': Actividad.REALIZADO, 'observacion': 'Se entregó la ayuda'})
        self.assertEqual(r.status_code, 302)
        a.refresh_from_db()
        self.assertEqual(a.fecha_cierre, HOY)
        fila = next(f for f in self.ficha()['filas'] if f['codigo'] == 'IT010')
        self.assertEqual(fila['avance'], 1)
        self.assertEqual(a.historial.count(), 1)

    def test_doble_envio_no_duplica(self):
        """RG-15 · Un segundo envío del mismo formulario no crea un duplicado ni consume cupo"""
        datos = self.datos()
        self.client.post(reverse('actividad_nueva'), datos)
        r = self.client.post(reverse('actividad_nueva'), datos)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Actividad.objects.filter(funcionario=self.nueva).count(), 1)

    def test_responsable_y_delegacion_los_asigna_el_servidor(self):
        """RG-16 · Responsable, delegación y día de ingreso no se pueden alterar desde el formulario"""
        otro = Usuario.objects.get(nombre_usuario='bcastillo')
        self.client.post(reverse('actividad_nueva'), self.datos(funcionario=otro.pk, delegacion=1,
                                                                ingresada_el='2026-01-01'))
        a = Actividad.objects.get(funcionario=self.nueva)
        self.assertEqual((a.delegacion, a.ingresada_el), (self.rural, HOY))

    def test_compromiso_obligatorio_si_queda_pendiente(self):
        """RG-17 · Una solicitud que no queda realizada necesita fecha de compromiso"""
        r = self.client.post(reverse('actividad_nueva'), self.datos(estado=Actividad.PENDIENTE))
        self.assertContains(r, 'necesita fecha de compromiso')


# ---------------------------------------------------------------------------
# PM · Cálculo de la matriz
# ---------------------------------------------------------------------------
class CalculoTests(BaseMatriz):

    def test_cumplimiento_y_ponderado(self):
        """PM-01 · 45 de 90 atenciones = 50 % del ítem y 10 puntos ponderados (pondera 20 %)"""
        Actividad.objects.bulk_create([Actividad(
            periodo=self.periodo, delegacion=self.rural, funcionario=self.nueva, item=self.item, fecha=HOY,
            titulo='A', descripcion='d', estado=Actividad.REALIZADO, ingresada_el=HOY) for _ in range(45)])
        fila = next(f for f in self.ficha()['filas'] if f['codigo'] == 'IT010')
        self.assertAlmostEqual(fila['cumplimiento'], 50.0)
        self.assertAlmostEqual(fila['ponderado'], 10.0)

    def test_regla7_tope_120_por_item(self):
        """PM-02 · Regla 7: 200 atenciones (222 %) aportan como máximo 120 % del ítem"""
        Actividad.objects.bulk_create([Actividad(
            periodo=self.periodo, delegacion=self.rural, funcionario=self.nueva, item=self.item, fecha=HOY,
            titulo='A', descripcion='d', estado=Actividad.REALIZADO, ingresada_el=HOY) for _ in range(200)])
        fila = next(f for f in self.ficha()['filas'] if f['codigo'] == 'IT010')
        self.assertTrue(fila['topado'])
        self.assertAlmostEqual(fila['cumplimiento'], 120.0)
        self.assertAlmostEqual(fila['ponderado'], 24.0)

    def test_regla7_borde_exacto(self):
        """PM-03 · Borde: exactamente 120 % no se marca como topado"""
        MetaCargo.objects.filter(periodo=self.periodo, cargo=self.gestor, item=self.item).update(meta=10)
        for _ in range(12):
            self.actividad()
        fila = next(f for f in self.ficha()['filas'] if f['codigo'] == 'IT010')
        self.assertAlmostEqual(fila['cumplimiento'], 120.0)
        self.assertFalse(fila['topado'])

    def test_actividad_sin_puntaje_o_rechazada_no_cuenta(self):
        """PM-04 · No cuentan: sin teléfono, gestión previa, del delegado, rechazada o pendiente"""
        self.actividad(solicitante_telefono='')
        self.actividad(naturaleza=Actividad.GESTION)
        self.actividad(solicitante_es_delegado=True)
        self.actividad(validacion=Actividad.RECHAZADA)
        self.actividad(estado=Actividad.EN_PROCESO, fecha_compromiso=HOY)
        self.actividad()                                    # la única que suma
        fila = next(f for f in self.ficha()['filas'] if f['codigo'] == 'IT010')
        self.assertEqual(fila['avance'], 1)

    def test_item_tubo_es_proporcion(self):
        """PM-05 · Ítem TUBO: 3 de 4 solicitudes resueltas = 75 % frente a meta 80 %"""
        for estado in [Actividad.REALIZADO] * 3 + [Actividad.PENDIENTE]:
            self.actividad(estado=estado, fecha_compromiso=HOY + timedelta(days=3))
        fila = next(f for f in self.ficha()['filas'] if f['codigo'] == 'IT009')
        self.assertAlmostEqual(fila['avance'], 75.0)
        self.assertAlmostEqual(fila['cumplimiento'], 75 / 80 * 100)

    def test_regla9_ausencia_ajusta_meta(self):
        """PM-06 · Regla 9: 23 días de ausencia en un trimestre de 92 reducen la meta de 90 a 67,5"""
        Ausencia.objects.create(periodo=self.periodo, funcionario=self.nueva, tipo=Ausencia.LICENCIA,
                                desde=date(2026, 10, 1), hasta=date(2026, 10, 23),
                                registrada_por=self.usuario('arojas'))
        ficha = self.ficha()
        fila = next(f for f in ficha['filas'] if f['codigo'] == 'IT010')
        self.assertEqual(ficha['dias_ausencia'], 23)
        self.assertAlmostEqual(fila['meta_ajustada'], 90 * 69 / 92)

    def test_regla9_ausencia_fuera_del_periodo_no_cuenta(self):
        """PM-07 · Borde: solo cuentan los días de ausencia dentro del período"""
        Ausencia.objects.create(periodo=self.periodo, funcionario=self.nueva, tipo=Ausencia.VACACIONES,
                                desde=date(2026, 9, 25), hasta=date(2026, 10, 2),
                                registrada_por=self.usuario('arojas'))
        self.assertEqual(self.ficha()['dias_ausencia'], 2)

    def test_felicitaciones_suman_con_maximo_y_reclamos_descuentan(self):
        """PM-08 · Felicitaciones +10 % (máximo 3) y reclamos −20 %"""
        jefa = self.usuario('arojas')
        for tipo in [Observacion.FELICITACION] * 4 + [Observacion.RECLAMO]:
            Observacion.objects.create(periodo=self.periodo, tipo=tipo, funcionario=self.nueva, fecha=HOY,
                                       medio=Observacion.CORREO, remitente='Vecina', descripcion='x',
                                       respaldo='observacion/x.pdf', respaldo_nombre='x.pdf', registrada_por=jefa)
        ficha = self.ficha()
        self.assertEqual(ficha['felicitaciones_validas'], 3)
        self.assertEqual(ficha['ajuste'], 3 * 10 - 20)
        self.assertAlmostEqual(ficha['total'], 10.0)

    def test_total_no_es_negativo_ni_supera_tope(self):
        """PM-09 · Borde: el total queda entre 0 y el tope total del período (150 %)"""
        jefa = self.usuario('arojas')
        Observacion.objects.create(periodo=self.periodo, tipo=Observacion.RECLAMO, funcionario=self.nueva,
                                   fecha=HOY, medio=Observacion.LIBRO, remitente='Vecino', descripcion='x',
                                   respaldo='observacion/x.pdf', respaldo_nombre='x.pdf', registrada_por=jefa)
        self.assertEqual(self.ficha()['total'], 0.0)

    def test_semaforo(self):
        """PM-10 · Semáforo: verde ≥ esperado; naranjo ≥ 60 % de lo esperado; rojo bajo eso"""
        self.assertEqual(calculos.semaforo(40, 38, self.periodo), 'verde')
        self.assertEqual(calculos.semaforo(23, 38, self.periodo), 'ambar')
        self.assertEqual(calculos.semaforo(22, 38, self.periodo), 'rojo')

    def test_esperado_al_dia(self):
        """PM-11 · 04-11-2026 es el día 35 de 92 del cuarto trimestre: 38,04 % esperado"""
        self.assertEqual(calculos.dias_transcurridos(self.periodo), 35)
        self.assertAlmostEqual(calculos.esperado_al_dia(self.periodo), 35 / 92 * 100)

    def test_regla10_resultado_de_equipo(self):
        """PM-12 · Regla 10: el resultado del equipo es el promedio de quienes tienen metas"""
        integrantes = list(Usuario.objects.filter(delegaciones=self.rural, is_active=True).select_related('cargo'))
        r = calculos.indicadores(self.periodo, integrantes)
        equipo = calculos.resultado_equipo(r['fichas'], r['esperado'], self.periodo)
        con_metas = [f for f in r['fichas'] if not f['sin_metas']]
        self.assertAlmostEqual(equipo['promedio'], sum(f['total'] for f in con_metas) / len(con_metas))
        self.assertTrue(any(f['sin_metas'] for f in r['fichas']))       # la delegada no tiene metas

    def test_regla6_alerta_tope_diario(self):
        """PM-13 · Regla 6: llegar al tope diario genera una alerta de calidad para el delegado"""
        for _ in range(7):
            self.actividad()
        alertas = calculos.alertas_de_registro(self.periodo, self.rural)
        self.assertTrue(any(a['tipo'] == 'Tope diario' and a['funcionario'] == 'Fernanda Test' for a in alertas))

    def test_metas_de_la_matriz_suman_100(self):
        """PM-14 · Las metas cargadas desde la matriz suman 100 % por cargo"""
        for cargo in Cargo.objects.filter(metas__periodo=self.periodo).distinct():
            suma = sum(m.ponderador for m in MetaCargo.objects.filter(periodo=self.periodo, cargo=cargo))
            self.assertEqual(suma, Decimal('100'), cargo)

    def test_meta_que_excede_100_se_rechaza(self):
        """PM-15 · Agregar un ítem que haga superar 100 % al cargo se rechaza"""
        self.entrar('emunoz')
        r = self.client.post(reverse('metas'), {'cargo': self.gestor.pk, 'item': ItemMedicion.objects.get(
            codigo='IT001').pk, 'meta': 10, 'ponderador': 5})
        self.assertContains(r, 'sumarían más de 100')

    def test_tablero_y_informe_muestran_ficha(self):
        """PM-16 · El tablero muestra la ficha propia y el informe exporta la matriz a Excel"""
        self.actividad()
        self.entrar('ftest')
        r = self.client.get(reverse('tablero'))
        self.assertEqual(r.context['ficha']['funcionario'], self.nueva)
        self.entrar('arojas')
        r = self.client.get(reverse('informes_exportar'))
        self.assertEqual(r['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ---------------------------------------------------------------------------
# PV · Validación, ausencias, felicitaciones y acceso por objeto
# ---------------------------------------------------------------------------
class ValidacionYAccesoTests(BaseMatriz):

    def test_delegado_valida_y_rechaza(self):
        """PV-01 · El delegado valida; un rechazo exige motivo y deja de sumar"""
        a = self.actividad()
        self.entrar('arojas')
        r = self.client.post(reverse('validar', args=[a.pk]), {'decision': Actividad.RECHAZADA, 'motivo': ''})
        a.refresh_from_db()
        self.assertEqual(a.validacion, Actividad.VALIDACION_PENDIENTE)
        self.client.post(reverse('validar', args=[a.pk]), {'decision': Actividad.RECHAZADA,
                                                           'motivo': 'No corresponde al ítem'})
        a.refresh_from_db()
        self.assertEqual((a.validacion, a.validada_por.nombre_usuario), (Actividad.RECHAZADA, 'arojas'))
        self.assertEqual(next(f for f in self.ficha()['filas'] if f['codigo'] == 'IT010')['avance'], 0)

    def test_nadie_valida_lo_propio(self):
        """PV-02 · El delegado no puede validar una actividad propia (403)"""
        jefa = self.usuario('arojas')
        a = self.actividad(funcionario=jefa)
        self.entrar('arojas')
        r = self.client.post(reverse('validar', args=[a.pk]), {'decision': Actividad.VALIDADA})
        self.assertEqual(r.status_code, 403)

    def test_funcionario_no_valida(self):
        """PV-03 · Un funcionario no puede validar (403)"""
        a = self.actividad(funcionario=self.usuario('bcastillo'))
        self.entrar('ftest')
        self.assertEqual(self.client.post(reverse('validar', args=[a.pk]),
                                          {'decision': Actividad.VALIDADA}).status_code, 403)

    def test_funcionario_no_ve_actividad_ajena(self):
        """PV-04 · Acceso por objeto: un funcionario no abre la actividad de un compañero (403)"""
        a = self.actividad(funcionario=self.usuario('bcastillo'))
        self.entrar('ftest')
        self.assertEqual(self.client.get(reverse('actividad_ver', args=[a.pk])).status_code, 403)

    def test_delegado_de_otra_delegacion_no_ve(self):
        """PV-05 · Un delegado de otra delegación no abre ni valida la actividad (403)"""
        a = self.actividad()
        self.entrar('mtapia')
        self.assertEqual(self.client.get(reverse('actividad_ver', args=[a.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('validar', args=[a.pk]),
                                          {'decision': Actividad.VALIDADA}).status_code, 403)

    def test_funcionario_solo_lista_lo_suyo(self):
        """PV-06 · El listado del funcionario muestra solo sus actividades"""
        self.actividad()
        self.entrar('ftest')
        r = self.client.get(reverse('actividades'))
        self.assertEqual({a.funcionario_id for a in r.context['pagina'].object_list}, {self.nueva.pk})

    def test_regla9_solo_delegado_registra_ausencias(self):
        """PV-07 · Regla 9: el funcionario no puede registrar ausencias (403); el delegado sí"""
        datos = {'funcionario': self.nueva.pk, 'tipo': Ausencia.LICENCIA, 'desde': '2026-10-05',
                 'hasta': '2026-10-09'}
        self.entrar('ftest')
        self.assertEqual(self.client.post(reverse('ausencias'), datos).status_code, 403)
        self.entrar('arojas')
        self.assertEqual(self.client.post(reverse('ausencias'), datos).status_code, 302)
        self.assertEqual(Ausencia.objects.get(funcionario=self.nueva).dias, 5)

    def test_ausencias_superpuestas_se_rechazan(self):
        """PV-08 · Borde: una ausencia que se superpone a otra del mismo funcionario se rechaza"""
        self.entrar('arojas')
        datos = {'funcionario': self.nueva.pk, 'tipo': Ausencia.LICENCIA, 'desde': '2026-10-05',
                 'hasta': '2026-10-09'}
        self.client.post(reverse('ausencias'), datos)
        r = self.client.post(reverse('ausencias'), {**datos, 'desde': '2026-10-09', 'hasta': '2026-10-12'})
        self.assertContains(r, 'Se superpone')

    def test_regla8_felicitacion_requiere_respaldo(self):
        """PV-09 · Regla 8: sin respaldo formal no se registra la felicitación"""
        self.entrar('arojas')
        r = self.client.post(reverse('observaciones'), {
            'tipo': Observacion.FELICITACION, 'funcionario': self.nueva.pk, 'fecha': '2026-11-03',
            'medio': Observacion.CORREO, 'remitente': 'Vecina', 'descripcion': 'Gracias'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Observacion.objects.filter(funcionario=self.nueva).exists())

    def test_regla8_delegado_registra_con_respaldo(self):
        """PV-10 · Regla 8: el delegado registra la felicitación con respaldo PDF y suma al funcionario"""
        self.entrar('arojas')
        r = self.client.post(reverse('observaciones'), {
            'tipo': Observacion.FELICITACION, 'funcionario': self.nueva.pk, 'fecha': '2026-11-03',
            'medio': Observacion.CORREO, 'remitente': 'Vecina', 'descripcion': 'Gracias',
            'respaldo': SimpleUploadedFile('correo.pdf', PDF, 'application/pdf')})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.ficha()['felicitaciones'], 1)

    def test_regla8_funcionario_no_registra_felicitaciones(self):
        """PV-11 · Regla 8: la felicitación no puede venir del funcionario (403)"""
        self.entrar('ftest')
        r = self.client.post(reverse('observaciones'), {'tipo': Observacion.FELICITACION})
        self.assertEqual(r.status_code, 403)

    def test_periodo_cerrado_congela(self):
        """PV-12 · Con el período cerrado no se cambia el estado de sus actividades"""
        a = self.actividad(estado=Actividad.PENDIENTE, fecha_compromiso=HOY)
        Periodo.objects.filter(pk=self.periodo.pk).update(estado=Periodo.CERRADO)
        self.entrar('ftest')
        self.client.post(reverse('actividad_estado', args=[a.pk]),
                         {'estado': Actividad.REALIZADO, 'observacion': 'Cierre tardío'})
        a.refresh_from_db()
        self.assertEqual(a.estado, Actividad.PENDIENTE)

    def test_un_solo_periodo_abierto(self):
        """PV-13 · No se puede abrir un segundo período mientras otro está abierto"""
        cerrado = Periodo.objects.get(estado=Periodo.CERRADO)
        self.entrar('emunoz')
        r = self.client.post(reverse('periodo_estado', args=[cerrado.pk, 'abrir']), follow=True)
        self.assertMensaje(r, 'Ya hay un período abierto')
        self.assertEqual(Periodo.objects.filter(estado=Periodo.ABIERTO).count(), 1)

    def test_base_de_datos_impide_dos_periodos_abiertos(self):
        """PV-16 · Aunque se salte la pantalla, la base de datos rechaza un segundo período abierto"""
        from django.db import IntegrityError, transaction
        cerrado = Periodo.objects.get(estado=Periodo.CERRADO)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Periodo.objects.filter(pk=cerrado.pk).update(estado=Periodo.ABIERTO)

    def test_periodos_superpuestos_se_rechazan(self):
        """PV-14 · Un período que se superpone con otro existente se rechaza"""
        self.entrar('emunoz')
        r = self.client.post(reverse('periodos'), {
            'nombre': 'Prueba', 'inicio': '2026-12-01', 'termino': '2027-02-28', 'tope_item': 120,
            'tope_total': 150, 'bono_felicitacion': 10, 'max_felicitaciones': 3, 'descuento_reclamo': 20,
            'umbral_naranjo': 60, 'cumplimiento_minimo': 80})
        self.assertContains(r, 'Se superpone')

    def test_consultor_no_registra(self):
        """PV-15 · El perfil de consulta no registra actividades (403)"""
        self.entrar('lectura')
        self.assertEqual(self.client.get(reverse('actividad_nueva')).status_code, 403)


# ---------------------------------------------------------------------------
# PE · Evidencias y archivos
# ---------------------------------------------------------------------------
class EvidenciasTests(BaseMatriz):

    def subir(self, nombre, contenido, actividad=None):
        actividad = actividad or self.actividad()
        return self.client.post(reverse('evidencia_subir', args=[actividad.pk]),
                                {'archivo': SimpleUploadedFile(nombre, contenido)}, follow=True), actividad

    def test_sube_png_con_nombre_aleatorio(self):
        """PE-01 · Un PNG válido se guarda con nombre aleatorio (no el original)"""
        self.entrar('ftest')
        _r, a = self.subir('foto ../../x.png', PNG)
        e = Evidencia.objects.get(actividad=a)
        self.assertNotIn('foto', e.archivo.name)
        self.assertEqual(e.tipo_mime, 'image/png')

    def test_rechaza_extension_no_permitida(self):
        """PE-02 · Un ejecutable se rechaza"""
        self.entrar('ftest')
        r, a = self.subir('virus.exe', b'MZ\x90\x00')
        self.assertMensaje(r, 'Formato no permitido')
        self.assertFalse(Evidencia.objects.filter(actividad=a).exists())

    def test_rechaza_contenido_falso(self):
        """PE-03 · Un archivo de texto renombrado a .pdf se rechaza por su contenido"""
        self.entrar('ftest')
        r, a = self.subir('informe.pdf', b'<script>alert(1)</script>')
        self.assertMensaje(r, 'no corresponde a su extensión')

    @override_settings(SGR_EVIDENCIA_MAX_MB=0)
    def test_rechaza_archivo_grande(self):
        """PE-04 · Borde: un archivo sobre el tamaño máximo se rechaza"""
        self.entrar('ftest')
        r, _a = self.subir('grande.pdf', PDF)
        self.assertMensaje(r, 'supera')

    def test_descarga_fuera_de_alcance(self):
        """PE-05 · Un funcionario de otra delegación no descarga la evidencia (403)"""
        self.entrar('ftest')
        _r, a = self.subir('respaldo.pdf', PDF)
        e = Evidencia.objects.get(actividad=a)
        self.assertEqual(self.client.get(reverse('evidencia_descargar', args=[e.pk])).status_code, 200)
        self.entrar('jalvarez')
        self.assertEqual(self.client.get(reverse('evidencia_descargar', args=[e.pk])).status_code, 403)

    def test_no_adjunta_en_actividad_ajena(self):
        """PE-06 · No se adjuntan archivos a actividades de otro funcionario (403)"""
        a = self.actividad(funcionario=self.usuario('bcastillo'))
        self.entrar('ftest')
        r = self.client.post(reverse('evidencia_subir', args=[a.pk]),
                             {'archivo': SimpleUploadedFile('x.pdf', PDF)})
        self.assertEqual(r.status_code, 403)


# ---------------------------------------------------------------------------
# PO · Organizaciones e importación de la base JJVV
# ---------------------------------------------------------------------------
class OrganizacionesTests(BaseMatriz):

    def excel(self, filas):
        libro = Workbook()
        hoja = libro.active
        hoja.append(['ORGANIZACIONES', 'DOMICILIO LEGAL ', 'TERRIT. DELEG.', 'SOCIOS ACTIVOS', 'FECHA CONSTIT.',
                     'Nº REG. P.J.', 'FECHA INSCRIPC EN REG.', 'REG. DIR. Nº'])
        for fila in filas:
            hoja.append(fila)
        ruta = tempfile.mktemp(suffix='.xlsx', dir=ARCHIVOS)
        libro.save(ruta)
        return ruta

    def test_subfamilias(self):
        """PO-01 · Clasificación por subfamilia según el nombre"""
        casos = {'JUNTA DE VECINOS LAS ROJAS': 'TO01', 'CLUB ADULTO MAYOR LOS AÑOS': 'TO02',
                 'CLUB DEPORTIVO EL MILAGRO': 'TO03', 'CENTRO DE MADRES LAS VIOLETAS': 'TO04',
                 'AGRUPACION FOLCLORICA RAICES': 'TO05', 'GRUPO JUVENIL ALBA': 'TO06',
                 'COMITE DE SEGURIDAD VILLA': 'TO07', 'COMITÉ HABITACIONAL ESPERANZA': 'TO08',
                 'UNION COMUNAL DE ADULTOS MAYORES': 'TO10', 'MUJERES EMPRENDEDORAS': 'TO11'}
        for nombre, codigo in casos.items():
            self.assertEqual(subfamilia(nombre), codigo, nombre)

    def test_importacion_con_datos_dudosos(self):
        """PO-02 · Importa, traduce territorios, omite repetidos y anota datos dudosos"""
        ruta = self.excel([
            ['  junta de vecinos   el valle ', 'CALLE 1', 'RURAL', 30, date(2010, 1, 1), 9001, date(2010, 2, 1), 5],
            ['CLUB DEPORTIVO NORTE', 'CALLE 2', 'CIAS', '3 CLUBES', date(2012, 1, 1), 9002, None, None],
            ['AGRUPACION ALFALFARES', '', 'ALFALFARES', 15, date(2026, 5, 30), 9003, date(2026, 6, 8), None],
            ['ORGANIZACION SIN TERRITORIO', 'CALLE 4', None, 10, date(2015, 1, 1), 9004, date(2014, 1, 1), 1],
            ['REPETIDA', 'CALLE 5', 'CENTRO', 5, None, 9001, None, None],
            ['SIN REGISTRO', 'CALLE 6', 'CENTRO', 5, None, None, None, None],
        ])
        r = importar(ruta)
        self.assertEqual((r.leidas, r.creadas, r.omitidas), (6, 4, 2))
        valle = Organizacion.objects.get(registro_pj=9001)
        self.assertEqual((valle.nombre, valle.delegacion.codigo, valle.tipo.codigo, valle.verificada),
                         ('JUNTA DE VECINOS EL VALLE', 'DEL06', 'TO01', False))
        self.assertIn('Socios no numérico', Organizacion.objects.get(registro_pj=9002).observacion)
        self.assertIn('inferido', Organizacion.objects.get(registro_pj=9003).observacion)
        sin = Organizacion.objects.get(registro_pj=9004)
        self.assertIsNone(sin.delegacion)
        self.assertIn('Inscripción anterior', sin.observacion)

    def test_reimportar_no_pisa_verificadas(self):
        """PO-03 · Reimportar actualiza, pero no pisa una organización ya verificada"""
        ruta = self.excel([['ORG UNO', 'CALLE', 'CENTRO', 10, None, 9100, None, None]])
        importar(ruta)
        Organizacion.objects.filter(registro_pj=9100).update(verificada=True, domicilio='CORREGIDO')
        importar(ruta)
        self.assertEqual(Organizacion.objects.get(registro_pj=9100).domicilio, 'CORREGIDO')

    def test_simulacion_no_guarda(self):
        """PO-04 · La importación simulada no guarda nada"""
        antes = Organizacion.objects.count()
        r = importar(self.excel([['ORG DOS', 'CALLE', 'PAMPA', 10, None, 9200, None, None]]), simular=True)
        self.assertEqual((r.creadas, Organizacion.objects.count()), (1, antes))

    def test_delegado_solo_ve_su_territorio(self):
        """PO-05 · Un delegado solo ve organizaciones de sus delegaciones"""
        self.entrar('mtapia')
        r = self.client.get(reverse('organizaciones_lista'))
        self.assertTrue(r.context['filas'])
        self.assertEqual({f['obj'].delegacion.codigo for f in r.context['filas']}, {'DEL01'})

    def test_formulario_actividad_ofrece_organizaciones_del_territorio(self):
        """PO-06 · Al registrar una actividad solo se ofrecen organizaciones de la delegación activa"""
        self.entrar('ftest')
        r = self.client.get(reverse('actividad_nueva'))
        delegaciones = {o.delegacion_id for o in r.context['form'].fields['organizacion'].queryset}
        self.assertEqual(delegaciones, {self.rural.pk})


# ---------------------------------------------------------------------------
# PF · Rendimiento: las pantallas no crecen en consultas con el volumen
# ---------------------------------------------------------------------------
class RendimientoTests(BaseMatriz):

    def test_tablero_consultas_acotadas(self):
        """PF-01 · El tablero usa las mismas consultas con 10 o con 500 actividades (sin N+1)"""
        self.entrar('arojas')
        with CaptureQueriesContext(connection) as pocas:
            self.client.get(reverse('tablero'))
        Actividad.objects.bulk_create([Actividad(
            periodo=self.periodo, delegacion=self.rural, funcionario=self.nueva, item=self.item, fecha=HOY,
            titulo=f'A{n}', descripcion='d', estado=Actividad.REALIZADO, ingresada_el=HOY - timedelta(days=n % 30))
            for n in range(500)])
        with CaptureQueriesContext(connection) as muchas:
            self.client.get(reverse('tablero'))
        self.assertLessEqual(len(muchas), len(pocas) + 2)
        self.assertLess(len(muchas), 60)

"""
TUBO en tarjetas arrastrable (corrección del profesor): mover una solicitud a otra columna cambia su estado.

Prefijo PW. El arrastre en el navegador está en pruebas_ui (UI-22); aquí se prueban las reglas del servidor,
que son las mismas de la ficha de la actividad: solo el responsable o el delegado, período abierto,
fecha de cierre al quedar realizada, historial y auditoría.
"""

from datetime import date, timedelta

from django.urls import reverse

from core.models import Auditoria
from gestion.models import Actividad, HistorialActividad, Periodo

from .test_matriz import HOY, BaseMatriz


class TuboArrastrableTests(BaseMatriz):

    def compromiso(self, **campos):
        valores = dict(estado=Actividad.INGRESADO, fecha_compromiso=HOY + timedelta(days=5), titulo='Solicitud TUBO')
        valores.update(campos)
        return self.actividad(**valores)

    def mover(self, actividad, estado, **extra):
        return self.client.post(reverse('actividad_mover', args=[actividad.pk]), {'estado': estado, **extra},
                                HTTP_ACCEPT='application/json')

    def test_responsable_mueve_su_tarjeta(self):
        """PW-01 · El responsable mueve su solicitud: cambia el estado, queda en el historial y en la auditoría"""
        a = self.compromiso()
        self.entrar('ftest')
        r = self.mover(a, Actividad.EN_PROCESO)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['estado'], Actividad.EN_PROCESO)
        a.refresh_from_db()
        self.assertEqual(a.estado, Actividad.EN_PROCESO)
        self.assertIsNone(a.fecha_cierre)
        h = HistorialActividad.objects.get(actividad=a)
        self.assertEqual((h.estado_anterior, h.estado_nuevo), (Actividad.INGRESADO, Actividad.EN_PROCESO))
        self.assertIn('Movida en el TUBO', h.observacion)
        self.assertTrue(Auditoria.objects.filter(evento='CAMBIO_ESTADO', registro=str(a.pk)).exists())

    def test_realizado_cierra_y_guarda_la_respuesta(self):
        """PW-02 · Al soltar en «Realizado» la solicitud se cierra con la fecha de hoy y guarda la respuesta"""
        a = self.compromiso(estado=Actividad.PENDIENTE, fecha_compromiso=HOY - timedelta(days=2))
        self.assertTrue(a.vencida)
        self.entrar('ftest')
        r = self.mover(a, Actividad.REALIZADO, observacion='Se instaló la luminaria en el pasaje.')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['vencida'])
        a.refresh_from_db()
        self.assertEqual((a.estado, a.fecha_cierre), (Actividad.REALIZADO, HOY))
        self.assertEqual(a.historial.get().observacion, 'Se instaló la luminaria en el pasaje.')
        # Si se devuelve a «Pendiente», se reabre y vuelve a quedar vencida
        r = self.mover(a, Actividad.PENDIENTE)
        a.refresh_from_db()
        self.assertTrue(r.json()['vencida'])
        self.assertIsNone(a.fecha_cierre)

    def test_otro_funcionario_no_puede_mover(self):
        """PW-03 · Un funcionario no mueve la solicitud de otro; el delegado sí puede"""
        a = self.compromiso()
        self.entrar('bcastillo')
        r = self.mover(a, Actividad.PENDIENTE)
        self.assertEqual(r.status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.estado, Actividad.INGRESADO)
        self.assertTrue(Auditoria.objects.filter(evento='ACCESO_DENEGADO').exists())
        self.entrar('arojas')
        self.assertEqual(self.mover(a, Actividad.PENDIENTE).status_code, 200)
        a.refresh_from_db()
        self.assertEqual(a.estado, Actividad.PENDIENTE)

    def test_periodo_cerrado_no_se_mueve(self):
        """PW-04 · En un período cerrado las tarjetas no se mueven (ni por la URL)"""
        cerrado = Periodo.objects.create(nombre='Trimestre de prueba cerrado', inicio=date(2025, 1, 1),
                                         termino=date(2025, 3, 31), estado=Periodo.CERRADO)
        a = self.compromiso(periodo=cerrado, fecha=date(2025, 2, 3), ingresada_el=date(2025, 2, 3),
                            fecha_compromiso=date(2025, 2, 10))
        self.entrar('ftest')
        r = self.mover(a, Actividad.REALIZADO)
        self.assertEqual(r.status_code, 409)
        a.refresh_from_db()
        self.assertEqual(a.estado, Actividad.INGRESADO)

    def test_datos_no_validos(self):
        """PW-05 · Estado inexistente o el mismo estado se rechazan; solo se acepta POST; sin sesión no entra"""
        a = self.compromiso()
        self.entrar('ftest')
        self.assertEqual(self.mover(a, 'INVENTADO').status_code, 400)
        self.assertEqual(self.mover(a, Actividad.INGRESADO).status_code, 400)
        self.assertEqual(self.client.get(reverse('actividad_mover', args=[a.pk])).status_code, 405)
        self.client.logout()
        self.assertEqual(self.mover(a, Actividad.PENDIENTE).status_code, 401)
        a.refresh_from_db()
        self.assertEqual(a.estado, Actividad.INGRESADO)
        self.assertFalse(a.historial.exists())

    def test_tablero_marca_solo_lo_que_se_puede_mover(self):
        """PW-06 · En el TUBO solo son arrastrables las tarjetas que el usuario puede mover"""
        propia = self.compromiso(titulo='Solicitud propia')
        ajena = self.compromiso(funcionario=self.usuario('bcastillo'), titulo='Solicitud ajena')
        self.entrar('ftest')
        r = self.client.get(reverse('agenda'))
        self.assertContains(r, 'data-tubo-arrastrable')
        self.assertContains(r, reverse('actividad_mover', args=[propia.pk]))
        self.assertNotContains(r, reverse('actividad_mover', args=[ajena.pk]))
        self.assertContains(r, 'Mover a…')
        self.entrar('arojas')
        r = self.client.get(reverse('agenda'))
        self.assertContains(r, reverse('actividad_mover', args=[ajena.pk]))

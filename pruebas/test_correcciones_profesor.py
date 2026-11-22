"""
Pruebas de las correcciones pedidas por el profesor tras la presentación de la EV2.

Prefijos:
    PD  directiva vecinal de la organización: presidente, tesorero y encargado, vinculados a los vecinos
    PC  «Enviar a compromiso» desde una atención: llega al TUBO de Compromisos
    PT  TUBO dentro de Compromisos (vista en tarjetas por defecto)
    PQ  el trimestre en curso se ve siempre, para todos los usuarios

La fecha de trabajo es el miércoles 04-11-2026 (SGR_FECHA_HOY), igual que en test_matriz.
"""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.urls import reverse

from atenciones.models import Atencion, SeguimientoAtencion, Solicitante
from catalogos.models import ItemMedicion, SubAtencion
from gestion.models import Actividad, DirigenteOrganizacion, Organizacion, TipoOrganizacion

from .test_matriz import HOY, BaseMatriz

RUT_PRESIDENTA = '23.456.701-2'
RUT_TESORERO = '23.456.702-0'
RUT_ENCARGADA = '23.456.703-9'


class DirectivaVecinalTests(BaseMatriz):

    def datos_org(self, **cambios):
        datos = {
            'nombre': 'Junta de vecinos directiva', 'tipo': TipoOrganizacion.objects.get(codigo='TO01').pk,
            'delegacion': self.rural.pk, 'domicilio': 'Calle 1', 'socios': 40, 'registro_pj': 8801,
            'observacion': '', 'activo': 'on',
            'rut_presidente': RUT_PRESIDENTA, 'nombre_presidente': 'Rosa Presidenta',
            'telefono_presidente': '+56 9 1111 2222',
            'rut_tesorero': RUT_TESORERO, 'nombre_tesorero': 'Tomás Tesorero', 'telefono_tesorero': '',
            'rut_encargado': RUT_ENCARGADA, 'nombre_encargado': 'Elena Encargada', 'telefono_encargado': '',
        }
        datos.update(cambios)
        return datos

    def directiva(self, registro=8801):
        return dict(DirigenteOrganizacion.objects.filter(organizacion__registro_pj=registro)
                    .values_list('cargo', 'vecino__rut'))

    def test_crear_con_directiva_vinculada_a_vecinos(self):
        """PD-01 · Presidente, tesorero y encargado quedan vinculados a vecinos; los nuevos se registran por RUT"""
        existente = Solicitante.objects.create(rut=RUT_TESORERO, nombre='Tomás Tesorero Ya Registrado')
        self.entrar('arojas')
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org())
        org = Organizacion.objects.get(registro_pj=8801)
        self.assertRedirects(r, reverse('organizaciones_ver', args=[org.pk]))
        self.assertEqual(self.directiva(), {'PRESIDENTE': RUT_PRESIDENTA, 'TESORERO': RUT_TESORERO,
                                            'ENCARGADO': RUT_ENCARGADA})
        self.assertEqual(org.directiva.get(cargo='TESORERO').vecino, existente)   # no duplica al vecino
        self.assertEqual(Solicitante.objects.get(rut=RUT_PRESIDENTA).telefono, '+56 9 1111 2222')
        r = self.client.get(reverse('organizaciones_ver', args=[org.pk]))
        self.assertContains(r, 'Directiva vecinal')
        self.assertContains(r, 'Rosa Presidenta')
        self.assertContains(r, 'Tomás Tesorero Ya Registrado')
        r = self.client.get(reverse('organizaciones_lista'), {'q': 'Elena'})
        self.assertContains(r, 'JUNTA DE VECINOS DIRECTIVA')

    def test_reglas_de_la_directiva(self):
        """PD-02 · RUT válido, nombre si es nuevo y el mismo vecino no ocupa dos cargos"""
        self.entrar('arojas')
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org(rut_tesorero=RUT_PRESIDENTA))
        self.assertIn('rut_tesorero', r.context['form'].errors)
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org(rut_encargado='23.456.703-1'))
        self.assertIn('rut_encargado', r.context['form'].errors)
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org(nombre_encargado=''))
        self.assertIn('nombre_encargado', r.context['form'].errors)
        r = self.client.post(reverse('organizaciones_crear'), self.datos_org(rut_presidente=''))
        self.assertIn('rut_presidente', r.context['form'].errors)                  # nombre sin RUT
        self.assertFalse(Organizacion.objects.filter(registro_pj=8801).exists())

    def test_editar_quita_cargos_y_la_base_lo_asegura(self):
        """PD-03 · Al editar se puede dejar un cargo vacío; la base no admite dos personas en un cargo"""
        self.entrar('arojas')
        self.client.post(reverse('organizaciones_crear'), self.datos_org())
        org = Organizacion.objects.get(registro_pj=8801)
        self.client.post(reverse('organizaciones_editar', args=[org.pk]),
                         self.datos_org(rut_tesorero='', nombre_tesorero='', telefono_tesorero=''))
        self.assertEqual(set(self.directiva()), {'PRESIDENTE', 'ENCARGADO'})
        self.assertTrue(Solicitante.objects.filter(rut=RUT_TESORERO).exists())    # el vecino no se borra
        otro = Solicitante.objects.get(rut=RUT_TESORERO)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DirigenteOrganizacion.objects.create(organizacion=org, cargo='PRESIDENTE', vecino=otro)

    def test_historial_del_vecino_muestra_su_cargo(self):
        """PD-04 · El historial por vecino muestra el cargo aunque el dirigente no tenga atenciones"""
        self.entrar('arojas')
        self.client.post(reverse('organizaciones_crear'), self.datos_org())
        r = self.client.get(reverse('atencion_social'), {'rut': RUT_ENCARGADA})
        self.assertEqual(r.context['caso']['solicitante'].rut, RUT_ENCARGADA)
        self.assertContains(r, 'Encargado</b> de')


class EnviarCompromisoTests(BaseMatriz):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        sub = SubAtencion.objects.filter(activo=True, tipo__activo=True).select_related('tipo').first()
        cls.vecina = Solicitante.objects.create(rut='23.456.704-7', nombre='Vecina Compromiso',
                                                telefono='+56 9 5555 6666')
        cls.atencion = Atencion.objects.create(solicitante=cls.vecina, tipo=sub.tipo, subatencion=sub,
                                               descripcion='Solicita poda de árbol frente a su casa.',
                                               delegacion=cls.rural, responsable=cls.nueva)

    def enviar(self, **datos):
        datos = {'fecha_compromiso': (HOY + timedelta(days=10)).isoformat(), 'area_apoyo': 'Aseo y Ornato',
                 **datos}
        return self.client.post(reverse('atencion_a_compromiso', args=[self.atencion.pk]), datos)

    def test_la_atencion_ofrece_enviar_a_compromiso(self):
        """PC-01 · La ficha de la atención muestra «Enviar a compromiso» y el ingreso ofrece guardar y enviar"""
        self.entrar('ftest')
        r = self.client.get(reverse('atenciones_ver', args=[self.atencion.pk]))
        self.assertContains(r, 'Enviar a compromiso')
        self.assertIsNotNone(r.context['form_compromiso'])
        r = self.client.get(reverse('atenciones_crear'))
        self.assertContains(r, 'Guardar y enviar a compromiso')

    def test_envio_llega_al_tubo(self):
        """PC-02 · Enviar crea la solicitud «Ingresada» en el TUBO con los datos del vecino y deja el rastro"""
        self.entrar('ftest')
        r = self.enviar()
        self.assertRedirects(r, reverse('atenciones_ver', args=[self.atencion.pk]) + '#enviar-compromiso',
                             fetch_redirect_response=False)
        a = Actividad.objects.get(atencion=self.atencion)
        self.assertEqual((a.estado, a.fecha_compromiso, a.funcionario, a.delegacion),
                         (Actividad.INGRESADO, HOY + timedelta(days=10), self.nueva, self.rural))
        self.assertEqual(a.item.medicion, ItemMedicion.TUBO)
        self.assertEqual((a.solicitante_nombre, a.solicitante_telefono), ('Vecina Compromiso', '+56 9 5555 6666'))
        self.assertTrue(a.puntua)
        self.assertTrue(SeguimientoAtencion.objects.filter(atencion=self.atencion,
                                                           comentario__contains=a.folio).exists())
        r = self.client.get(reverse('agenda'))
        self.assertEqual(r.context['vista'], 'tubo')
        ingresadas = next(c for c in r.context['columnas'] if c['codigo'] == Actividad.INGRESADO)
        self.assertIn(a, ingresadas['filas'])
        r = self.client.get(reverse('atenciones_ver', args=[self.atencion.pk]))
        self.assertContains(r, 'En Compromisos (TUBO)')
        self.assertIsNone(r.context['form_compromiso'])

    def test_no_se_envia_dos_veces_ni_cerrada_ni_con_fecha_pasada(self):
        """PC-03 · Sin duplicados, sin fecha pasada y sin atenciones cerradas"""
        self.entrar('ftest')
        self.enviar(fecha_compromiso=(HOY - timedelta(days=1)).isoformat())
        self.assertFalse(Actividad.objects.filter(atencion=self.atencion).exists())
        self.enviar()
        self.enviar()
        self.assertEqual(Actividad.objects.filter(atencion=self.atencion).count(), 1)
        cerrada = Atencion.objects.create(solicitante=self.vecina, tipo=self.atencion.tipo, estado=Atencion.CERRADA,
                                          subatencion=self.atencion.subatencion, descripcion='Ya resuelta antes.',
                                          delegacion=self.rural, responsable=self.nueva)
        self.client.post(reverse('atencion_a_compromiso', args=[cerrada.pk]),
                         {'fecha_compromiso': (HOY + timedelta(days=3)).isoformat()})
        self.assertFalse(Actividad.objects.filter(atencion=cerrada).exists())

    def test_otra_delegacion_y_cupo_diario(self):
        """PC-04 · No se envía una atención de otra delegación y se respeta el máximo diario (regla 3)"""
        self.entrar('mtapia', delegacion='DEL01')
        self.assertEqual(self.enviar().status_code, 403)
        for _ in range(7):
            self.actividad(ingresada_el=HOY)
        self.entrar('ftest')
        self.enviar()
        self.assertFalse(Actividad.objects.filter(atencion=self.atencion).exists())


class TuboYTrimestreTests(BaseMatriz):

    def test_compromisos_abre_el_tubo_en_tarjetas(self):
        """PT-01 · Compromisos abre el TUBO en tarjetas por estado; la tabla sigue disponible"""
        self.entrar('arojas')
        r = self.client.get(reverse('agenda'))
        self.assertEqual(r.context['vista'], 'tubo')
        self.assertContains(r, 'TUBO en tarjetas')
        self.assertEqual(sum(c['total'] for c in r.context['columnas']), r.context['total'])
        self.assertEqual(self.client.get(reverse('agenda'), {'vista': 'tabla'}).context['vista'], 'tabla')
        r = self.client.get(reverse('inicio'))
        self.assertContains(r, 'Compromisos (TUBO)')
        self.assertNotContains(r, 'Actividades y TUBO')

    def test_trimestre_visible_para_todos(self):
        """PQ-01 · Todos los perfiles ven el trimestre en curso en la cabecera de cualquier pantalla"""
        for usuario, ruta in [('ftest', 'inicio'), ('arojas', 'agenda'), ('emunoz', 'usuarios_lista'),
                              ('bcastillo', 'atenciones_lista')]:
            self.entrar(usuario)
            r = self.client.get(reverse(ruta))
            self.assertEqual(r.status_code, 200, (usuario, ruta))
            self.assertContains(r, 'Trimestre en curso')
            self.assertContains(r, self.periodo.nombre)
            self.assertContains(r, f'quedan {self.periodo.dias_restantes} días')

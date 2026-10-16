"""Pruebas del ingreso de atención."""

import uuid

from django.urls import reverse

from atenciones.models import Atencion, Solicitante
from catalogos.models import Delegacion, SubAtencion, TipoAtencion

from .base import PruebaSGR


class IngresoAtencionTests(PruebaSGR):

    def setUp(self):
        self.entrar('bcastillo')
        self.tipo = TipoAtencion.objects.get(codigo='TA001')
        self.sub = self.tipo.subatenciones.filter(activo=True).first()

    def datos(self, **cambios):
        base = {'token_envio': str(uuid.uuid4()), 'rut': '11.111.111-1', 'nombre': 'Vecina de Prueba',
                'telefono': '+56 9 1234 5678', 'tipo': self.tipo.pk, 'subatencion': self.sub.pk,
                'descripcion': 'Solicita orientación sobre el beneficio municipal.'}
        base.update(cambios)
        return base

    def test_registro_correcto_con_folio(self):
        """PT-01 · Registrar una atención entrega confirmación con identificador (folio)"""
        antes = Atencion.objects.count()
        r = self.client.post(reverse('atenciones_crear'), self.datos(), follow=True)
        self.assertEqual(Atencion.objects.count(), antes + 1)
        a = Atencion.objects.latest('pk')
        self.assertRegex(a.folio, r'^AT-\d{4}-\d{6}$')
        self.assertMensaje(r, a.folio)
        self.assertEqual(r.redirect_chain[-1][0], reverse('atenciones_ver', args=[a.pk]) + '?nueva=1')

    def test_delegacion_responsable_y_fecha_automaticos(self):
        """PT-02 · Delegación, responsable y fecha se asignan en el servidor, no desde el formulario"""
        otra = Delegacion.objects.get(codigo='DEL01')
        self.client.post(reverse('atenciones_crear'), self.datos(delegacion=otra.pk, responsable=1))
        a = Atencion.objects.latest('pk')
        self.assertEqual(a.delegacion.codigo, 'DEL06')
        self.assertEqual(a.responsable.nombre_usuario, 'bcastillo')
        self.assertIsNotNone(a.creada)

    def test_doble_envio_no_duplica(self):
        """PT-03 · Doble envío del mismo formulario no crea dos atenciones"""
        datos = self.datos()
        antes = Atencion.objects.count()
        self.client.post(reverse('atenciones_crear'), datos)
        r = self.client.post(reverse('atenciones_crear'), datos, follow=True)
        self.assertEqual(Atencion.objects.count(), antes + 1)
        self.assertMensaje(r, 'No se creó un duplicado')

    def test_sub_debe_pertenecer_al_tipo(self):
        """PT-04 · La sub atención debe pertenecer al tipo elegido"""
        otra_sub = SubAtencion.objects.filter(activo=True).exclude(tipo=self.tipo).first()
        antes = Atencion.objects.count()
        r = self.client.post(reverse('atenciones_crear'), self.datos(subatencion=otra_sub.pk))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertEqual(Atencion.objects.count(), antes)

    def test_sub_inactiva_rechazada(self):
        """PT-05 · Una sub atención inactiva no puede usarse"""
        inactiva = SubAtencion.objects.get(codigo='SA021')
        r = self.client.post(reverse('atenciones_crear'),
                             self.datos(tipo=inactiva.tipo_id, subatencion=inactiva.pk))
        self.assertTrue(r.context['form'].errors)

    def test_tipo_inactivo_rechazado(self):
        """PT-06 · Un tipo de atención inactivo no puede usarse"""
        inactivo = TipoAtencion.objects.get(codigo='TA009')
        r = self.client.post(reverse('atenciones_crear'), self.datos(tipo=inactivo.pk))
        self.assertIn('tipo', r.context['form'].errors)

    def test_api_subatenciones_solo_activas_del_tipo(self):
        """PT-07 · El selector dependiente entrega solo sub atenciones activas del tipo"""
        tipo = TipoAtencion.objects.get(codigo='TA001')
        r = self.client.get(reverse('api_subatenciones'), {'tipo': tipo.pk})
        ids = {s['id'] for s in r.json()['subatenciones']}
        esperado = set(tipo.subatenciones.filter(activo=True).values_list('pk', flat=True))
        self.assertEqual(ids, esperado)
        self.assertNotIn(SubAtencion.objects.get(codigo='SA021').pk, ids)

    def test_api_subatenciones_tipo_invalido(self):
        """PT-08 · El selector dependiente rechaza tipos inválidos o inactivos"""
        r = self.client.get(reverse('api_subatenciones'), {'tipo': 'abc'})
        self.assertEqual(r.status_code, 400)
        r = self.client.get(reverse('api_subatenciones'), {'tipo': TipoAtencion.objects.get(codigo='TA009').pk})
        self.assertEqual(r.json()['subatenciones'], [])

    def test_campos_obligatorios(self):
        """PT-09 · Solicitante, tipo, sub atención y descripción son obligatorios"""
        r = self.client.post(reverse('atenciones_crear'), {'token_envio': str(uuid.uuid4())})
        errores = r.context['form'].errors
        for campo in ['rut', 'nombre', 'tipo', 'subatencion', 'descripcion']:
            self.assertIn(campo, errores)

    def test_rut_invalido(self):
        """PT-10 · El RUT se valida con dígito verificador"""
        r = self.client.post(reverse('atenciones_crear'), self.datos(rut='11.111.111-2'))
        self.assertIn('rut', r.context['form'].errors)

    def test_descripcion_minima(self):
        """PT-11 · La descripción exige un mínimo de caracteres"""
        r = self.client.post(reverse('atenciones_crear'), self.datos(descripcion='corta'))
        self.assertIn('descripcion', r.context['form'].errors)

    def test_solicitante_existente_se_reutiliza(self):
        """PT-12 · Un vecino ya registrado se reutiliza (sin duplicar por RUT)"""
        existente = Solicitante.objects.first()
        antes = Solicitante.objects.count()
        self.client.post(reverse('atenciones_crear'), self.datos(rut=existente.rut, nombre=existente.nombre))
        self.assertEqual(Solicitante.objects.count(), antes)
        r = self.client.get(reverse('api_solicitante'), {'rut': existente.rut})
        self.assertTrue(r.json()['encontrado'])

    def test_cancelar_no_crea(self):
        """PT-13 · Abrir el formulario y salir (cancelar) no crea registros"""
        antes = Atencion.objects.count()
        self.client.get(reverse('atenciones_crear'))
        self.client.get(reverse('atenciones_lista'))
        self.assertEqual(Atencion.objects.count(), antes)

    def test_sin_permiso_de_crear(self):
        """PT-14 · Un perfil sin permiso de crear no puede registrar atenciones"""
        self.client.post(reverse('salir'))
        self.entrar('lectura')
        antes = Atencion.objects.count()
        r = self.client.post(reverse('atenciones_crear'), self.datos())
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Atencion.objects.count(), antes)

    def test_listado_solo_de_la_delegacion_activa(self):
        """PT-15 · El listado y el Excel de atenciones se limitan a la delegación activa"""
        r = self.client.get(reverse('atenciones_lista'))
        delegaciones = {a.delegacion.codigo for a in r.context['pagina'].object_list}
        self.assertEqual(delegaciones, {'DEL06'})
        from .test_mantenedores import leer_excel
        _, _, filas = leer_excel(self.client.get(reverse('atenciones_exportar')))
        self.assertEqual(len(filas), Atencion.objects.filter(delegacion__codigo='DEL06').count())
        self.assertEqual({f[2] for f in filas}, {'DEL06'})

    def test_busqueda_por_folio_y_rut(self):
        """PT-16 · La búsqueda de atenciones encuentra por folio y por RUT"""
        a = Atencion.objects.filter(delegacion__codigo='DEL06').first()
        r = self.client.get(reverse('atenciones_lista'), {'q': a.folio})
        self.assertIn(a, r.context['pagina'].object_list)
        r = self.client.get(reverse('atenciones_lista'), {'q': a.solicitante.rut[:6]})
        self.assertIn(a, r.context['pagina'].object_list)

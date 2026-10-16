"""Pruebas de perfiles, permisos y contexto de delegación."""

from django.urls import reverse

from atenciones.models import Atencion
from catalogos.models import Delegacion
from core.models import Auditoria
from cuentas.models import Rol

from .base import PruebaSGR


def menu_de(respuesta):
    return {e['codigo'] for g in respuesta.context['menu'] for e in g['enlaces']}


class MenuPorRolTests(PruebaSGR):

    def test_superadministrador_ve_todo(self):
        """PP-01 · Superadministrador ve todos los módulos del menú"""
        self.entrar('admin')
        menu = menu_de(self.client.get(reverse('inicio')))
        for codigo in ['atenciones', 'delegaciones', 'roles', 'usuarios', 'items', 'tipos_atencion',
                       'sub_atenciones', 'auditoria', 'correos', 'tablero', 'informes']:
            self.assertIn(codigo, menu)

    def test_coordinador(self):
        """PP-02 · Coordinador ve catálogos y auditoría, pero no la bandeja de correos"""
        self.entrar('emunoz')
        menu = menu_de(self.client.get(reverse('inicio')))
        self.assertTrue({'items', 'tipos_atencion', 'sub_atenciones', 'auditoria', 'roles'} <= menu)
        self.assertNotIn('correos', menu)

    def test_delegado_municipal(self):
        """PP-03 · Delegado municipal no ve Roles ni Auditoría"""
        self.entrar('arojas')
        menu = menu_de(self.client.get(reverse('inicio')))
        self.assertIn('atenciones', menu)
        self.assertIn('usuarios', menu)
        self.assertNotIn('roles', menu)
        self.assertNotIn('auditoria', menu)

    def test_funcionario(self):
        """PP-04 · Funcionario solo ve atenciones y sus módulos operativos de trabajo"""
        self.entrar('bcastillo')
        menu = menu_de(self.client.get(reverse('inicio')))
        self.assertIn('atenciones', menu)
        for codigo in ['delegaciones', 'roles', 'usuarios', 'items', 'tipos_atencion', 'sub_atenciones',
                       'auditoria', 'correos']:
            self.assertNotIn(codigo, menu)

    def test_botones_segun_permiso(self):
        """PP-05 · Los botones Crear/Editar/Eliminar aparecen solo con permiso"""
        self.entrar('lectura')
        r = self.client.get(reverse('items_lista'))
        self.assertFalse(r.context['puede_crear'])
        self.assertNotContains(r, reverse('items_crear'))
        self.client.post(reverse('salir'))
        self.entrar('admin')
        r = self.client.get(reverse('items_lista'))
        self.assertContains(r, reverse('items_crear'))

    def test_cambio_de_permisos_se_refleja(self):
        """PP-06 · Quitar un permiso al rol oculta el módulo y bloquea la ruta"""
        rol = Rol.objects.get(codigo='ROL04')
        rol.permisos.remove(*rol.permisos.filter(modulo='atenciones'))
        self.entrar('bcastillo')
        self.assertNotIn('atenciones', menu_de(self.client.get(reverse('inicio'))))
        self.assertEqual(self.client.get(reverse('atenciones_lista')).status_code, 403)


class RutasProtegidasTests(PruebaSGR):

    def test_acceso_directo_por_url_sin_permiso(self):
        """PP-07 · Escribir la URL de un módulo no autorizado devuelve 403 y queda auditado"""
        self.entrar('bcastillo')
        for ruta in ['roles_lista', 'usuarios_crear', 'delegaciones_lista', 'auditoria', 'correos',
                     'items_exportar', 'roles_exportar']:
            with self.subTest(ruta=ruta):
                r = self.client.get(reverse(ruta))
                self.assertEqual(r.status_code, 403)
                self.assertTemplateUsed(r, '403.html')
        self.assertTrue(Auditoria.objects.filter(evento='ACCESO_DENEGADO').count() >= 7)

    def test_post_sin_permiso(self):
        """PP-08 · Un POST directo sin permiso no modifica datos"""
        self.entrar('lectura')
        tipo = Rol.objects.get(codigo='ROL04')
        r = self.client.post(reverse('roles_eliminar', args=[tipo.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Rol.objects.filter(pk=tipo.pk).exists())

    def test_consultor_solo_lectura(self):
        """PP-09 · Consultor puede ver catálogos pero no crear ni editar"""
        self.entrar('lectura')
        self.assertEqual(self.client.get(reverse('items_lista')).status_code, 200)
        self.assertEqual(self.client.get(reverse('items_crear')).status_code, 403)
        self.assertEqual(self.client.get(reverse('items_editar', args=[1])).status_code, 403)

    def test_modulos_simulados_respetan_permisos(self):
        """PP-10 · Los módulos simulados también respetan los permisos del rol"""
        self.entrar('bcastillo')
        self.assertEqual(self.client.get(reverse('tablero')).status_code, 200)
        self.assertEqual(self.client.get(reverse('periodos')).status_code, 403)


class EscaladaPrivilegiosTests(PruebaSGR):

    def test_delegado_no_asigna_rol_global(self):
        """PP-11 · Un delegado no puede asignar roles globales (escalada de privilegios)"""
        self.entrar('arojas')
        global_ = Rol.objects.get(codigo='ROL01')
        d = Delegacion.objects.get(codigo='DEL06')
        r = self.client.post(reverse('usuarios_crear'), {
            'nombre': 'Intruso', 'nombre_usuario': 'intruso', 'correo': 'intruso@example.test',
            'rol': global_.pk, 'delegaciones': [d.pk], 'is_active': 'on',
            'clave': 'Elqui#Valle77', 'confirmacion': 'Elqui#Valle77'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('rol', r.context['form'].errors)

    def test_delegado_no_asigna_delegacion_ajena(self):
        """PP-12 · Un delegado no puede asignar delegaciones que no tiene autorizadas"""
        self.entrar('arojas')
        r = self.client.post(reverse('usuarios_crear'), {
            'nombre': 'Otro', 'nombre_usuario': 'otro1', 'correo': 'otro1@example.test',
            'rol': Rol.objects.get(codigo='ROL04').pk,
            'delegaciones': [Delegacion.objects.get(codigo='DEL01').pk], 'is_active': 'on',
            'clave': 'Elqui#Valle77', 'confirmacion': 'Elqui#Valle77'})
        self.assertIn('delegaciones', r.context['form'].errors)

    def test_delegado_solo_ve_usuarios_de_sus_delegaciones(self):
        """PP-13 · Un delegado solo lista usuarios de sus delegaciones"""
        self.entrar('arojas')
        r = self.client.get(reverse('usuarios_lista'))
        nombres = {f['obj'].nombre_usuario for f in r.context['filas']}
        self.assertIn('bcastillo', nombres)
        self.assertNotIn('jalvarez', nombres)  # DEL01

    def test_delegado_no_edita_usuario_de_otra_delegacion(self):
        """PP-14 · Alterar el id en la URL para editar un usuario ajeno se rechaza con 403"""
        self.entrar('arojas')
        ajeno = self.usuario('jalvarez')
        r = self.client.get(reverse('usuarios_editar', args=[ajeno.pk]))
        self.assertEqual(r.status_code, 403)

    def test_delegado_no_edita_superadministrador(self):
        """PP-15 · Un delegado no puede editar cuentas con rol global"""
        self.entrar('arojas')
        r = self.client.get(reverse('usuarios_ver', args=[self.usuario('admin').pk]))
        self.assertEqual(r.status_code, 403)

    def test_editar_conserva_delegaciones_fuera_de_alcance(self):
        """PP-16 · Al editar, el delegado no borra delegaciones que no administra"""
        u = self.usuario('cvega')
        u.delegaciones.add(Delegacion.objects.get(codigo='DEL01'))
        self.entrar('arojas')
        r = self.client.post(reverse('usuarios_editar', args=[u.pk]), {
            'nombre': 'Camila Vega Soto', 'nombre_usuario': 'cvega', 'correo': 'cvega@example.test',
            'rol': u.rol_id, 'delegaciones': [Delegacion.objects.get(codigo='DEL06').pk], 'is_active': 'on',
            'clave': '', 'confirmacion': ''})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(set(u.delegaciones.values_list('codigo', flat=True)), {'DEL06', 'DEL01'})


class ContextoDelegacionTests(PruebaSGR):

    def test_cabecera_muestra_delegacion_usuario_y_rol(self):
        """PD-01 · La cabecera muestra código y nombre de la delegación, usuario y rol"""
        self.entrar('bcastillo')
        r = self.client.get(reverse('inicio'))
        self.assertContains(r, 'DEL06')
        self.assertContains(r, 'Delegación Rural')
        self.assertContains(r, 'Bruno Castillo Peña')
        self.assertContains(r, 'Funcionario')

    def test_una_delegacion_contexto_fijo(self):
        """PD-02 · Con una sola delegación el contexto es fijo (sin selector)"""
        self.entrar('bcastillo')
        r = self.client.get(reverse('inicio'))
        self.assertNotContains(r, 'id="selectorDelegacion"')
        self.assertContains(r, 'Contexto fijo')

    def test_varias_delegaciones_selector_solo_autorizadas(self):
        """PD-03 · Con varias delegaciones el selector ofrece solo las autorizadas"""
        self.entrar('arojas')
        r = self.client.get(reverse('inicio'))
        self.assertContains(r, 'id="selectorDelegacion"')
        codigos = {d.codigo for d in r.context['delegaciones_autorizadas']}
        self.assertEqual(codigos, {'DEL03', 'DEL06'})

    def test_cambio_de_contexto_actualiza_listados(self):
        """PD-04 · Cambiar la delegación activa cambia el listado y la exportación"""
        self.entrar('arojas')
        del06 = Delegacion.objects.get(codigo='DEL06')
        del03 = Delegacion.objects.get(codigo='DEL03')
        self.client.post(reverse('cambiar_delegacion'), {'delegacion': del06.pk, 'siguiente': '/atenciones/'})
        r = self.client.get(reverse('atenciones_lista'))
        self.assertEqual(r.context['pagina'].paginator.count, Atencion.objects.filter(delegacion=del06).count())
        self.client.post(reverse('cambiar_delegacion'), {'delegacion': del03.pk})
        r = self.client.get(reverse('atenciones_lista'))
        self.assertEqual(r.context['pagina'].paginator.count, Atencion.objects.filter(delegacion=del03).count())
        self.assertTrue(Auditoria.objects.filter(evento='CAMBIO_CONTEXTO').exists())

    def test_cambio_a_delegacion_no_autorizada(self):
        """PD-05 · Forzar una delegación no autorizada se rechaza (403) y el contexto no cambia"""
        self.entrar('arojas')
        antes = self.client.get(reverse('inicio')).context['delegacion_activa']
        ajena = Delegacion.objects.get(codigo='DEL01')
        r = self.client.post(reverse('cambiar_delegacion'), {'delegacion': ajena.pk})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get(reverse('inicio')).context['delegacion_activa'], antes)
        self.assertTrue(Auditoria.objects.filter(evento='ACCESO_DENEGADO').exists())

    def test_sesion_alterada_vuelve_a_delegacion_valida(self):
        """PD-06 · Si la sesión apunta a una delegación ajena, el servidor la corrige"""
        self.entrar('bcastillo')
        sesion = self.client.session
        sesion['delegacion_id'] = Delegacion.objects.get(codigo='DEL01').pk
        sesion.save()
        r = self.client.get(reverse('atenciones_lista'))
        self.assertEqual(r.context['delegacion_activa'].codigo, 'DEL06')

    def test_cambio_de_contexto_exige_post(self):
        """PD-07 · El cambio de contexto exige POST con token CSRF"""
        self.entrar('arojas')
        self.assertEqual(self.client.get(reverse('cambiar_delegacion')).status_code, 405)

    def test_atencion_de_otra_delegacion(self):
        """PD-08 · Ver una atención de una delegación no autorizada devuelve 403"""
        self.entrar('bcastillo')
        ajena = Atencion.objects.exclude(delegacion__codigo='DEL06').first()
        self.assertEqual(self.client.get(reverse('atenciones_ver', args=[ajena.pk])).status_code, 403)

    def test_delegacion_fuera_de_alcance_por_url(self):
        """PD-09 · Consultar por URL una delegación no autorizada devuelve 403"""
        self.entrar('arojas')
        ajena = Delegacion.objects.get(codigo='DEL01')
        r = self.client.get(reverse('delegaciones_ver', args=[ajena.pk]))
        self.assertEqual(r.status_code, 403)

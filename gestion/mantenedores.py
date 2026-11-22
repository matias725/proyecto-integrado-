"""Mantenedores de cargos y organizaciones comunitarias (motor común de core/crud.py)."""

from django import forms
from django.db import transaction
from django.db.models import Count

from atenciones.models import Solicitante
from catalogos.models import Cargo, Delegacion, Sector
from core.crud import Mantenedor
from core.forms_base import FormularioCatalogo
from core.validadores import formatear_rut, validar_rut, validar_telefono
from cuentas.models import Usuario

from .models import DirigenteOrganizacion, EncargadoOrganizacion, Organizacion, TipoOrganizacion


class CargoForm(FormularioCatalogo):
    prefijo, digitos = 'CAR', 2

    class Meta:
        model = Cargo
        fields = ['codigo', 'nombre', 'descripcion', 'es_delegado', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class SelectConPadre(forms.Select):
    """
    Agrega data-padre a cada opción para filtrar la lista en el navegador según otra lista
    (sector según delegación). `padres` devuelve los identificadores del padre, separados por espacio:
    un funcionario puede pertenecer a más de una delegación.
    """

    def __init__(self, *args, padres=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.padres = padres or (lambda instancia: str(instancia.delegacion_id))

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        instancia = getattr(value, 'instance', None)
        if instancia is not None:
            opcion['attrs']['data-padre'] = self.padres(instancia)
        return opcion


def delegaciones_del_usuario(usuario):
    return ' '.join(str(d.pk) for d in usuario.delegaciones.all())


class EncargadoField(forms.ModelChoiceField):
    def label_from_instance(self, usuario):
        return f'{usuario.nombre} · {usuario.cargo.nombre}' if usuario.cargo_id else usuario.nombre


class OrganizacionForm(forms.ModelForm):
    """
    Datos de la organización, su territorio (delegación y sector), hasta 3 funcionarios encargados y su directiva
    vecinal (presidente, tesorero y encargado), elegida entre los vecinos registrados por RUT.
    """

    PUESTOS = range(1, Organizacion.MAXIMO_ENCARGADOS + 1)

    class Meta:
        model = Organizacion
        fields = ['nombre', 'tipo', 'delegacion', 'sector', 'domicilio', 'socios', 'fecha_constitucion',
                  'registro_pj', 'fecha_inscripcion', 'registro_directiva', 'verificada', 'observacion', 'activo']
        widgets = {'fecha_constitucion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'fecha_inscripcion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'sector': SelectConPadre(attrs={'data-depende-de': 'id_delegacion'})}

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoOrganizacion.objects.filter(activo=True)
        delegaciones = Delegacion.objects.filter(activo=True)
        if actor and not actor.alcance_global:
            delegaciones = actor.delegaciones_autorizadas()
            self.fields['delegacion'].required = True
        self.fields['delegacion'].queryset = delegaciones.order_by('codigo')
        sectores = Sector.objects.filter(activo=True, delegacion__in=delegaciones)
        if self.instance.pk and self.instance.sector_id:
            sectores = sectores | Sector.objects.filter(pk=self.instance.sector_id)
        self.fields['sector'].queryset = sectores.select_related('delegacion').distinct().order_by('nombre')
        self.fields['sector'].empty_label = 'Sin sector'
        self.fields['verificada'].help_text = 'Marque solo después de contrastar los datos con el registro municipal.'
        # Encargados: funcionarios activos con cargo, de las delegaciones que el actor puede administrar
        funcionarios = (Usuario.objects.filter(is_active=True, cargo__isnull=False, delegaciones__in=delegaciones)
                        .select_related('cargo').prefetch_related('delegaciones').distinct().order_by('nombre'))
        actuales = {e.orden: e.usuario_id for e in self.instance.encargos.all()} if self.instance.pk else {}
        for orden in self.PUESTOS:
            campo = EncargadoField(
                queryset=funcionarios, required=False, label=f'Encargado {orden}',
                empty_label='Sin asignar', initial=actuales.get(orden),
                widget=SelectConPadre(attrs={'data-depende-de': 'id_delegacion'}, padres=delegaciones_del_usuario))
            if orden == 1:
                campo.help_text = 'Funcionarios de la delegación de la organización.'
            self.fields[f'encargado_{orden}'] = campo
        # Directiva vecinal: por cada cargo, el RUT del vecino (y su nombre si aún no está registrado)
        directiva = {d.cargo: d.vecino for d in self.instance.directiva.select_related('vecino')} \
            if self.instance.pk else {}
        for codigo, nombre in DirigenteOrganizacion.CARGOS:
            clave, vecino = codigo.lower(), directiva.get(codigo)
            self.fields[f'rut_{clave}'] = forms.CharField(
                label=f'RUT del {nombre.lower()}', max_length=12, required=False, validators=[validar_rut],
                initial=vecino.rut if vecino else '',
                widget=forms.TextInput(attrs={'placeholder': '12.345.678-5', 'autocomplete': 'off'}))
            self.fields[f'nombre_{clave}'] = forms.CharField(
                label='Nombre', max_length=150, required=False, initial=vecino.nombre if vecino else '',
                help_text='Solo si el RUT aún no está registrado como vecino.')
            self.fields[f'telefono_{clave}'] = forms.CharField(
                label='Teléfono', max_length=20, required=False, validators=[validar_telefono],
                initial=vecino.telefono if vecino else '',
                widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+56 9 1234 5678'}))

    def campos_encargados(self):
        return [self[f'encargado_{orden}'] for orden in self.PUESTOS]

    def campos_directiva(self):
        """[(nombre del cargo, campo RUT, campo nombre, campo teléfono)] para la plantilla."""
        return [(nombre, self[f'rut_{c.lower()}'], self[f'nombre_{c.lower()}'], self[f'telefono_{c.lower()}'])
                for c, nombre in DirigenteOrganizacion.CARGOS]

    def clean_nombre(self):
        return ' '.join(self.cleaned_data['nombre'].split()).upper()

    def clean(self):
        limpio = super().clean()
        constitucion, inscripcion = limpio.get('fecha_constitucion'), limpio.get('fecha_inscripcion')
        if constitucion and inscripcion and inscripcion < constitucion:
            self.add_error('fecha_inscripcion', 'La inscripción no puede ser anterior a la constitución.')
        delegacion, sector = limpio.get('delegacion'), limpio.get('sector')
        if sector and sector.delegacion_id != getattr(delegacion, 'pk', None):
            self.add_error('sector', f'El sector «{sector}» pertenece a {sector.delegacion.nombre}. '
                                     'Elija un sector de la delegación de la organización.')
        vistos = set()
        for orden in self.PUESTOS:
            usuario = limpio.get(f'encargado_{orden}')
            if not usuario:
                continue
            if delegacion is None:
                self.add_error(f'encargado_{orden}', 'Elija primero la delegación de la organización.')
            elif delegacion not in usuario.delegaciones.all():
                self.add_error(f'encargado_{orden}', f'{usuario.nombre} no trabaja en {delegacion.nombre}.')
            if usuario.pk in vistos:
                self.add_error(f'encargado_{orden}', f'{usuario.nombre} ya está como encargado.')
            vistos.add(usuario.pk)
        self._limpiar_directiva(limpio)
        return limpio

    def _limpiar_directiva(self, limpio):
        """Valida la directiva: RUT válido, nombre si el vecino es nuevo y sin repetir a la misma persona."""
        self.directiva_elegida, ruts = {}, {}
        for codigo, nombre in DirigenteOrganizacion.CARGOS:
            clave = codigo.lower()
            rut = (limpio.get(f'rut_{clave}') or '').strip()
            persona = ' '.join((limpio.get(f'nombre_{clave}') or '').split())
            telefono = (limpio.get(f'telefono_{clave}') or '').strip()
            if not rut:
                if persona or telefono:
                    self.add_error(f'rut_{clave}', f'Escriba el RUT del {nombre.lower()} para vincularlo al vecino.')
                continue
            if f'rut_{clave}' in self.errors:
                continue
            rut = formatear_rut(rut)
            if rut in ruts:
                self.add_error(f'rut_{clave}', f'Ese vecino ya figura como {ruts[rut].lower()}.')
                continue
            ruts[rut] = nombre
            vecino = Solicitante.objects.filter(rut=rut).first()
            if vecino is None and len(persona) < 5:
                self.add_error(f'nombre_{clave}', 'El RUT no está registrado: escriba el nombre completo del vecino.')
                continue
            self.directiva_elegida[codigo] = (rut, persona, telefono, vecino)

    @transaction.atomic
    def save(self, commit=True):
        organizacion = super().save(commit=commit)
        if commit:
            self.guardar_encargados(organizacion)
            self.guardar_directiva(organizacion)
        return organizacion

    def guardar_directiva(self, organizacion):
        """Vincula cada cargo con su vecino; registra al vecino si su RUT aún no estaba en el sistema."""
        organizacion.directiva.all().delete()
        nuevos = []
        for codigo, (rut, persona, telefono, vecino) in self.directiva_elegida.items():
            if vecino is None:
                vecino = Solicitante.objects.create(rut=rut, nombre=persona, telefono=telefono)
            elif telefono and not vecino.telefono:
                vecino.telefono = telefono
                vecino.save(update_fields=['telefono'])
            nuevos.append(DirigenteOrganizacion(organizacion=organizacion, cargo=codigo, vecino=vecino))
        DirigenteOrganizacion.objects.bulk_create(nuevos)

    def guardar_encargados(self, organizacion):
        """Los puestos quedan correlativos: si se deja vacío el 1 y se elige el 2, este pasa a ser el 1."""
        elegidos = [self.cleaned_data[f'encargado_{orden}'] for orden in self.PUESTOS
                    if self.cleaned_data.get(f'encargado_{orden}')]
        actuales = [(e.orden, e.usuario_id) for e in organizacion.encargos.order_by('orden')]
        if actuales == [(n, u.pk) for n, u in enumerate(elegidos, start=1)]:
            return
        organizacion.encargos.all().delete()
        EncargadoOrganizacion.objects.bulk_create([
            EncargadoOrganizacion(organizacion=organizacion, usuario=u, orden=n)
            for n, u in enumerate(elegidos, start=1)])


class Cargos(Mantenedor):
    modulo = 'cargos'
    modelo = Cargo
    formulario = CargoForm
    titulo = 'Cargos de las delegaciones'
    singular = 'cargo'
    femenino = False
    descripcion = 'Cargos del descriptor de funciones 2026. Cada cargo tiene sus ítems y metas en la matriz SGR.'
    traza = 'Descriptor de funciones 2026 · Matriz SGR'
    columnas = [('codigo', 'Código'), ('nombre', 'Cargo'), ('es_delegado', 'Delegado'),
                ('total_usuarios', 'Funcionarios')]
    busqueda = ['codigo', 'nombre', 'descripcion']
    exportar = [('codigo', 'Código'), ('nombre', 'Cargo'), ('descripcion', 'Función principal'),
                ('es_delegado', 'Delegado'), ('total_usuarios', 'Funcionarios'), ('estado', 'Estado')]
    detalle = [('codigo', 'Código'), ('nombre', 'Cargo'), ('descripcion', 'Función principal'),
               ('es_delegado', 'Es delegado'), ('estado', 'Estado'), ('actualizado', 'Última modificación')]
    relacionados = [('usuarios', 'Funcionarios con este cargo', [('nombre', 'Nombre'),
                                                                  ('lista_delegaciones', 'Delegación'),
                                                                  ('estado', 'Estado')])]

    def consulta(self, request):
        return Cargo.objects.annotate(total_usuarios=Count('usuarios', distinct=True))


class Organizaciones(Mantenedor):
    modulo = 'organizaciones'
    modelo = Organizacion
    formulario = OrganizacionForm
    titulo = 'Organizaciones comunitarias'
    singular = 'organización'
    descripcion = ('Juntas de vecinos y organizaciones funcionales de la base municipal, por territorio, sector y '
                   'subfamilia, con su directiva vecinal (presidente, tesorero y encargado) y hasta 3 funcionarios '
                   'encargados. Las importadas quedan «sin verificar» hasta revisarlas.')
    traza = 'Nuevo requerimiento · base JJVV · Leyes 19.418 y 20.500'
    plantilla_formulario = 'gestion/organizacion_formulario.html'
    plantilla_detalle = 'gestion/organizacion_detalle.html'
    orden = ['nombre']
    columnas = [('nombre', 'Organización'), ('tipo.nombre', 'Subfamilia'), ('territorio', 'Territorio y sector'),
                ('directiva_texto', 'Directiva vecinal'), ('encargados_texto', 'Encargados municipales'),
                ('encargados_resumen', 'Puestos'), ('verificada', 'Verificada')]
    busqueda = ['nombre', 'domicilio', 'tipo__nombre', 'delegacion__nombre', 'sector__nombre', 'registro_pj',
                'encargos__usuario__nombre', 'directiva__vecino__nombre', 'directiva__vecino__rut']
    exportar = [('nombre', 'Organización'), ('tipo.get_familia_display', 'Familia'), ('tipo.nombre', 'Subfamilia'),
                ('delegacion.nombre', 'Territorio'), ('sector.nombre', 'Sector'), ('domicilio', 'Domicilio legal'),
                ('socios', 'Socios'), ('fecha_constitucion', 'Constitución'), ('registro_pj', 'Registro PJ'),
                ('fecha_inscripcion', 'Inscripción'), ('registro_directiva', 'Registro directiva'),
                ('presidente', 'Presidente'), ('tesorero', 'Tesorero'), ('encargado_vecinal', 'Encargado vecinal'),
                ('encargado_1', 'Encargado 1'), ('encargado_2', 'Encargado 2'), ('encargado_3', 'Encargado 3'),
                ('verificada', 'Verificada'), ('observacion', 'Observación'), ('estado', 'Vigencia')]
    detalle = [('nombre', 'Organización'), ('tipo.get_familia_display', 'Familia'), ('tipo.nombre', 'Subfamilia'),
               ('delegacion', 'Territorio de delegación'), ('sector', 'Sector'), ('domicilio', 'Domicilio legal'),
               ('socios', 'Socios activos'), ('fecha_constitucion', 'Fecha de constitución'),
               ('registro_pj', 'N.º registro PJ'), ('fecha_inscripcion', 'Inscripción en el registro'),
               ('registro_directiva', 'N.º registro directiva'), ('verificada', 'Datos verificados'),
               ('observacion', 'Observación de calidad'), ('estado', 'Vigencia'),
               ('actualizado', 'Última modificación')]
    relacionados = [('actividades', 'Actividades con la organización', [
        ('folio', 'Folio'), ('fecha', 'Fecha'), ('titulo', 'Actividad'), ('funcionario.nombre', 'Responsable')])]

    def consulta(self, request):
        consulta = Organizacion.objects.select_related('tipo', 'delegacion', 'sector').prefetch_related(
            'encargos__usuario', 'directiva__vecino')
        if not request.user.alcance_global:
            consulta = consulta.filter(delegacion__in=request.delegaciones_autorizadas)
        tipo, delegacion, verificada, sector = (request.GET.get(k, '') for k in
                                                ('tipo', 'delegacion', 'verificada', 'sector'))
        if tipo.isdigit():
            consulta = consulta.filter(tipo_id=int(tipo))
        if delegacion.isdigit():
            consulta = consulta.filter(delegacion_id=int(delegacion))
        if sector.isdigit():
            consulta = consulta.filter(sector_id=int(sector))
        if verificada in ('si', 'no'):
            consulta = consulta.filter(verificada=verificada == 'si')
        if request.GET.get('a_cargo') == 'mias':
            consulta = consulta.filter(encargos__usuario=request.user)
        return consulta

    def kwargs_formulario(self, request):
        return {'actor': request.user}


CARGOS = Cargos()
ORGANIZACIONES = Organizaciones()

"""Mantenedores de cargos y organizaciones comunitarias (motor común de core/crud.py)."""

from django import forms
from django.db.models import Count

from catalogos.models import Cargo, Delegacion
from core.crud import Mantenedor
from core.forms_base import FormularioCatalogo

from .models import Organizacion, TipoOrganizacion


class CargoForm(FormularioCatalogo):
    prefijo, digitos = 'CAR', 2

    class Meta:
        model = Cargo
        fields = ['codigo', 'nombre', 'descripcion', 'es_delegado', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class OrganizacionForm(forms.ModelForm):
    class Meta:
        model = Organizacion
        fields = ['nombre', 'tipo', 'delegacion', 'domicilio', 'socios', 'fecha_constitucion', 'registro_pj',
                  'fecha_inscripcion', 'registro_directiva', 'verificada', 'observacion', 'activo']
        widgets = {'fecha_constitucion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'fecha_inscripcion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoOrganizacion.objects.filter(activo=True)
        delegaciones = Delegacion.objects.filter(activo=True)
        if actor and not actor.alcance_global:
            delegaciones = actor.delegaciones_autorizadas()
            self.fields['delegacion'].required = True
        self.fields['delegacion'].queryset = delegaciones.order_by('codigo')
        self.fields['verificada'].help_text = 'Marque solo después de contrastar los datos con el registro municipal.'

    def clean_nombre(self):
        return ' '.join(self.cleaned_data['nombre'].split()).upper()

    def clean(self):
        limpio = super().clean()
        constitucion, inscripcion = limpio.get('fecha_constitucion'), limpio.get('fecha_inscripcion')
        if constitucion and inscripcion and inscripcion < constitucion:
            self.add_error('fecha_inscripcion', 'La inscripción no puede ser anterior a la constitución.')
        return limpio


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
    descripcion = ('Juntas de vecinos y organizaciones funcionales de la base municipal, por territorio y '
                   'subfamilia. Las importadas quedan «sin verificar» hasta revisarlas.')
    traza = 'Nuevo requerimiento · base JJVV · Leyes 19.418 y 20.500'
    orden = ['nombre']
    columnas = [('nombre', 'Organización'), ('tipo.nombre', 'Subfamilia'), ('delegacion.nombre', 'Territorio'),
                ('socios', 'Socios'), ('verificada', 'Verificada')]
    busqueda = ['nombre', 'domicilio', 'tipo__nombre', 'delegacion__nombre', 'registro_pj']
    exportar = [('nombre', 'Organización'), ('tipo.get_familia_display', 'Familia'), ('tipo.nombre', 'Subfamilia'),
                ('delegacion.nombre', 'Territorio'), ('domicilio', 'Domicilio legal'), ('socios', 'Socios'),
                ('fecha_constitucion', 'Constitución'), ('registro_pj', 'Registro PJ'),
                ('fecha_inscripcion', 'Inscripción'), ('registro_directiva', 'Registro directiva'),
                ('verificada', 'Verificada'), ('observacion', 'Observación'), ('estado', 'Vigencia')]
    detalle = [('nombre', 'Organización'), ('tipo.get_familia_display', 'Familia'), ('tipo.nombre', 'Subfamilia'),
               ('delegacion', 'Territorio de delegación'), ('domicilio', 'Domicilio legal'),
               ('socios', 'Socios activos'), ('fecha_constitucion', 'Fecha de constitución'),
               ('registro_pj', 'N.º registro PJ'), ('fecha_inscripcion', 'Inscripción en el registro'),
               ('registro_directiva', 'N.º registro directiva'), ('verificada', 'Datos verificados'),
               ('observacion', 'Observación de calidad'), ('estado', 'Vigencia'),
               ('actualizado', 'Última modificación')]
    relacionados = [('actividades', 'Actividades con la organización', [
        ('folio', 'Folio'), ('fecha', 'Fecha'), ('titulo', 'Actividad'), ('funcionario.nombre', 'Responsable')])]

    def consulta(self, request):
        consulta = Organizacion.objects.select_related('tipo', 'delegacion')
        if not request.user.alcance_global:
            consulta = consulta.filter(delegacion__in=request.delegaciones_autorizadas)
        tipo, delegacion, verificada = (request.GET.get(k, '') for k in ('tipo', 'delegacion', 'verificada'))
        if tipo.isdigit():
            consulta = consulta.filter(tipo_id=int(tipo))
        if delegacion.isdigit():
            consulta = consulta.filter(delegacion_id=int(delegacion))
        if verificada in ('si', 'no'):
            consulta = consulta.filter(verificada=verificada == 'si')
        return consulta

    def kwargs_formulario(self, request):
        return {'actor': request.user}


CARGOS = Cargos()
ORGANIZACIONES = Organizaciones()

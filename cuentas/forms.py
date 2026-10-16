"""Formularios de acceso, recuperación de contraseña, roles y usuarios."""

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError
from django.utils import timezone

from catalogos.models import Delegacion
from core.forms_base import FormularioCatalogo
from core.reglas import motivo_no_desactivar

from .models import Permiso, Rol, Usuario
from .modulos import ACCIONES, MODULOS

MENSAJE_CREDENCIALES = 'Usuario, correo o contraseña incorrectos. Revise los datos e intente nuevamente.'


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------
class AccesoForm(forms.Form):
    identificador = forms.CharField(
        label='Usuario o correo', max_length=120,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'placeholder': 'usuario o nombre@example.test'}))
    clave = forms.CharField(
        label='Contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.usuario = None
        super().__init__(*args, **kwargs)

    def clean(self):
        limpio = super().clean()
        if self.errors:
            return limpio
        identificador, clave = limpio['identificador'], limpio['clave']
        cuenta = Usuario.objects.por_identificador(identificador)

        if cuenta and cuenta.bloqueado:
            minutos = max(1, int((cuenta.bloqueado_hasta - timezone.now()).total_seconds() // 60) + 1)
            raise ValidationError(
                f'Por seguridad, el acceso quedó bloqueado temporalmente tras varios intentos fallidos. '
                f'Intente nuevamente en {minutos} minuto(s) o recupere su contraseña.', code='bloqueada')

        usuario = authenticate(self.request, username=identificador, password=clave)
        if usuario is None:
            if cuenta and cuenta.check_password(clave) and not (cuenta.is_active and cuenta.rol.activo):
                raise ValidationError('Su cuenta está inactiva. Contacte al administrador del sistema.',
                                      code='inactiva')
            if cuenta:
                cuenta.registrar_fallo()
            from core.models import registrar
            registrar(self.request, 'ACCESO_FALLIDO', 'sesión', detalle=identificador[:60], usuario=cuenta)
            raise ValidationError(MENSAJE_CREDENCIALES, code='credenciales')
        self.usuario = usuario
        return limpio


# ---------------------------------------------------------------------------
# Recuperación de contraseña
# ---------------------------------------------------------------------------
class SolicitudCodigoForm(forms.Form):
    correo = forms.EmailField(
        label='Correo electrónico', max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'nombre@example.test'}))


class ValidarCodigoForm(forms.Form):
    codigo = forms.RegexField(
        label='Código de verificación', regex=r'^\d{6}$', max_length=6,
        error_messages={'invalid': 'El código tiene 6 dígitos numéricos.',
                        'required': 'Ingrese los 6 dígitos del código.'},
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code'}))


class NuevaClaveForm(forms.Form):
    clave = forms.CharField(
        label='Nueva contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    confirmacion = forms.CharField(
        label='Confirmar nueva contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_clave(self):
        clave = self.cleaned_data['clave']
        password_validation.validate_password(clave, self.usuario)
        if self.usuario.check_password(clave):
            raise ValidationError('La nueva contraseña debe ser distinta de la anterior.')
        return clave

    def clean(self):
        limpio = super().clean()
        if limpio.get('clave') and limpio.get('confirmacion') and limpio['clave'] != limpio['confirmacion']:
            self.add_error('confirmacion', 'Las contraseñas no coinciden.')
        return limpio


# ---------------------------------------------------------------------------
# Mantenedor de roles
# ---------------------------------------------------------------------------
class RolForm(FormularioCatalogo):
    prefijo = 'ROL'
    digitos = 2

    permisos = forms.ModelMultipleChoiceField(
        queryset=Permiso.objects.all(), required=False, widget=forms.CheckboxSelectMultiple,
        label='Permisos')

    class Meta:
        model = Rol
        fields = ['codigo', 'nombre', 'descripcion', 'alcance', 'permisos', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.protegido:
            # Un rol protegido conserva alcance, permisos y estado.
            for campo in ('alcance', 'permisos', 'activo'):
                self.fields[campo].disabled = True
            self.fields['permisos'].help_text = 'Rol del sistema: conserva todos los permisos.'

    def clean_activo(self):
        activo = self.cleaned_data['activo']
        if self.instance.pk and self.instance.activo and not activo:
            motivo = motivo_no_desactivar(self.instance)
            if motivo:
                raise ValidationError(motivo)
        return activo

    def matriz(self):
        """Permisos ordenados por módulo para dibujarlos como tabla."""
        elegidos = {str(getattr(v, 'pk', v)) for v in (self['permisos'].value() or [])}
        por_codigo = {(p.modulo, p.accion): p for p in Permiso.objects.all()}
        filas = []
        for codigo, nombre, estado, acciones, _icono, grupo in MODULOS:
            celdas = []
            for accion, etiqueta in ACCIONES:
                permiso = por_codigo.get((codigo, accion))
                celdas.append({'permiso': permiso, 'etiqueta': etiqueta,
                               'marcado': bool(permiso) and str(permiso.pk) in elegidos})
            filas.append({'codigo': codigo, 'nombre': nombre, 'estado': estado, 'grupo': grupo, 'celdas': celdas})
        return filas


# ---------------------------------------------------------------------------
# Mantenedor de usuarios
# ---------------------------------------------------------------------------
class UsuarioForm(forms.ModelForm):
    clave = forms.CharField(
        label='Contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}, render_value=False))
    confirmacion = forms.CharField(
        label='Confirmar contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}, render_value=False))

    class Meta:
        model = Usuario
        fields = ['nombre', 'nombre_usuario', 'correo', 'rol', 'delegaciones', 'is_active']
        widgets = {'delegaciones': forms.CheckboxSelectMultiple}
        labels = {'is_active': 'Cuenta activa'}

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        roles = Rol.objects.filter(activo=True)
        delegaciones = Delegacion.objects.filter(activo=True)
        if actor and not actor.alcance_global:
            # Sin alcance global no se pueden otorgar más privilegios de los propios.
            roles = roles.filter(alcance=Rol.DELEGACION, protegido=False)
            delegaciones = actor.delegaciones_autorizadas()
        if self.instance.pk and self.instance.rol_id:
            roles = roles | Rol.objects.filter(pk=self.instance.rol_id)
        self.fields['rol'].queryset = roles.distinct().order_by('codigo')
        self.fields['delegaciones'].queryset = delegaciones.order_by('codigo')
        self.fields['delegaciones'].required = True
        self.fields['delegaciones'].help_text = 'Al menos una. La primera se usa como contexto inicial.'
        self.fields['nombre_usuario'].help_text = 'Minúsculas, sin espacios. Sirve para ingresar junto con el correo.'
        if self.instance.pk:
            self.fields['clave'].help_text = 'Déjela en blanco para conservar la contraseña actual.'
        else:
            self.fields['clave'].required = True
            self.fields['confirmacion'].required = True
        if self.instance.pk and actor and self.instance.pk == actor.pk:
            self.fields['is_active'].disabled = True
            self.fields['is_active'].help_text = 'No puede desactivar su propia cuenta.'

    def clean_nombre_usuario(self):
        valor = self.cleaned_data['nombre_usuario'].strip().lower()
        if Usuario.objects.filter(nombre_usuario__iexact=valor).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe un usuario con ese nombre de usuario.')
        return valor

    def clean_correo(self):
        valor = self.cleaned_data['correo'].strip().lower()
        if Usuario.objects.filter(correo__iexact=valor).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe un usuario con ese correo.')
        return valor

    def clean_rol(self):
        rol = self.cleaned_data['rol']
        if self.actor and not self.actor.alcance_global and (rol.alcance == Rol.GLOBAL or rol.protegido):
            raise ValidationError('Su perfil no permite asignar un rol con alcance global.')
        return rol

    def clean_delegaciones(self):
        elegidas = self.cleaned_data['delegaciones']
        if self.actor and not self.actor.alcance_global:
            permitidas = set(self.actor.delegaciones_autorizadas().values_list('pk', flat=True))
            if any(d.pk not in permitidas for d in elegidas):
                raise ValidationError('Solo puede asignar delegaciones que usted tiene autorizadas.')
        return elegidas

    def clean(self):
        limpio = super().clean()
        clave, confirmacion = limpio.get('clave'), limpio.get('confirmacion')
        if clave or confirmacion:
            if clave != confirmacion:
                self.add_error('confirmacion', 'Las contraseñas no coinciden.')
            else:
                usuario = self.instance if self.instance.pk else Usuario(
                    nombre=limpio.get('nombre', ''), nombre_usuario=limpio.get('nombre_usuario', ''),
                    correo=limpio.get('correo', ''))
                try:
                    password_validation.validate_password(clave, usuario)
                except ValidationError as error:
                    self.add_error('clave', error)
        return limpio

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('clave'):
            usuario.set_password(self.cleaned_data['clave'])
        if commit:
            usuario.save()
            self.save_m2m()
            self._conservar_delegaciones_ajenas(usuario)
        return usuario

    def _conservar_delegaciones_ajenas(self, usuario):
        """Un actor sin alcance global no ve todas las delegaciones del usuario
        que edita: las que están fuera de su alcance se conservan intactas."""
        if not (self.actor and not self.actor.alcance_global and self.initial.get('delegaciones')):
            return
        permitidas = set(self.actor.delegaciones_autorizadas().values_list('pk', flat=True))
        previas = {getattr(d, 'pk', d) for d in self.initial['delegaciones']}
        ajenas = previas - permitidas
        if ajenas:
            usuario.delegaciones.add(*ajenas)

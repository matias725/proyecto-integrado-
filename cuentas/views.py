"""
Acceso, recuperación de contraseña, contexto de delegación e inicio.

Recuperación en tres pasos:
  1. Solicitar código: respuesta genérica, no revela si el correo existe.
  2. Validar código: 6 dígitos, vigencia, intentos limitados y reenvío con espera.
  3. Nueva contraseña: solo tras una verificación válida; el código queda usado.
"""

import secrets
import time
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import registrar

from .forms import AccesoForm, NuevaClaveForm, SolicitudCodigoForm, ValidarCodigoForm
from .middleware import CLAVE_SESION
from .models import CodigoRecuperacion, CorreoSaliente, Usuario, enmascarar_correo
from .modulos import MODULOS, OPERATIVO
from .permisos import denegar, permiso_requerido, sesion_requerida
from .validadores import REQUISITOS

SESION_RECUPERACION = 'recuperacion'


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------
def acceso(request):
    if request.user.is_authenticated:
        return redirect('inicio')
    form = AccesoForm(request, request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if form.is_valid():
            usuario = form.usuario
            login(request, usuario)
            usuario.limpiar_fallos()
            registrar(request, 'ACCESO', 'sesión', usuario.pk, 'Inicio de sesión correcto')
            messages.success(request, f'Sesión iniciada como {usuario.nombre} · {usuario.rol.nombre}.')
            siguiente = request.POST.get('next') or request.GET.get('next') or ''
            if not url_has_allowed_host_and_scheme(siguiente, {request.get_host()}, request.is_secure()):
                siguiente = 'inicio'
            return redirect(siguiente)
        messages.error(request, form.non_field_errors()[0] if form.non_field_errors()
                       else 'Complete los campos marcados.')
    return render(request, 'cuentas/acceso.html', {'form': form, 'next': request.GET.get('next', '')})


@require_POST
def salir(request):
    if request.user.is_authenticated:
        registrar(request, 'SALIDA', 'sesión', request.user.pk)
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('acceso')


# ---------------------------------------------------------------------------
# Recuperación · paso 1
# ---------------------------------------------------------------------------
def _enviar_codigo(usuario):
    codigo = f'{secrets.randbelow(10 ** 6):06d}'
    registro = CodigoRecuperacion.emitir(usuario, codigo)
    send_mail(
        'Código de verificación · SGR La Serena',
        f'Hola {usuario.nombre}:\n\n'
        f'Su código para recuperar la contraseña es: {codigo}\n\n'
        f'Vence en {settings.SGR_CODIGO_VIGENCIA_MIN} minutos y sirve una sola vez.\n'
        'Si usted no lo solicitó, ignore este mensaje: su contraseña no cambiará.\n\n'
        'Sistema de Gestión de Resultados · Municipalidad de La Serena',
        None, [usuario.correo], fail_silently=False)
    return registro


def _puede_emitir(usuario):
    hace_una_hora = timezone.now() - timedelta(hours=1)
    recientes = usuario.codigos_recuperacion.filter(creado__gte=hace_una_hora).count()
    ultimo = usuario.codigos_recuperacion.first()
    if ultimo and ultimo.segundos_para_reenvio() > 0:
        return False
    return recientes < settings.SGR_CODIGO_MAX_POR_HORA


def recuperar(request):
    form = SolicitudCodigoForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if form.is_valid():
            correo = form.cleaned_data['correo'].lower()
            usuario = Usuario.objects.filter(correo__iexact=correo, is_active=True).first()
            codigo_id = None
            if usuario:
                ultimo = usuario.codigos_recuperacion.first()
                if _puede_emitir(usuario):
                    codigo_id = _enviar_codigo(usuario).pk
                elif ultimo and ultimo.utilizable:
                    codigo_id = ultimo.pk
                registrar(request, 'RECUPERACION', 'cuenta', usuario.pk, 'Solicitud de código', usuario=usuario)
            request.session[SESION_RECUPERACION] = {
                'correo': enmascarar_correo(correo), 'codigo_id': codigo_id,
                'emitido': time.time(), 'intentos': 0, 'verificado': False,
            }
            # Mismo mensaje exista o no la cuenta
            messages.info(request, 'Si el correo está asociado a una cuenta activa, recibirá un código de '
                                   'verificación. Revise su bandeja de entrada.')
            return redirect('recuperar_validar')
        messages.error(request, 'Ingrese un correo válido, por ejemplo nombre@example.test.')
    return render(request, 'cuentas/recuperar.html', {'form': form, 'paso': 1})


# ---------------------------------------------------------------------------
# Recuperación · paso 2
# ---------------------------------------------------------------------------
def _datos_recuperacion(request):
    return request.session.get(SESION_RECUPERACION)


def _codigo_de(datos):
    return CodigoRecuperacion.objects.select_related('usuario').filter(pk=datos.get('codigo_id')).first()


def _segundos_reenvio(datos, codigo):
    if codigo:
        return codigo.segundos_para_reenvio()
    return max(0, int(settings.SGR_CODIGO_REENVIO_SEG - (time.time() - datos.get('emitido', 0))))


def validar_codigo(request):
    datos = _datos_recuperacion(request)
    if not datos:
        messages.warning(request, 'Primero solicite un código de verificación.')
        return redirect('recuperar')
    codigo = _codigo_de(datos)
    form = ValidarCodigoForm(request.POST if request.method == 'POST' else None)
    maximo = settings.SGR_CODIGO_MAX_INTENTOS

    if request.method == 'POST':
        if form.is_valid():
            ingresado = form.cleaned_data['codigo']
            error = None
            if codigo is None:
                # Sin cuenta: se simulan los mismos mensajes para no revelar nada.
                datos['intentos'] += 1
                restantes = max(0, maximo - datos['intentos'])
                error = (f'Código incorrecto. Le quedan {restantes} intento(s).' if restantes
                         else 'Superó el número de intentos permitidos. Solicite un código nuevo.')
            elif codigo.usado_en:
                error = 'Este código ya fue utilizado. Solicite uno nuevo.'
            elif codigo.anulado:
                error = 'Este código fue reemplazado por uno más reciente. Use el último código recibido.'
            elif codigo.vencido:
                error = 'El código venció. Solicite uno nuevo con «Reenviar código».'
            elif codigo.agotado:
                error = 'Superó el número de intentos permitidos. Solicite un código nuevo.'
            elif not codigo.coincide(ingresado):
                codigo.intentos += 1
                codigo.save(update_fields=['intentos'])
                restantes = max(0, maximo - codigo.intentos)
                error = (f'Código incorrecto. Le quedan {restantes} intento(s).' if restantes
                         else 'Superó el número de intentos permitidos. Solicite un código nuevo.')
            if error:
                request.session[SESION_RECUPERACION] = datos
                messages.error(request, error)
            else:
                codigo.verificado_en = timezone.now()
                codigo.save(update_fields=['verificado_en'])
                datos['verificado'] = True
                request.session[SESION_RECUPERACION] = datos
                registrar(request, 'RECUPERACION', 'cuenta', codigo.usuario_id, 'Código verificado',
                          usuario=codigo.usuario)
                messages.success(request, 'Código verificado. Ahora cree su nueva contraseña.')
                return redirect('recuperar_nueva')
        else:
            messages.error(request, 'Ingrese los 6 dígitos del código.')

    return render(request, 'cuentas/recuperar_validar.html', {
        'form': form, 'paso': 2, 'correo': datos['correo'],
        'segundos_reenvio': _segundos_reenvio(datos, codigo),
        'vigencia': settings.SGR_CODIGO_VIGENCIA_MIN,
    })


@require_POST
def reenviar_codigo(request):
    datos = _datos_recuperacion(request)
    if not datos:
        return redirect('recuperar')
    codigo = _codigo_de(datos)
    espera = _segundos_reenvio(datos, codigo)
    if espera > 0:
        messages.warning(request, f'Podrá solicitar un nuevo código en {espera} segundos.')
        return redirect('recuperar_validar')
    if codigo:
        usuario = codigo.usuario
        if _puede_emitir(usuario):
            datos['codigo_id'] = _enviar_codigo(usuario).pk
            registrar(request, 'RECUPERACION', 'cuenta', usuario.pk, 'Reenvío de código', usuario=usuario)
        else:
            messages.warning(request, 'Alcanzó el máximo de códigos por hora. Intente más tarde.')
            return redirect('recuperar_validar')
    datos.update({'emitido': time.time(), 'intentos': 0, 'verificado': False})
    request.session[SESION_RECUPERACION] = datos
    messages.info(request, 'Si el correo está asociado a una cuenta activa, enviamos un nuevo código.')
    return redirect('recuperar_validar')


# ---------------------------------------------------------------------------
# Recuperación · paso 3
# ---------------------------------------------------------------------------
def nueva_clave(request):
    datos = _datos_recuperacion(request)
    codigo = _codigo_de(datos) if datos else None
    limite = timedelta(minutes=settings.SGR_CODIGO_VIGENCIA_MIN)
    valido = (datos and datos.get('verificado') and codigo and codigo.verificado_en and not codigo.usado_en
              and not codigo.anulado and timezone.now() - codigo.verificado_en <= limite)
    if not valido:
        messages.warning(request, 'Para crear una nueva contraseña primero debe verificar un código vigente.')
        return redirect('recuperar_validar' if datos else 'recuperar')

    usuario = codigo.usuario
    form = NuevaClaveForm(usuario, request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if form.is_valid():
            usuario.set_password(form.cleaned_data['clave'])
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.save(update_fields=['password', 'intentos_fallidos', 'bloqueado_hasta'])
            codigo.usado_en = timezone.now()
            codigo.save(update_fields=['usado_en'])
            usuario.codigos_recuperacion.filter(usado_en__isnull=True).update(anulado=True)
            request.session.pop(SESION_RECUPERACION, None)
            registrar(request, 'CAMBIO_CLAVE', 'cuenta', usuario.pk, 'Contraseña restablecida', usuario=usuario)
            messages.success(request, 'Contraseña actualizada. Ya puede ingresar con su nueva contraseña.')
            return redirect('acceso')
        messages.error(request, 'La contraseña no se guardó. Revise los requisitos indicados.')
    return render(request, 'cuentas/recuperar_nueva.html', {
        'form': form, 'paso': 3, 'requisitos': REQUISITOS,
    })


# ---------------------------------------------------------------------------
# Contexto de delegación
# ---------------------------------------------------------------------------
@require_POST
@sesion_requerida
def cambiar_delegacion(request):
    elegida = request.POST.get('delegacion', '')
    autorizadas = {str(d.pk): d for d in request.delegaciones_autorizadas}
    if elegida not in autorizadas:
        # Una solicitud alterada no cambia el contexto
        return denegar(request, f'delegación {elegida[:10]} no autorizada')
    request.session[CLAVE_SESION] = autorizadas[elegida].pk
    request.delegacion_activa = autorizadas[elegida]
    registrar(request, 'CAMBIO_CONTEXTO', 'delegación', elegida, str(autorizadas[elegida]))
    messages.success(request, f'Ahora trabaja en {autorizadas[elegida].codigo} · '
                              f'{autorizadas[elegida].nombre_completo}.')
    siguiente = request.POST.get('siguiente', '')
    if not url_has_allowed_host_and_scheme(siguiente, {request.get_host()}, request.is_secure()):
        siguiente = 'inicio'
    return redirect(siguiente)


# ---------------------------------------------------------------------------
# Inicio: muestra solo lo autorizado al rol
# ---------------------------------------------------------------------------
@sesion_requerida
def inicio(request):
    usuario = request.user
    modulos = []
    for codigo, nombre, estado, acciones, icono, grupo in MODULOS:
        permitidas = [a for a in acciones if usuario.tiene_permiso(codigo, a)]
        if permitidas:
            modulos.append({'codigo': codigo, 'nombre': nombre, 'icono': icono, 'grupo': grupo,
                            'operativo': estado == OPERATIVO, 'acciones': permitidas})
    from atenciones.models import Atencion
    resumen = None
    if usuario.tiene_permiso('atenciones', 'ver') and request.delegacion_activa:
        hoy = timezone.localdate()
        de_la_delegacion = Atencion.objects.filter(delegacion=request.delegacion_activa)
        resumen = {
            'total': de_la_delegacion.count(),
            'mias': de_la_delegacion.filter(responsable=usuario).count(),
            'ultimas': de_la_delegacion.select_related('tipo', 'subatencion', 'solicitante')[:5],
            'hoy': hoy,
        }
    return render(request, 'cuentas/inicio.html', {
        'modulos': modulos, 'resumen': resumen,
        'operativos': sum(m['operativo'] for m in modulos),
        'simulados': sum(not m['operativo'] for m in modulos),
    })


# ---------------------------------------------------------------------------
# Bandeja de correos de prueba
# ---------------------------------------------------------------------------
@permiso_requerido('correos', 'ver')
def bandeja(request):
    pagina = Paginator(CorreoSaliente.objects.all(), settings.SGR_POR_PAGINA).get_page(request.GET.get('pagina'))
    return render(request, 'cuentas/bandeja.html', {'pagina': pagina,
                                                    'backend': settings.EMAIL_BACKEND.rsplit('.', 1)[-1]})

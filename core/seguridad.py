"""
Cabeceras de seguridad y límite de intentos por dirección IP.

- Content-Security-Policy estricta: solo recursos propios, sin scripts ni estilos
  en línea (el proyecto no los usa) y sin incrustarse en otros sitios.
- Permissions-Policy: el sistema no usa cámara, micrófono, ubicación ni pagos.
- Cache-Control «no-store» en páginas con sesión: los datos de vecinos no quedan
  en la caché del navegador de un computador compartido.
- Límite por IP en el acceso y la recuperación de clave (complementa el bloqueo
  por cuenta: frena a quien prueba muchas cuentas distintas desde un mismo equipo).
"""

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.template.loader import render_to_string

CSP = '; '.join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
PERMISOS = 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()'



def grupo_limitado(path):
    """Rutas con límite por IP: el acceso ('/') y todo el flujo de recuperación."""
    if path == '/':
        return 'acceso'
    if path.startswith('/recuperar/'):
        return 'recuperar'
    return None


def ip_cliente(request):
    """
    IP real del cliente. Detrás de Nginx se toma la última entrada de X-Forwarded-For
    (la que agrega el propio Nginx), porque las anteriores las puede inventar el cliente.
    """
    if settings.SGR_DETRAS_DE_PROXY:
        reenviada = [p.strip() for p in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if p.strip()]
        if reenviada:
            return reenviada[-1]
    return request.META.get('REMOTE_ADDR') or 'desconocida'


def _clave(request, ruta):
    return f'sgr:intentos:{ruta}:{ip_cliente(request)}'


def demasiados_intentos(request, ruta):
    return cache.get(_clave(request, ruta), 0) >= settings.SGR_IP_MAX_INTENTOS


def anotar_intento(request, ruta):
    clave = _clave(request, ruta)
    if cache.add(clave, 1, settings.SGR_IP_VENTANA_MIN * 60):
        return
    try:
        cache.incr(clave)
    except ValueError:              # expiró entre add e incr
        cache.set(clave, 1, settings.SGR_IP_VENTANA_MIN * 60)


class SeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        grupo = grupo_limitado(request.path)
        if grupo and request.method == 'POST':
            if demasiados_intentos(request, grupo):
                return self._limitada(request)
            anotar_intento(request, grupo)

        respuesta = self.get_response(request)
        respuesta.setdefault('Content-Security-Policy', CSP)
        respuesta.setdefault('Permissions-Policy', PERMISOS)
        if getattr(request, 'user', None) is not None and request.user.is_authenticated:
            respuesta.setdefault('Cache-Control', 'no-store, private')
        return respuesta

    def _limitada(self, request):
        contenido = render_to_string('429.html', {'minutos': settings.SGR_IP_VENTANA_MIN}, request=request)
        respuesta = HttpResponse(contenido, status=429)
        respuesta['Retry-After'] = str(settings.SGR_IP_VENTANA_MIN * 60)
        return respuesta

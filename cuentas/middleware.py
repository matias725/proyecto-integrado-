"""
Contexto de delegación activa.

En cada petición se valida en el servidor que la delegación guardada en la
sesión siga estando autorizada para el usuario; si no lo está, se usa la
primera autorizada. Las vistas leen request.delegacion_activa.
"""

CLAVE_SESION = 'delegacion_id'


class ContextoDelegacionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.delegacion_activa = None
        request.delegaciones_autorizadas = []
        if request.user.is_authenticated:
            autorizadas = list(request.user.delegaciones_autorizadas().order_by('codigo'))
            request.delegaciones_autorizadas = autorizadas
            elegida = request.session.get(CLAVE_SESION)
            activa = next((d for d in autorizadas if d.pk == elegida), autorizadas[0] if autorizadas else None)
            request.delegacion_activa = activa
            if activa and elegida != activa.pk:
                request.session[CLAVE_SESION] = activa.pk
        return self.get_response(request)

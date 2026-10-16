from .mantenedores import DELEGACIONES, ITEMS, SUB_ATENCIONES, TIPOS_ATENCION

urlpatterns = [
    *DELEGACIONES.urls('delegaciones'),
    *ITEMS.urls('items'),
    *TIPOS_ATENCION.urls('tipos-atencion'),
    *SUB_ATENCIONES.urls('sub-atenciones'),
]

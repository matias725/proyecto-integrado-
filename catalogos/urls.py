from .mantenedores import DELEGACIONES, ITEMS, SECTORES, SUB_ATENCIONES, TIPOS_ATENCION

urlpatterns = [
    *DELEGACIONES.urls('delegaciones'),
    *SECTORES.urls('sectores'),
    *ITEMS.urls('items'),
    *TIPOS_ATENCION.urls('tipos-atencion'),
    *SUB_ATENCIONES.urls('sub-atenciones'),
]

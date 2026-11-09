from django.urls import path

from . import views
from .mantenedores import CARGOS, ORGANIZACIONES

urlpatterns = [
    path('tablero/', views.tablero, name='tablero'),
    path('actividades/', views.actividades, name='actividades'),
    path('actividades/exportar/', views.actividades_exportar, name='actividades_exportar'),
    path('actividades/nueva/', views.actividad_nueva, name='actividad_nueva'),
    path('actividades/<int:pk>/', views.actividad_ver, name='actividad_ver'),
    path('actividades/<int:pk>/estado/', views.actividad_estado, name='actividad_estado'),
    path('actividades/<int:pk>/evidencia/', views.evidencia_subir, name='evidencia_subir'),
    path('actividades/<int:pk>/validar/', views.validar, name='validar'),
    path('evidencias/', views.evidencias, name='evidencias'),
    path('evidencias/<int:pk>/descargar/', views.evidencia_descargar, name='evidencia_descargar'),
    path('validacion/', views.validacion, name='validacion'),
    path('agenda/', views.agenda, name='agenda'),
    path('atencion-social/', views.atencion_social, name='atencion_social'),
    path('semaforo/', views.ausencias, name='ausencias'),
    path('semaforo/<int:pk>/eliminar/', views.ausencia_eliminar, name='ausencia_eliminar'),
    path('felicitaciones-reclamos/', views.observaciones, name='observaciones'),
    path('felicitaciones-reclamos/<int:pk>/respaldo/', views.observacion_respaldo, name='observacion_respaldo'),
    path('periodos/', views.periodos, name='periodos'),
    path('periodos/<int:pk>/<str:accion>/', views.periodo_estado, name='periodo_estado'),
    path('metas/', views.metas, name='metas'),
    path('metas/<int:pk>/eliminar/', views.meta_eliminar, name='meta_eliminar'),
    path('informes/', views.informes, name='informes'),
    path('informes/exportar/', views.informes_exportar, name='informes_exportar'),
    *CARGOS.urls('cargos'),
    *ORGANIZACIONES.urls('organizaciones'),
]

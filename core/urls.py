from django.urls import path

from . import views, vistas_sistema

urlpatterns = [
    # Operativo
    path('auditoria/', vistas_sistema.auditoria, name='auditoria'),
    path('auditoria/exportar/', vistas_sistema.auditoria_exportar, name='auditoria_exportar'),
    path('salud/', vistas_sistema.salud, name='salud'),

    # Módulos simulados heredados de la EV1 (datos en memoria)
    path('periodo/', views.cambiar_periodo, name='cambiar_periodo'),
    path('tablero/', views.tablero, name='tablero'),
    path('actividades/', views.actividades, name='actividades'),
    path('actividades/nueva/', views.actividad_nueva, name='actividad_nueva'),
    path('actividades/<int:id>/registrada/', views.actividad_registrada, name='actividad_registrada'),
    path('evidencias/', views.evidencias, name='evidencias'),
    path('validacion/', views.validacion, name='validacion'),
    path('agenda/', views.agenda, name='agenda'),
    path('agenda/<int:id>/estado/', views.compromiso_estado, name='compromiso_estado'),
    path('atencion-social/', views.atencion_social, name='atencion_social'),
    path('periodos/', views.periodos, name='periodos'),
    path('periodos/<int:id>/<str:accion>/', views.periodo_estado, name='periodo_estado'),
    path('metas/', views.metas, name='metas'),
    path('informes/', views.informes, name='informes'),
]

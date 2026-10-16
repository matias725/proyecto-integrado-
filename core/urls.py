from django.urls import path

from . import views

urlpatterns = [
    # CU-01 · Acceso
    path('', views.acceso, name='acceso'),
    path('salir/', views.salir, name='salir'),
    path('periodo/', views.cambiar_periodo, name='cambiar_periodo'),

    # Operación
    path('tablero/', views.tablero, name='tablero'),                                          # CU-13
    path('actividades/', views.actividades, name='actividades'),                              # CU-07, CU-17
    path('actividades/nueva/', views.actividad_nueva, name='actividad_nueva'),                # CU-07
    path('actividades/<int:id>/registrada/', views.actividad_registrada, name='actividad_registrada'),
    path('evidencias/', views.evidencias, name='evidencias'),                                 # CU-09
    path('validacion/', views.validacion, name='validacion'),                                 # CU-10
    path('agenda/', views.agenda, name='agenda'),                                             # CU-11
    path('agenda/<int:id>/estado/', views.compromiso_estado, name='compromiso_estado'),       # CU-12
    path('atencion-social/', views.atencion_social, name='atencion_social'),                  # CU-08

    # Configuración
    path('delegaciones/', views.delegaciones, name='delegaciones'),                           # CU-02
    path('delegaciones/<int:id>/estado/', views.delegacion_estado, name='delegacion_estado'),
    path('usuarios/', views.usuarios, name='usuarios'),                                       # CU-03
    path('periodos/', views.periodos, name='periodos'),                                       # CU-05
    path('periodos/<int:id>/<str:accion>/', views.periodo_estado, name='periodo_estado'),
    path('metas/', views.metas, name='metas'),                                                # CU-06

    # Información
    path('informes/', views.informes, name='informes'),                                       # CU-14
    path('auditoria/', views.auditoria, name='auditoria'),                                    # CU-16
]

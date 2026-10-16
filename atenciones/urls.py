from django.urls import path

from . import views

urlpatterns = [
    path('atenciones/', views.lista, name='atenciones_lista'),
    path('atenciones/nueva/', views.nueva, name='atenciones_crear'),
    path('atenciones/exportar/', views.exportar, name='atenciones_exportar'),
    path('atenciones/<int:pk>/', views.ver, name='atenciones_ver'),
    path('api/subatenciones/', views.api_subatenciones, name='api_subatenciones'),
    path('api/solicitantes/', views.api_solicitante, name='api_solicitante'),
]

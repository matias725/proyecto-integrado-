from django.urls import path

from . import views
from .mantenedores import ROLES, USUARIOS

urlpatterns = [
    path('', views.acceso, name='acceso'),
    path('salir/', views.salir, name='salir'),
    path('recuperar/', views.recuperar, name='recuperar'),
    path('recuperar/validar/', views.validar_codigo, name='recuperar_validar'),
    path('recuperar/reenviar/', views.reenviar_codigo, name='recuperar_reenviar'),
    path('recuperar/nueva/', views.nueva_clave, name='recuperar_nueva'),
    path('inicio/', views.inicio, name='inicio'),
    path('contexto/delegacion/', views.cambiar_delegacion, name='cambiar_delegacion'),
    path('correos/', views.bandeja, name='correos'),
    *ROLES.urls('roles'),
    *USUARIOS.urls('usuarios'),
]

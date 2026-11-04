from django.urls import path

from . import vistas_sistema

urlpatterns = [
    path('auditoria/', vistas_sistema.auditoria, name='auditoria'),
    path('auditoria/exportar/', vistas_sistema.auditoria_exportar, name='auditoria_exportar'),
    path('salud/', vistas_sistema.salud, name='salud'),
]

from django.urls import include, path

urlpatterns = [
    path('', include('cuentas.urls')),
    path('', include('catalogos.urls')),
    path('', include('atenciones.urls')),
    path('', include('core.urls')),
]

handler500 = 'core.vistas_sistema.error_servidor'
handler403 = 'core.vistas_sistema.acceso_denegado'

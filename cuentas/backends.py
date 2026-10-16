"""Ingreso con nombre de usuario o correo (requisito A1 · Login)."""

from django.contrib.auth.backends import ModelBackend

from .models import Usuario


class UsuarioOCorreoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        usuario = Usuario.objects.por_identificador(username)
        if usuario is None:
            # Se calcula un hash igual para que el tiempo de respuesta no
            # revele si la cuenta existe.
            Usuario().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None

    def user_can_authenticate(self, user):
        return user.is_active and bool(user.rol_id) and user.rol.activo

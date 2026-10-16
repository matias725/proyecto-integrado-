"""
Reglas de integridad de los catálogos.

Las usan tanto los formularios como las acciones rápidas de la tabla, para
que la misma regla se cumpla por cualquier camino.
"""


def _plural(n, singular, plural):
    return f'{n} {singular if n == 1 else plural}'


def motivo_no_desactivar(obj, actor=None):
    from catalogos.models import Delegacion, SubAtencion, TipoAtencion
    from cuentas.models import Rol, Usuario

    if isinstance(obj, Delegacion):
        n = obj.usuarios.filter(is_active=True).count()
        if n:
            return f'Tiene {_plural(n, "usuario activo", "usuarios activos")}. Reasígnelos antes de desactivarla.'
    elif isinstance(obj, TipoAtencion):
        n = obj.subatenciones.filter(activo=True).count()
        if n:
            return (f'Tiene {_plural(n, "sub atención activa", "sub atenciones activas")}. '
                    'Desactívelas antes de desactivar el tipo.')
    elif isinstance(obj, Rol):
        if obj.protegido:
            return 'Es un rol del sistema y no puede desactivarse.'
        n = obj.usuarios.filter(is_active=True).count()
        if n:
            return f'Lo usan {_plural(n, "usuario activo", "usuarios activos")}. Asígneles otro rol primero.'
    elif isinstance(obj, Usuario):
        if actor and obj.pk == actor.pk:
            return 'No puede desactivar su propia cuenta.'
    elif isinstance(obj, SubAtencion):
        pass
    return None


def motivo_no_activar(obj):
    from catalogos.models import SubAtencion

    if isinstance(obj, SubAtencion) and not obj.tipo.activo:
        return f'Su tipo de atención «{obj.tipo}» está inactivo. Actívelo primero.'
    return None


def motivo_no_eliminar(obj, actor=None):
    from catalogos.models import Delegacion, SubAtencion, TipoAtencion
    from cuentas.models import Rol, Usuario

    if isinstance(obj, Delegacion):
        usuarios, atenciones = obj.usuarios.count(), obj.atenciones.count()
        if usuarios or atenciones:
            return (f'Tiene {_plural(usuarios, "usuario", "usuarios")} y '
                    f'{_plural(atenciones, "atención", "atenciones")} asociados. Puede desactivarla en su lugar.')
    elif isinstance(obj, Rol):
        if obj.protegido:
            return 'Es un rol del sistema y no puede eliminarse.'
        n = obj.usuarios.count()
        if n:
            return f'Lo tienen asignado {_plural(n, "usuario", "usuarios")}. Puede desactivarlo en su lugar.'
    elif isinstance(obj, Usuario):
        if actor and obj.pk == actor.pk:
            return 'No puede eliminar su propia cuenta.'
        n = obj.atenciones.count()
        if n:
            return f'Registró {_plural(n, "atención", "atenciones")}. Desactive la cuenta para conservar el historial.'
    elif isinstance(obj, TipoAtencion):
        subs, atenciones = obj.subatenciones.count(), obj.atenciones.count()
        if subs or atenciones:
            return (f'Tiene {_plural(subs, "sub atención", "sub atenciones")} y '
                    f'{_plural(atenciones, "atención", "atenciones")} asociadas. Puede desactivarlo en su lugar.')
    elif isinstance(obj, SubAtencion):
        n = obj.atenciones.count()
        if n:
            return f'Se usó en {_plural(n, "atención", "atenciones")}. Puede desactivarla en su lugar.'
    return None

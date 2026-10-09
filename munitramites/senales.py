"""Señales del proyecto. >>> ACÁ SE CORTAN LAS REGLAS DE ORO <<<

Se enganchan desde `apps.ready()` (ver `conectar_senales()`), siguiendo el
mismo patrón que `services/chatbot/indexar.py`.
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save


def un_solo_superusuario(sender, instance, **kwargs):
    """Regla: UNA sola cuenta de superusuario en todo el sistema.

    El superusuario es la única llave a /admin/, a los usuarios, a los
    grupos y a los perfiles (DNI): si se multiplica, el candado deja de
    servir. El guard corre ANTES de escribir, así que cualquier intento de
    crear —o de elevar una cuenta a— un segundo superusuario corta en el
    acto, sin importar por dónde venga (admin, shell, script, test).
    """
    if not instance.is_superuser:
        return
    hay_otro = (
        User.objects.filter(is_superuser=True).exclude(pk=instance.pk).exists()
    )
    if hay_otro:
        raise ValidationError(
            'Solo puede haber UN superusuario en el sistema. Para dar de '
            'alta otra cuenta con permisos de gestión, usá el rol '
            '«Administrador» desde el panel (/panel/usuarios/).'
        )


def conectar_senales():
    """Se engancha al guardado de usuarios (se llama desde apps.ready())."""
    pre_save.connect(
        un_solo_superusuario,
        sender=User,
        dispatch_uid='un_solo_superusuario',
    )

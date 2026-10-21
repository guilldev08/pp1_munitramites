"""Pasa los enlaces viejos (`enlace_turnos` / `enlace_oficial`) a botones.

El Centro de Trámites ya no tiene esos dos campos fijos: los enlaces son
botones con nombre y URL (`Enlace`), y se agregan o se borran de la
lista. Esta migración conserva lo que ya estaba cargado, lo pasa a
botones y deja los campos viejos vacíos para que la ficha muestre los
botones y no el respaldo.
"""

from django.db import migrations

# Campo viejo → nombre que se le da al botón.
CAMPOS = (
    ('enlace_turnos', 'Pedir turno'),
    ('enlace_oficial', 'Sitio del organismo'),
)


def pasar_a_enlaces(apps, schema_editor):
    Tramite = apps.get_model('munitramites', 'Tramite')
    Enlace = apps.get_model('munitramites', 'Enlace')

    for tramite in Tramite.objects.all():
        existentes = set(tramite.enlaces.values_list('url', flat=True))
        orden = tramite.enlaces.count()
        for campo, nombre in CAMPOS:
            url = getattr(tramite, campo)
            if not url or url in existentes:
                continue
            Enlace.objects.create(
                tramite=tramite, nombre=nombre, url=url, orden=orden,
            )
            existentes.add(url)
            orden += 1
        if tramite.enlace_turnos or tramite.enlace_oficial:
            tramite.enlace_turnos = ''
            tramite.enlace_oficial = ''
            tramite.save(update_fields=['enlace_turnos', 'enlace_oficial'])


def volver(apps, schema_editor):
    """No se reconstruye: los botones se pudieron editar después."""


class Migration(migrations.Migration):

    dependencies = [
        ('munitramites', '0009_alter_enlace_url'),
    ]

    operations = [
        migrations.RunPython(pasar_a_enlaces, volver),
    ]

"""Comando retirado: ya no carga los datos de ejemplo.

La base de desarrollo se pobló con el dataset curado de trámites oficiales
de Misiones (138 fichas). El seed anterior creaba ocho trámites ficticios y
organismos/municipios de relleno, así que se dejó este comando como aviso
para no volver a introducir esos datos por accidente.

No escribe en la base. Para restaurar una copia usar el backup JSON del
equipo o el admin de Django.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Aviso: el seed de datos de ejemplo fue retirado.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'cargar_datos ya no carga datos de ejemplo. '
            'La base se pobló con el dataset curado de trámites oficiales '
            'de Misiones y este comando no modifica nada.'
        ))

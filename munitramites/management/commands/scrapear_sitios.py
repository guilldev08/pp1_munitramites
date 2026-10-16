"""Importa la planilla de organismos y scrapea los sitios oficiales.

    docker compose exec web python manage.py scrapear_sitios
    docker compose exec web python manage.py scrapear_sitios --limite 5 --max-por-sitio 3

La lógica vive en `munitramites/services/scraper/` (ahí está
documentada: planilla → rastreo → extracción). Este comando solo lee las
opciones, llama al servicio y muestra el resumen.

Todo lo que sale del scraping queda INACTIVO: se revisa, se corrige y se
publica desde el Centro de Trámites del panel. Es idempotente: si se
corre de nuevo, no duplica trámites ya cargados.
"""

import os

from django.core.management.base import BaseCommand, CommandError

from munitramites.services import scraper


class Command(BaseCommand):
    help = (
        'Importa la planilla de organismos y scrapear cada sitio oficial '
        'buscando trámites (quedan inactivos para revisar).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv', default=str(scraper.PLANILLA),
            help='Planilla a importar (NOMBRE, OCUPACION, LINK_SITIO_OFICIAL).',
        )
        parser.add_argument(
            '--limite', type=int, default=0,
            help='Procesar solo los primeros N sitios (0 = todos).',
        )
        parser.add_argument(
            '--max-por-sitio', type=int, default=8,
            help='Cuántos links con pinta de trámite se siguen por sitio.',
        )
        parser.add_argument(
            '--espera', type=float, default=0.6,
            help='Segundos de pausa entre pedido y pedido (cortesía).',
        )
        parser.add_argument(
            '--solo-organismos', action='store_true',
            help='Importa la planilla y no scrapear nada.',
        )

    def handle(self, *args, **opciones):
        ruta = opciones['csv']
        if not os.path.exists(ruta):
            raise CommandError(f'No existe la planilla: {ruta}')

        organismos, creados, actualizados = scraper.importar_planilla(ruta)
        self.stdout.write(self.style.SUCCESS(
            f'Organismos: {creados} creados, {actualizados} actualizados '
            f'(total en la planilla: {len(organismos)}).'
        ))
        if opciones['solo_organismos']:
            return

        if opciones['limite']:
            organismos = organismos[:opciones['limite']]

        def avisar(mensaje, error=False):
            if error:
                self.stderr.write(self.style.WARNING(mensaje))
            else:
                self.stdout.write(mensaje)

        creados, omitidos, caidos = scraper.scrapear(
            organismos,
            max_por_sitio=opciones['max_por_sitio'],
            espera=opciones['espera'],
            avisar=avisar,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Listo: {creados} trámites nuevos (todos inactivos para '
            f'revisar), {omitidos} ya existían, '
            f'{caidos} sitio(s) no contestaron.'
        ))

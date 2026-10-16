"""Importar la planilla de organismos (NOMBRE, OCUPACION, LINK_SITIO_OFICIAL).

La planilla viaja con el scraper, en `services/scraper/data/`. Es
idempotente: crea los organismos que falten y completa sitio/ocupación
de los que ya están.
"""

import csv
from pathlib import Path

from munitramites.models import Organismo

# Ruta por defecto de la planilla, resuelta contra este archivo para que
# funcione sin importar desde dónde se corra el comando.
PLANILLA = Path(__file__).resolve().parent / 'data' / 'organismos_misiones.csv'


def importar(ruta=PLANILLA):
    """Crea (o completa) los organismos de la planilla.

    Devuelve (organismos, creados, actualizados).
    """
    organismos, creados, actualizados = [], 0, 0
    with open(ruta, encoding='utf-8-sig', newline='') as archivo:
        for fila in csv.DictReader(archivo):
            nombre = (fila.get('NOMBRE') or '').strip()
            if not nombre:
                continue
            organismo, creado = Organismo.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'direccion': 'Sin dirección informada',
                    'ocupacion': (fila.get('OCUPACION') or '').strip(),
                    'sitio': (fila.get('LINK_SITIO_OFICIAL') or '').strip(),
                },
            )
            if creado:
                creados += 1
            else:
                cambios = {}
                if not organismo.sitio and fila.get('LINK_SITIO_OFICIAL'):
                    cambios['sitio'] = fila['LINK_SITIO_OFICIAL'].strip()
                if not organismo.ocupacion and fila.get('OCUPACION'):
                    cambios['ocupacion'] = fila['OCUPACION'].strip()
                if cambios:
                    for campo, valor in cambios.items():
                        setattr(organismo, campo, valor)
                    organismo.save(update_fields=list(cambios))
                    actualizados += 1
            organismos.append(organismo)
    return organismos, creados, actualizados

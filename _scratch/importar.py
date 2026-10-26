# -*- coding: utf-8 -*-
"""Reemplaza los tramites de la base por el dataset curado.

Uso, desde la raiz del repositorio y con los contenedores levantados:

    docker compose exec -T web python _scratch/importar.py --confirmar

El script hace un dump de la app antes de tocar nada. No borra usuarios,
perfiles ni consultas: las consultas que apuntan a un tramite eliminado
quedan con ``tramite = NULL`` por la FK ``SET_NULL``.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import django

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'munitramites.settings')
django.setup()

from django.core.management import call_command  # noqa: E402
from django.db import transaction  # noqa: E402

import dataset  # noqa: E402
from munitramites.models import (  # noqa: E402
    Direccion,
    Enlace,
    Municipio,
    Organismo,
    Requisito,
    Tema,
    Tramite,
)


def _dump_backup() -> Path:
    """Guarda un dump JSON de la app antes de borrar nada."""
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = BASE / f'backup_antes_import_{marca}.json'
    call_command(
        'dumpdata',
        'munitramites',
        indent=2,
        output=str(destino),
        verbosity=0,
    )
    if not destino.exists() or destino.stat().st_size == 0:
        raise RuntimeError(f'No se pudo crear el backup en {destino}')
    return destino


def _borrar_datos() -> None:
    """Borra primero los tramites y despues los catalogos que usan."""
    Tramite.objects.all().delete()
    # Por las dudas, si quedara una fila huerfana (no deberia).
    Direccion.objects.all().delete()
    Requisito.objects.all().delete()
    Enlace.objects.all().delete()
    Organismo.objects.all().delete()
    Tema.objects.all().delete()
    Municipio.objects.all().delete()

    if Tramite.objects.exists():
        raise RuntimeError('Quedaron tramites despues del borrado')


def _crear_catalogos():
    municipios = {
        nombre: Municipio.objects.create(nombre=nombre)
        for nombre in dataset.MUNICIPIOS
    }
    temas = {
        nombre: Tema.objects.create(nombre=nombre)
        for nombre in dataset.TEMAS
    }
    organismos = {}
    for nombre, datos in dataset.ORGANISMOS.items():
        organismos[nombre] = Organismo.objects.create(
            nombre=nombre,
            direccion=datos['direccion'],
            ocupacion=datos['ocupacion'],
            sitio=datos['sitio'],
        )
    return municipios, temas, organismos


def _crear_tramites(municipios, temas, organismos) -> None:
    for ficha in dataset.TRAMITES:
        tramite = Tramite.objects.create(
            titulo=ficha['titulo'],
            tema=temas[ficha['tema']],
            modalidad=ficha['modalidad'],
            municipio=municipios[ficha['municipio']],
            organismo=organismos[ficha['organismo']],
            descripcion=ficha['descripcion'],
            destacado=ficha['destacado'],
            activo=True,
        )
        Requisito.objects.bulk_create([
            Requisito(
                tramite=tramite,
                descripcion=descripcion,
                orden=orden,
            )
            for orden, descripcion in enumerate(ficha['requisitos'], start=1)
        ])
        Enlace.objects.bulk_create([
            Enlace(
                tramite=tramite,
                nombre=nombre,
                url=url,
                orden=orden,
            )
            for orden, (nombre, url) in enumerate(ficha['enlaces'], start=1)
        ])
        Direccion.objects.bulk_create([
            Direccion(
                tramite=tramite,
                lugar=lugar,
                municipio=municipios[municipio],
                direccion=direccion,
            )
            for lugar, municipio, direccion in ficha['sedes']
        ])


def _verificar() -> None:
    total = Tramite.objects.count()
    if total != len(dataset.TRAMITES):
        raise RuntimeError(
            f'Se esperaban {len(dataset.TRAMITES)} tramites y hay {total}'
        )
    sin_requisitos = Tramite.objects.filter(requisitos__isnull=True).count()
    sin_enlaces = Tramite.objects.filter(enlaces__isnull=True).count()
    sin_direcciones = Tramite.objects.filter(direcciones__isnull=True).count()
    if sin_requisitos or sin_enlaces or sin_direcciones:
        raise RuntimeError(
            'Fichas incompletas: '
            f'sin requisitos={sin_requisitos}, '
            f'sin enlaces={sin_enlaces}, '
            f'sin direcciones={sin_direcciones}'
        )
    print(
        'OK: '
        f'{total} tramites, '
        f'{Requisito.objects.count()} requisitos, '
        f'{Enlace.objects.count()} enlaces, '
        f'{Direccion.objects.count()} direcciones, '
        f'{Municipio.objects.count()} municipios, '
        f'{Tema.objects.count()} temas, '
        f'{Organismo.objects.count()} organismos'
    )


def _csv_fuentes(destino: Path) -> None:
    """Genera el CSV de trazabilidad, una fila por fuente y ficha."""
    filas = []
    for ficha in dataset.TRAMITES:
        for url, dato in ficha['fuentes']:
            metodo = 'GET'
            parametros = ''
            if url == dataset.POSADAS_AJAX:
                metodo = 'POST'
                # El helper de Posadas guarda el id dentro del texto.
                if 'idtramite=' in dato:
                    parametros = 'idtramite=' + dato.split('idtramite=', 1)[1].split(':', 1)[0]
            filas.append({
                'municipio': ficha['municipio'],
                'organismo': ficha['organismo'],
                'tema': ficha['tema'],
                'tramite': ficha['titulo'],
                'url_fuente': url,
                'metodo': metodo,
                'parametros': parametros,
                'dato_extraido': dato,
            })
    with destino.open('w', encoding='utf-8-sig', newline='') as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=[
                'municipio',
                'organismo',
                'tema',
                'tramite',
                'url_fuente',
                'metodo',
                'parametros',
                'dato_extraido',
            ],
        )
        escritor.writeheader()
        escritor.writerows(filas)
    print(f'CSV de fuentes: {destino} ({len(filas)} filas)')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--confirmar',
        action='store_true',
        help='Confirma que se van a borrar los tramites actuales.',
    )
    args = parser.parse_args()
    if not args.confirmar:
        print('Nada hecho. Volve a ejecutar con --confirmar.')
        return 2

    backup = _dump_backup()
    print(f'Backup: {backup}')
    with transaction.atomic():
        _borrar_datos()
        municipios, temas, organismos = _crear_catalogos()
        _crear_tramites(municipios, temas, organismos)
        _verificar()
    _csv_fuentes(BASE / 'fuentes_tramites.csv')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

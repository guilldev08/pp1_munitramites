# -*- coding: utf-8 -*-
"""Reemplaza listas puntuales por versiones más desglosadas."""

import importlib
import sys
from pathlib import Path

from django.conf import settings

sys.path.insert(0, str(Path(settings.BASE_DIR) / '_scratch'))

from munitramites.models import Requisito, Tramite  # noqa: E402

CAMBIOS = {
    'posadas': [
        'Primera licencia de conducir para clases particulares A, B y G',
        'Renovación de licencia de conducir para clases particulares A, B y G',
    ],
    'iguazu': [
        'Licencia de conducir por primera vez para menores de 16 y 17 años',
    ],
}

for modulo_nombre, titulos in CAMBIOS.items():
    modulo = importlib.import_module(f'limpios.{modulo_nombre}')
    for titulo in titulos:
        tramite = Tramite.objects.get(titulo=titulo)
        requisitos = modulo.REQUISITOS[titulo]
        tramite.requisitos.all().delete()
        Requisito.objects.bulk_create([
            Requisito(tramite=tramite, descripcion=texto, orden=orden)
            for orden, texto in enumerate(requisitos, 1)
        ])
        print(f'Reemplazado: {titulo} ({len(requisitos)})')

print('Listo.')

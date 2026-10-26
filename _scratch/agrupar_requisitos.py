# -*- coding: utf-8 -*-
"""Agrupa los requisitos por organismo para revisión manual (temporal)."""

import os
import sys

import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'munitramites.settings')
django.setup()

from munitramites.models import Tramite  # noqa: E402

GRUPOS = {
    'atm': 'Administración Tributaria de Misiones (ATM)',
    'pj': 'Dirección General de Personas Jurídicas y Registro Público',
    'energia': 'Energía de Misiones S.A.',
    'iprodha': 'Instituto Provincial de Desarrollo Habitacional (IPRODHA)',
    'salud': 'Ministerio de Salud Pública de Misiones',
    'posadas': 'Municipalidad de Posadas',
    'obera': 'Municipalidad de Oberá',
    'iguazu': 'Municipalidad de Puerto Iguazú',
    'policia': 'Policía de Misiones',
    'rc': 'Registro Provincial de las Personas',
    'samsa': 'SAMSA - Aguas de Misiones S.A.',
}

for clave, organismo in GRUPOS.items():
    lineas = [f'# {organismo}', '']
    for tramite in (
        Tramite.objects.filter(organismo__nombre=organismo)
        .prefetch_related('requisitos')
        .order_by('titulo')
    ):
        lineas.append(f"## {tramite.pk} · {tramite.titulo}")
        lineas.append('')
        for requisito in tramite.requisitos.all().order_by('orden', 'pk'):
            lineas.append(f'{requisito.orden}. {requisito.descripcion}')
        lineas.append('')
    with open(f'/app/_scratch/rev_{clave}.md', 'w', encoding='utf-8') as archivo:
        archivo.write('\n'.join(lineas))
print('OK')
